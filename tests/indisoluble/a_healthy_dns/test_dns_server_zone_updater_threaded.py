#!/usr/bin/env python3

import threading

import dns.name
import dns.versioned
import pytest

from unittest.mock import Mock, call, patch

from indisoluble.a_healthy_dns.dns_server_config_factory import DnsServerConfig
from indisoluble.a_healthy_dns.dns_server_zone_updater import (
    DELTA_PER_RECORD_MANAGEMENT,
    DnsServerZoneUpdater,
)
from indisoluble.a_healthy_dns.dns_server_zone_updater_threaded import (
    DnsServerZoneUpdaterThreaded,
)
from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp
from indisoluble.a_healthy_dns.records.a_healthy_record import AHealthyRecord
from indisoluble.a_healthy_dns.records.zone_origins import ZoneOrigins

_ZONE_UPDATER = (
    "indisoluble.a_healthy_dns.dns_server_zone_updater_threaded." "DnsServerZoneUpdater"
)
_EVENT = "indisoluble.a_healthy_dns.dns_server_zone_updater_threaded.threading.Event"
_THREAD = "indisoluble.a_healthy_dns.dns_server_zone_updater_threaded.threading.Thread"
_TIME = "indisoluble.a_healthy_dns.dns_server_zone_updater_threaded.time.time"


@pytest.fixture
def zone_origins():
    return ZoneOrigins("example.com", [])


@pytest.fixture
def config(zone_origins):
    subdomain = dns.name.from_text("www", origin=zone_origins.primary)
    ip = AHealthyIp(ip="192.168.1.1", health_port=8080, is_healthy=True)
    a_record = AHealthyRecord(subdomain=subdomain, healthy_ips=[ip])

    return DnsServerConfig(
        zone_origins=zone_origins,
        primary_name_server="ns1.dns.example.net",
        name_servers=frozenset(["ns1.dns.example.net", "ns2.dns.example.net"]),
        a_records=frozenset([a_record]),
        ext_private_key=None,
    )


@pytest.fixture
def zone(zone_origins):
    zone = Mock(spec=dns.versioned.Zone)
    zone.origin = zone_origins.primary

    return zone


@pytest.fixture
def zone_updater(zone):
    updater = Mock(spec=DnsServerZoneUpdater)
    updater.zone = zone

    return updater


@pytest.fixture
def stop_event():
    return Mock(spec=threading.Event)


@pytest.fixture
def updater_thread():
    return Mock(spec=threading.Thread)


def _make_threaded_updater(
    mock_zone_updater_class,
    mock_event_class,
    zone_updater,
    stop_event,
    config,
    *,
    min_interval=5,
    connection_timeout=10,
):
    mock_zone_updater_class.return_value = zone_updater
    mock_event_class.return_value = stop_event

    return DnsServerZoneUpdaterThreaded(min_interval, connection_timeout, config)


def _assert_thread_created_for_update_loop(mock_thread_class, updater):
    mock_thread_class.assert_called_once()

    thread_kwargs = mock_thread_class.call_args.kwargs
    thread_target = thread_kwargs["target"]
    assert thread_target.__self__ is updater
    assert thread_target.__name__ == "_update_zone_loop"
    assert thread_kwargs["name"] == "ZoneUpdaterThread"
    assert thread_kwargs["daemon"] is True


def _time_values_for_update_loop(update_count, min_interval, update_duration):
    return [
        timestamp
        for update_index in range(update_count)
        for timestamp in (
            update_index * min_interval,
            update_index * min_interval + update_duration,
        )
    ]


class TestInitialization:
    @patch(_EVENT)
    @patch(_ZONE_UPDATER)
    def test_creates_inner_updater_and_stop_event(
        self,
        mock_zone_updater_class,
        mock_event_class,
        zone_updater,
        stop_event,
        config,
    ):
        min_interval = 5
        connection_timeout = 10

        updater = _make_threaded_updater(
            mock_zone_updater_class,
            mock_event_class,
            zone_updater,
            stop_event,
            config,
            min_interval=min_interval,
            connection_timeout=connection_timeout,
        )

        assert updater is not None
        mock_zone_updater_class.assert_called_once_with(
            min_interval, connection_timeout, config
        )
        mock_event_class.assert_called_once_with()

    @patch(_EVENT)
    @patch(_ZONE_UPDATER)
    def test_wraps_inner_updater_initialization_failure(
        self, mock_zone_updater_class, mock_event_class, config
    ):
        mock_zone_updater_class.side_effect = Exception("Initialization failed")

        with pytest.raises(
            ValueError, match="Failed to initialize updater: Initialization failed"
        ):
            DnsServerZoneUpdaterThreaded(5, 10, config)

        mock_event_class.assert_not_called()


class TestZoneProperty:
    @patch(_EVENT)
    @patch(_ZONE_UPDATER)
    def test_returns_inner_updater_zone(
        self,
        mock_zone_updater_class,
        mock_event_class,
        zone_updater,
        stop_event,
        config,
        zone,
    ):
        updater = _make_threaded_updater(
            mock_zone_updater_class,
            mock_event_class,
            zone_updater,
            stop_event,
            config,
        )

        assert updater.zone == zone


class TestStart:
    @patch(_THREAD)
    @patch(_EVENT)
    @patch(_ZONE_UPDATER)
    def test_initializes_zone_and_starts_daemon_thread(
        self,
        mock_zone_updater_class,
        mock_event_class,
        mock_thread_class,
        zone_updater,
        stop_event,
        updater_thread,
        config,
    ):
        updater = _make_threaded_updater(
            mock_zone_updater_class,
            mock_event_class,
            zone_updater,
            stop_event,
            config,
        )
        mock_thread_class.return_value = updater_thread

        updater.start()

        updater_thread.is_alive.assert_not_called()
        zone_updater.initialize_zone.assert_called_once_with()
        stop_event.clear.assert_called_once_with()
        _assert_thread_created_for_update_loop(mock_thread_class, updater)
        updater_thread.start.assert_called_once_with()

    @patch(_THREAD)
    @patch(_EVENT)
    @patch(_ZONE_UPDATER)
    def test_does_nothing_when_thread_is_already_running(
        self,
        mock_zone_updater_class,
        mock_event_class,
        mock_thread_class,
        zone_updater,
        stop_event,
        updater_thread,
        config,
    ):
        updater = _make_threaded_updater(
            mock_zone_updater_class,
            mock_event_class,
            zone_updater,
            stop_event,
            config,
        )
        mock_thread_class.return_value = updater_thread
        updater_thread.is_alive.return_value = True

        updater.start()

        mock_thread_class.reset_mock()
        updater_thread.reset_mock()
        stop_event.reset_mock()
        zone_updater.reset_mock()

        updater.start()

        updater_thread.is_alive.assert_called_once_with()
        zone_updater.initialize_zone.assert_not_called()
        zone_updater.update.assert_not_called()
        stop_event.clear.assert_not_called()
        mock_thread_class.assert_not_called()
        updater_thread.start.assert_not_called()


class TestStop:
    @patch(_EVENT)
    @patch(_ZONE_UPDATER)
    def test_returns_true_without_signaling_when_thread_is_not_running(
        self,
        mock_zone_updater_class,
        mock_event_class,
        zone_updater,
        stop_event,
        config,
    ):
        updater = _make_threaded_updater(
            mock_zone_updater_class,
            mock_event_class,
            zone_updater,
            stop_event,
            config,
        )

        assert updater.stop() is True
        stop_event.set.assert_not_called()

    @pytest.mark.parametrize(
        "is_alive_after_join,expected_result",
        [
            (True, False),
            (False, True),
        ],
        ids=["still-running", "stopped"],
    )
    @patch(_THREAD)
    @patch(_EVENT)
    @patch(_ZONE_UPDATER)
    def test_signals_thread_and_returns_whether_it_stopped(
        self,
        mock_zone_updater_class,
        mock_event_class,
        mock_thread_class,
        is_alive_after_join,
        expected_result,
        zone_updater,
        stop_event,
        updater_thread,
        config,
    ):
        connection_timeout = 10
        updater = _make_threaded_updater(
            mock_zone_updater_class,
            mock_event_class,
            zone_updater,
            stop_event,
            config,
            connection_timeout=connection_timeout,
        )
        mock_thread_class.return_value = updater_thread
        updater.start()

        updater_thread.is_alive.side_effect = [True, is_alive_after_join]
        updater_thread.reset_mock()
        stop_event.reset_mock()

        assert updater.stop() is expected_result
        assert updater_thread.is_alive.call_count == 2
        stop_event.set.assert_called_once_with()
        updater_thread.join.assert_called_once_with(
            timeout=connection_timeout + DELTA_PER_RECORD_MANAGEMENT
        )


class TestUpdateLoop:
    @patch(_TIME)
    @patch(_EVENT)
    @patch(_ZONE_UPDATER)
    def test_update_loop_runs_updates_until_stop_event_is_set(
        self,
        mock_zone_updater_class,
        mock_event_class,
        mock_time,
        zone_updater,
        stop_event,
        config,
    ):
        min_interval = 5
        update_duration = 1
        update_count = 3
        updater = _make_threaded_updater(
            mock_zone_updater_class,
            mock_event_class,
            zone_updater,
            stop_event,
            config,
            min_interval=min_interval,
        )
        stop_event.is_set.side_effect = [False] * update_count + [True]
        stop_event.wait.return_value = False
        mock_time.side_effect = _time_values_for_update_loop(
            update_count, min_interval, update_duration
        )

        updater._update_zone_loop()

        assert zone_updater.update.call_count == update_count

    @patch(_TIME)
    @patch(_EVENT)
    @patch(_ZONE_UPDATER)
    def test_update_loop_passes_stop_event_abort_callback_to_each_update(
        self,
        mock_zone_updater_class,
        mock_event_class,
        mock_time,
        zone_updater,
        stop_event,
        config,
    ):
        min_interval = 2
        update_duration = 5
        update_count = 2
        updater = _make_threaded_updater(
            mock_zone_updater_class,
            mock_event_class,
            zone_updater,
            stop_event,
            config,
            min_interval=min_interval,
        )
        stop_event.is_set.side_effect = [False] * update_count + [True]
        mock_time.side_effect = _time_values_for_update_loop(
            update_count, min_interval, update_duration
        )

        updater._update_zone_loop()

        for update_call in zone_updater.update.call_args_list:
            should_abort = update_call.kwargs["should_abort"]
            assert callable(should_abort)

        stop_event.is_set.side_effect = None
        stop_event.is_set.return_value = True
        should_abort = zone_updater.update.call_args.kwargs["should_abort"]
        assert should_abort() is True

    @patch(_TIME)
    @patch(_EVENT)
    @patch(_ZONE_UPDATER)
    def test_update_loop_waits_remaining_interval_after_fast_updates(
        self,
        mock_zone_updater_class,
        mock_event_class,
        mock_time,
        zone_updater,
        stop_event,
        config,
    ):
        min_interval = 5
        update_duration = 1
        update_count = 3
        updater = _make_threaded_updater(
            mock_zone_updater_class,
            mock_event_class,
            zone_updater,
            stop_event,
            config,
            min_interval=min_interval,
        )
        stop_event.is_set.side_effect = [False] * update_count + [True]
        stop_event.wait.return_value = False
        mock_time.side_effect = _time_values_for_update_loop(
            update_count, min_interval, update_duration
        )

        updater._update_zone_loop()

        assert stop_event.wait.call_args_list == [
            call(4.0) for _ in range(update_count)
        ]

    @patch(_TIME)
    @patch(_EVENT)
    @patch(_ZONE_UPDATER)
    def test_update_loop_skips_wait_when_update_exceeds_interval(
        self,
        mock_zone_updater_class,
        mock_event_class,
        mock_time,
        zone_updater,
        stop_event,
        config,
    ):
        min_interval = 2
        update_duration = 5
        update_count = 3
        updater = _make_threaded_updater(
            mock_zone_updater_class,
            mock_event_class,
            zone_updater,
            stop_event,
            config,
            min_interval=min_interval,
        )
        stop_event.is_set.side_effect = [False] * update_count + [True]
        mock_time.side_effect = _time_values_for_update_loop(
            update_count, min_interval, update_duration
        )

        updater._update_zone_loop()

        stop_event.wait.assert_not_called()
