#!/usr/bin/env python3

import itertools
import threading

import dns.name
import dns.versioned
import pytest

from unittest.mock import ANY, Mock, patch

from indisoluble.a_healthy_dns.dns_server_config_factory import DnsServerConfig
from indisoluble.a_healthy_dns.dns_server_zone_updater import (
    DELTA_PER_RECORD_MANAGEMENT,
    DnsServerZoneUpdater,
)
from indisoluble.a_healthy_dns.dns_server_zone_updater_threated import (
    DnsServerZoneUpdaterThreated,
)
from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp
from indisoluble.a_healthy_dns.records.a_healthy_record import AHealthyRecord


@pytest.fixture
def mock_origin_name():
    return dns.name.from_text("example.com", origin=dns.name.root)


@pytest.fixture
def mock_config(mock_origin_name):
    subdomain = dns.name.from_text("www", origin=mock_origin_name)
    ip = AHealthyIp(ip="192.168.1.1", health_port=8080, is_healthy=True)
    a_record = AHealthyRecord(subdomain=subdomain, healthy_ips=[ip])

    return DnsServerConfig(
        origin_name=mock_origin_name,
        name_servers=frozenset(["ns1.example.com", "ns2.example.com"]),
        a_records=frozenset([a_record]),
        ext_private_key=None,
        alias_zones=frozenset(),
    )


@pytest.fixture
def mock_zone(mock_origin_name):
    zone = Mock(spec=dns.versioned.Zone)
    zone.origin = mock_origin_name

    return zone


@pytest.fixture
def mock_updater(mock_zone):
    updater = Mock(spec=DnsServerZoneUpdater)
    updater.zone = mock_zone

    return updater


@pytest.fixture
def mock_event():
    event = Mock(spec=threading.Event)

    return event


@pytest.fixture
def mock_thread():
    thread = Mock(spec=threading.Thread)

    return thread


@patch("threading.Event")
@patch(
    "indisoluble.a_healthy_dns.dns_server_zone_updater_threated.DnsServerZoneUpdater"
)
def test_init_success(
    mock_updater_class, mock_event_class, mock_updater, mock_event, mock_config
):
    mock_updater_class.return_value = mock_updater
    mock_event_class.return_value = mock_event

    min_interval = 5
    connection_timeout = 10

    assert (
        DnsServerZoneUpdaterThreated(min_interval, connection_timeout, mock_config)
        is not None
    )

    mock_updater_class.assert_called_once_with(
        min_interval, connection_timeout, mock_config
    )
    mock_event_class.assert_called_once()


@patch("threading.Event")
@patch(
    "indisoluble.a_healthy_dns.dns_server_zone_updater_threated.DnsServerZoneUpdater"
)
def test_init_failure_raises_value_error(
    mock_updater_class, mock_event_class, mock_config
):
    mock_updater_class.side_effect = Exception("Initialization failed")

    with pytest.raises(
        ValueError, match="Failed to initialize updater: Initialization failed"
    ):
        DnsServerZoneUpdaterThreated(5, 10, mock_config)

    mock_event_class.assert_not_called()


@patch("threading.Event")
@patch(
    "indisoluble.a_healthy_dns.dns_server_zone_updater_threated.DnsServerZoneUpdater"
)
def test_zone_property(
    mock_updater_class,
    mock_event_class,
    mock_updater,
    mock_event,
    mock_config,
    mock_zone,
):
    mock_updater_class.return_value = mock_updater
    mock_event_class.return_value = mock_event

    assert DnsServerZoneUpdaterThreated(5, 10, mock_config).zone == mock_zone


@patch("threading.Thread")
@patch("threading.Event")
@patch(
    "indisoluble.a_healthy_dns.dns_server_zone_updater_threated.DnsServerZoneUpdater"
)
def test_start_success(
    mock_updater_class,
    mock_event_class,
    mock_thread_class,
    mock_updater,
    mock_event,
    mock_thread,
    mock_config,
):
    mock_updater_class.return_value = mock_updater
    mock_event_class.return_value = mock_event
    updater = DnsServerZoneUpdaterThreated(5, 10, mock_config)

    mock_thread_class.return_value = mock_thread

    updater.start()

    mock_thread.is_alive.assert_not_called()
    mock_updater.update.assert_called_once_with(check_ips=False)
    mock_event.clear.assert_called_once()
    mock_thread_class.assert_called_once_with(
        target=updater._update_zone_loop, name=ANY, daemon=True
    )
    mock_thread.start.assert_called_once()


@patch("threading.Thread")
@patch("threading.Event")
@patch(
    "indisoluble.a_healthy_dns.dns_server_zone_updater_threated.DnsServerZoneUpdater"
)
def test_start_already_running(
    mock_updater_class,
    mock_event_class,
    mock_thread_class,
    mock_updater,
    mock_event,
    mock_thread,
    mock_config,
):
    mock_updater_class.return_value = mock_updater
    mock_event_class.return_value = mock_event
    updater = DnsServerZoneUpdaterThreated(5, 10, mock_config)

    mock_thread_class.return_value = mock_thread
    mock_thread.is_alive.return_value = True

    updater.start()

    mock_thread_class.reset_mock()
    mock_thread.reset_mock()
    mock_event.reset_mock()
    mock_updater.reset_mock()

    updater.start()

    mock_thread.is_alive.assert_called_once()
    mock_updater.update.assert_not_called()
    mock_event.clear.assert_not_called()
    mock_thread_class.assert_not_called()
    mock_thread.start.assert_not_called()


@patch("threading.Event")
@patch(
    "indisoluble.a_healthy_dns.dns_server_zone_updater_threated.DnsServerZoneUpdater"
)
def test_stop_not_running(
    mock_updater_class, mock_event_class, mock_updater, mock_event, mock_config
):
    mock_updater_class.return_value = mock_updater
    mock_event_class.return_value = mock_event
    updater = DnsServerZoneUpdaterThreated(5, 10, mock_config)

    assert updater.stop() is True

    mock_event.set.assert_not_called()


@pytest.mark.parametrize("is_alive_after_join", [True, False])
@patch("threading.Thread")
@patch("threading.Event")
@patch(
    "indisoluble.a_healthy_dns.dns_server_zone_updater_threated.DnsServerZoneUpdater"
)
def test_stop_with_different_join_result(
    mock_updater_class,
    mock_event_class,
    mock_thread_class,
    is_alive_after_join,
    mock_updater,
    mock_event,
    mock_thread,
    mock_config,
):
    mock_updater_class.return_value = mock_updater
    mock_event_class.return_value = mock_event

    connection_timeout = 10
    updater = DnsServerZoneUpdaterThreated(5, connection_timeout, mock_config)

    mock_thread_class.return_value = mock_thread

    updater.start()

    mock_thread.is_alive.side_effect = [True, is_alive_after_join]

    mock_thread.reset_mock()
    mock_event.reset_mock()

    assert updater.stop() is not is_alive_after_join

    assert mock_thread.is_alive.call_count == 2
    mock_event.set.assert_called_once()
    mock_thread.join.assert_called_once_with(
        timeout=connection_timeout + DELTA_PER_RECORD_MANAGEMENT
    )


@pytest.mark.parametrize("min_interval,update_duration", [(5, 1), (2, 5)])
@patch("time.time")
@patch("threading.Event")
@patch(
    "indisoluble.a_healthy_dns.dns_server_zone_updater_threated.DnsServerZoneUpdater"
)
def test_update_zone(
    mock_updater_class,
    mock_event_class,
    mock_time,
    min_interval,
    update_duration,
    mock_updater,
    mock_event,
    mock_config,
):
    mock_updater_class.return_value = mock_updater
    mock_event_class.return_value = mock_event

    updater = DnsServerZoneUpdaterThreated(min_interval, 10, mock_config)

    update_count = 3
    is_set_results = [False] * update_count + [True]
    mock_event.is_set.side_effect = is_set_results

    mock_time.side_effect = list(
        itertools.chain.from_iterable(
            (i * min_interval, i * min_interval + update_duration)
            for i in range(len(is_set_results))
        )
    )

    mock_event.wait.return_value = False

    updater._update_zone_loop()

    assert mock_updater.update.call_count == update_count
    if update_duration > min_interval:
        assert mock_event.wait.call_count == 0
    else:
        assert mock_event.wait.call_count == update_count
        assert all(
            call[0][0] == (min_interval - update_duration)
            for call in mock_event.wait.call_args_list
        )
