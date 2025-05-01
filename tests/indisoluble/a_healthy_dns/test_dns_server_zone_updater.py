#!/usr/bin/env python3

import time

import dns.name
import dns.rdatatype
import dns.versioned
import pytest

from typing import List, NamedTuple
from unittest.mock import call, MagicMock, patch

from indisoluble.a_healthy_dns.dns_server_zone_factory import ExtendedZone
from indisoluble.a_healthy_dns.dns_server_zone_updater import (
    _STOP_JOIN_EXTRA_TIMEOUT,
    ARG_CONNECTION_TIMEOUT,
    ARG_TEST_INTERVAL,
    DnsServerZoneUpdater,
)
from indisoluble.a_healthy_dns.healthy_a_record import HealthyARecord
from indisoluble.a_healthy_dns.healthy_ip import HealthyIp


class SimpleHealthyIp(NamedTuple):
    ip: str
    is_healthy: bool


class SimpleSubdomain(NamedTuple):
    name: str
    ips: List[SimpleHealthyIp]


DOMAIN = "example.com."
SUBDOMAIN_1_HEALTHY_1_UNHEALTHY = SimpleSubdomain(
    "server1",
    [SimpleHealthyIp("192.168.1.1", True), SimpleHealthyIp("192.168.1.2", False)],
)
SUBDOMAIN_2_HEALTHY = SimpleSubdomain(
    "server4",
    [SimpleHealthyIp("192.168.1.6", True), SimpleHealthyIp("192.168.1.7", True)],
)
SUBDOMAINS = [
    SUBDOMAIN_1_HEALTHY_1_UNHEALTHY,
    SimpleSubdomain("server2", [SimpleHealthyIp("192.168.1.3", True)]),
    SimpleSubdomain(
        "server3",
        [SimpleHealthyIp("192.168.1.4", False), SimpleHealthyIp("192.168.1.5", True)],
    ),
    SUBDOMAIN_2_HEALTHY,
]
VAL_CONNECTION_TIMEOUT = 2


def _make_a_record(name: dns.name.Name, ips: List[SimpleHealthyIp]) -> HealthyARecord:
    return HealthyARecord(
        name, 300, frozenset(HealthyIp(ip.ip, 8080, ip.is_healthy) for ip in ips)
    )


@pytest.fixture
def extended_zone():
    origin = dns.name.from_text(DOMAIN)

    # Create A records with different subdomains
    a_records = [
        _make_a_record(dns.name.from_text(sd.name, origin), sd.ips) for sd in SUBDOMAINS
    ]

    # Initialize zone with A records
    zone = dns.versioned.Zone(origin)
    with zone.writer() as txn:
        # Add A records to the zone
        for a_rec in a_records:
            txn.add(
                a_rec.subdomain,
                dns.rdataset.from_text(
                    dns.rdataclass.IN,
                    dns.rdatatype.A,
                    a_rec.ttl_a,
                    *[
                        health_ip.ip
                        for health_ip in a_rec.healthy_ips
                        if health_ip.is_healthy
                    ],
                ),
            )

        # Set SOA record
        txn.add(
            dns.name.empty,
            dns.rdataset.from_text(
                dns.rdataclass.IN,
                dns.rdatatype.SOA,
                300,
                f"ns1.{DOMAIN} admin.{DOMAIN} 1 3600 1800 604800 300",
            ),
        )

    return ExtendedZone(zone, set(a_records))


@pytest.fixture
def zone_updater(extended_zone):
    return DnsServerZoneUpdater(
        extended_zone,
        {ARG_TEST_INTERVAL: 1, ARG_CONNECTION_TIMEOUT: VAL_CONNECTION_TIMEOUT},
    )


@pytest.fixture
def zone_writer_with_changes():
    mock_txn = MagicMock()
    mock_txn.changed.return_value = True

    mock_writer = MagicMock()
    mock_writer.__enter__.return_value = mock_txn

    return mock_writer


@pytest.fixture
def zone_writer_without_changes():
    mock_txn = MagicMock()
    mock_txn.changed.return_value = False

    mock_writer = MagicMock()
    mock_writer.__enter__.return_value = mock_txn

    return mock_writer


def test_init_with_invalid_parameters(extended_zone):
    # Test with invalid check interval
    with pytest.raises(ValueError):
        DnsServerZoneUpdater(
            extended_zone, {ARG_TEST_INTERVAL: 0, ARG_CONNECTION_TIMEOUT: 1}
        )

    # Test with invalid connection timeout
    with pytest.raises(ValueError):
        DnsServerZoneUpdater(
            extended_zone, {ARG_TEST_INTERVAL: 1, ARG_CONNECTION_TIMEOUT: 0}
        )


@patch.object(DnsServerZoneUpdater, "_update_zone")
def test_start_stop(mock_update_zone, zone_updater):
    assert zone_updater._updater_thread is None

    zone_updater.start()

    assert zone_updater._updater_thread is not None
    assert zone_updater._updater_thread.is_alive()
    assert zone_updater._updater_thread.daemon is True

    # Wait a bit to ensure the thread runs
    time.sleep(0.2)

    # Check that update_zone was called at least once
    assert mock_update_zone.called

    result = zone_updater.stop()

    assert result is True
    assert not zone_updater._updater_thread.is_alive()


@patch.object(DnsServerZoneUpdater, "_update_zone")
def test_start_when_already_running(_, zone_updater):
    zone_updater.start()
    original_thread = zone_updater._updater_thread

    # Try to start again
    zone_updater.start()

    # Verify the thread is the same
    assert zone_updater._updater_thread is original_thread

    # Clean up
    zone_updater.stop()


@patch.object(DnsServerZoneUpdater, "_update_zone")
def test_stop_when_not_running(_, zone_updater):
    assert zone_updater.stop() is True


@patch("threading.Thread.join")
@patch("threading.Thread.is_alive", return_value=True)
@patch.object(DnsServerZoneUpdater, "_update_zone")
def test_stop_timeout(_, __, mock_join, zone_updater):
    zone_updater.start()
    result = zone_updater.stop()

    assert result is False

    # Verify join was called with the correct timeout
    mock_join.assert_called_once_with(
        timeout=VAL_CONNECTION_TIMEOUT + _STOP_JOIN_EXTRA_TIMEOUT
    )


@patch.object(DnsServerZoneUpdater, "_update_a_record_in_zone")
def test_update_zone(
    mock_update_a_record_in_zone, zone_updater, zone_writer_with_changes
):
    zone_updater._zone = MagicMock()
    zone_updater._zone.writer.return_value = zone_writer_with_changes

    mock_txn = zone_writer_with_changes.__enter__.return_value

    original_a_records = zone_updater._a_records.copy()
    updated_records = {
        a_record: a_record.updated_ips(
            frozenset(
                ip.updated_status(not ip.is_healthy) for ip in a_record.healthy_ips
            )
        )
        for a_record in original_a_records
    }
    mock_update_a_record_in_zone.side_effect = lambda r, _: updated_records[r]

    zone_updater._update_zone()

    assert mock_update_a_record_in_zone.call_count == len(original_a_records)
    mock_update_a_record_in_zone.assert_has_calls(
        [call(record, mock_txn) for record in original_a_records], any_order=True
    )
    mock_txn.update_serial.assert_called_once()
    assert zone_updater._a_records == set(updated_records.values())


@patch.object(DnsServerZoneUpdater, "_update_a_record_in_zone")
def test_update_zone_with_stop_event(
    mock_update_a_record_in_zone, zone_updater, zone_writer_with_changes
):
    zone_updater._zone = MagicMock()
    zone_updater._zone.writer.return_value = zone_writer_with_changes

    mock_txn = zone_writer_with_changes.__enter__.return_value

    original_a_records = list(zone_updater._a_records)
    updated_records = [
        original_a_records[0].updated_ips(
            frozenset(
                ip.updated_status(not ip.is_healthy)
                for ip in original_a_records[0].healthy_ips
            )
        ),
        *original_a_records[1:],
    ]

    def side_effect(record, _):
        if record == original_a_records[0]:
            zone_updater._stop_event.set()
            return updated_records[0]

        return record

    mock_update_a_record_in_zone.side_effect = side_effect

    zone_updater._update_zone()

    assert mock_update_a_record_in_zone.call_count == 1
    mock_update_a_record_in_zone.assert_called_once_with(
        original_a_records[0], mock_txn
    )
    mock_txn.update_serial.assert_called_once()
    assert zone_updater._a_records == set(updated_records)


@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.can_create_connection")
def test_update_a_record_in_zone(mock_can_create_connection, zone_updater):
    a_record = _make_a_record(
        dns.name.from_text(
            SUBDOMAIN_1_HEALTHY_1_UNHEALTHY.name, dns.name.from_text(DOMAIN)
        ),
        SUBDOMAIN_1_HEALTHY_1_UNHEALTHY.ips,
    )

    # Configure can_create_connection to return opposite health statuses
    updated_statuses = {
        healthy_ip.ip: healthy_ip.updated_status(not healthy_ip.is_healthy)
        for healthy_ip in a_record.healthy_ips
    }
    mock_can_create_connection.side_effect = lambda ip, _, __: updated_statuses[
        ip
    ].is_healthy

    mock_txn = MagicMock()
    result = zone_updater._update_a_record_in_zone(a_record, mock_txn)

    assert result.healthy_ips != a_record.healthy_ips
    assert result.healthy_ips == frozenset(updated_statuses.values())

    assert mock_can_create_connection.call_count == len(a_record.healthy_ips)
    mock_can_create_connection.assert_has_calls(
        [
            call(
                healthy_ip.ip, healthy_ip.health_port, zone_updater._connection_timeout
            )
            for healthy_ip in a_record.healthy_ips
        ],
        any_order=True,
    )

    updated_healthy_ips = [ip for ip in updated_statuses.values() if ip.is_healthy]
    assert len(updated_healthy_ips) == 1
    mock_txn.replace.assert_called_once_with(
        a_record.subdomain,
        dns.rdataset.from_text(
            dns.rdataclass.IN,
            dns.rdatatype.A,
            a_record.ttl_a,
            updated_healthy_ips[0].ip,
        ),
    )


@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.can_create_connection")
def test_delete_a_record_in_zone(mock_can_create_connection, zone_updater):
    a_record = _make_a_record(
        dns.name.from_text(SUBDOMAIN_2_HEALTHY.name, dns.name.from_text(DOMAIN)),
        SUBDOMAIN_2_HEALTHY.ips,
    )

    # Configure can_create_connection to return opposite health statuses
    updated_statuses = {
        healthy_ip.ip: healthy_ip.updated_status(not healthy_ip.is_healthy)
        for healthy_ip in a_record.healthy_ips
    }
    mock_can_create_connection.side_effect = lambda ip, _, __: updated_statuses[
        ip
    ].is_healthy

    mock_txn = MagicMock()
    result = zone_updater._update_a_record_in_zone(a_record, mock_txn)

    assert result.healthy_ips != a_record.healthy_ips
    assert result.healthy_ips == frozenset(updated_statuses.values())

    assert mock_can_create_connection.call_count == len(a_record.healthy_ips)
    mock_can_create_connection.assert_has_calls(
        [
            call(
                healthy_ip.ip, healthy_ip.health_port, zone_updater._connection_timeout
            )
            for healthy_ip in a_record.healthy_ips
        ],
        any_order=True,
    )

    mock_txn.delete.assert_called_once_with(a_record.subdomain)


@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.can_create_connection")
def test_update_a_record_in_zone_no_changes(mock_can_create_connection, zone_updater):
    a_record = _make_a_record(
        dns.name.from_text(
            SUBDOMAIN_1_HEALTHY_1_UNHEALTHY.name, dns.name.from_text(DOMAIN)
        ),
        SUBDOMAIN_1_HEALTHY_1_UNHEALTHY.ips,
    )

    # Configure can_create_connection to return the same health statuses
    mock_can_create_connection.side_effect = lambda ip, _, __: next(
        healthy_ip for healthy_ip in a_record.healthy_ips if healthy_ip.ip == ip
    ).is_healthy

    mock_txn = MagicMock()
    result = zone_updater._update_a_record_in_zone(a_record, mock_txn)

    assert result is a_record

    assert mock_can_create_connection.call_count == len(a_record.healthy_ips)
    mock_can_create_connection.assert_has_calls(
        [
            call(
                healthy_ip.ip, healthy_ip.health_port, zone_updater._connection_timeout
            )
            for healthy_ip in a_record.healthy_ips
        ],
        any_order=True,
    )

    mock_txn.replace.assert_not_called()
    mock_txn.delete.assert_not_called()


@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.can_create_connection")
def test_update_a_record_in_zone_with_stop_event(
    mock_can_create_connection, zone_updater
):
    a_record = _make_a_record(
        dns.name.from_text(
            SUBDOMAIN_1_HEALTHY_1_UNHEALTHY.name, dns.name.from_text(DOMAIN)
        ),
        SUBDOMAIN_1_HEALTHY_1_UNHEALTHY.ips,
    )

    def side_effect(ip, _, __):
        zone_updater._stop_event.set()
        return not next(
            healthy_ip for healthy_ip in a_record.healthy_ips if healthy_ip.ip == ip
        ).is_healthy

    mock_can_create_connection.side_effect = side_effect

    mock_txn = MagicMock()
    result = zone_updater._update_a_record_in_zone(a_record, mock_txn)

    assert result is a_record

    assert mock_can_create_connection.call_count == 1

    mock_txn.replace.assert_not_called()
    mock_txn.delete.assert_not_called()
