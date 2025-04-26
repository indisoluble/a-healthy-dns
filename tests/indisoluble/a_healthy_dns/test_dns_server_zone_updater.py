#!/usr/bin/env python3

from typing import List, NamedTuple

import dns.name
import dns.rdatatype
import dns.versioned
import pytest

from unittest.mock import patch

from indisoluble.a_healthy_dns.dns_server_zone_factory import ExtendedZone
from indisoluble.a_healthy_dns.dns_server_zone_updater import DnsServerZoneUpdater
from indisoluble.a_healthy_dns.healthy_a_record import HealthyARecord
from indisoluble.a_healthy_dns.healthy_ip import HealthyIp


class SimpleHealthyIp(NamedTuple):
    ip: str
    is_healthy: bool


class SimpleSubdomain(NamedTuple):
    name: str
    ips: List[SimpleHealthyIp]


DOMAIN = "example.com."
SUBDOMAINS = [
    SimpleSubdomain(
        "server1",
        [SimpleHealthyIp("192.168.1.1", True), SimpleHealthyIp("192.168.1.2", False)],
    ),
    SimpleSubdomain("server2", [SimpleHealthyIp("192.168.1.3", True)]),
]
IPS = [ip for subdomain in SUBDOMAINS for ip in subdomain.ips]


@pytest.fixture
def extended_zone():
    origin = dns.name.from_text(DOMAIN)
    zone = dns.versioned.Zone(origin)

    # Create A records with different subdomains
    subdomain1 = dns.name.from_text(SUBDOMAINS[0].name, origin)
    subdomain2 = dns.name.from_text(SUBDOMAINS[1].name, origin)

    a_record1 = HealthyARecord(
        subdomain1,
        300,
        frozenset(
            [
                HealthyIp(simple_ip.ip, 8080, simple_ip.is_healthy)
                for simple_ip in SUBDOMAINS[0].ips
            ]
        ),
    )
    a_record2 = HealthyARecord(
        subdomain2,
        300,
        frozenset(
            [
                HealthyIp(simple_ip.ip, 8080, simple_ip.is_healthy)
                for simple_ip in SUBDOMAINS[1].ips
            ]
        ),
    )

    # Initialize zone with A records
    with zone.writer() as txn:
        # Add A records to the zone
        txn.add(
            subdomain1,
            dns.rdataset.from_text(
                dns.rdataclass.IN,
                dns.rdatatype.A,
                a_record1.ttl_a,
                *[
                    health_ip.ip
                    for health_ip in a_record1.healthy_ips
                    if health_ip.is_healthy
                ],
            ),
        )
        txn.add(
            subdomain2,
            dns.rdataset.from_text(
                dns.rdataclass.IN,
                dns.rdatatype.A,
                a_record2.ttl_a,
                *[
                    health_ip.ip
                    for health_ip in a_record2.healthy_ips
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

    return ExtendedZone(zone, {a_record1, a_record2})


@pytest.fixture
def zone_updater(extended_zone):
    return DnsServerZoneUpdater(
        extended_zone, check_interval_seconds=1, connection_timeout=1
    )


def test_init_with_invalid_parameters(extended_zone):
    # Test with invalid check interval
    with pytest.raises(ValueError):
        DnsServerZoneUpdater(
            extended_zone, check_interval_seconds=0, connection_timeout=1
        )

    # Test with invalid connection timeout
    with pytest.raises(ValueError):
        DnsServerZoneUpdater(
            extended_zone, check_interval_seconds=1, connection_timeout=0
        )


@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.can_create_connection")
def test_update_zone_no_changes(mock_can_create, zone_updater):
    mock_can_create.side_effect = lambda ip, port, timeout: ip in [
        simple_ip.ip for simple_ip in IPS if simple_ip.is_healthy
    ]

    initial_a_records = zone_updater._a_records.copy()

    zone_updater._update_zone()

    assert zone_updater._a_records == initial_a_records
    assert mock_can_create.call_count == len(IPS)


@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.can_create_connection")
def test_update_zone_with_changes(mock_can_create, zone_updater):
    mock_can_create.side_effect = lambda ip, port, timeout: ip in [
        simple_ip.ip for simple_ip in IPS if not simple_ip.is_healthy
    ]

    zone_updater._update_zone()

    assert len(zone_updater._a_records) == len(SUBDOMAINS)
    for record in zone_updater._a_records:
        for health_ip in record.healthy_ips:
            simple_ip = next(
                simple_ip for simple_ip in IPS if simple_ip.ip == health_ip.ip
            )
            assert health_ip.is_healthy == (not simple_ip.is_healthy)

    with zone_updater._zone.reader() as txn:
        server1_rdataset = txn.get(
            dns.name.from_text(f"{SUBDOMAINS[0].name}.{DOMAIN}"), dns.rdatatype.A
        )
        server1_ips = [rdata.address for rdata in server1_rdataset]
        assert all(
            ip in server1_ips
            for ip in [
                simple_ip.ip
                for simple_ip in SUBDOMAINS[0].ips
                if not simple_ip.is_healthy
            ]
        )
        assert all(
            ip not in server1_ips
            for ip in [
                simple_ip.ip for simple_ip in SUBDOMAINS[0].ips if simple_ip.is_healthy
            ]
        )

        server2_rdataset = txn.get(
            dns.name.from_text(f"{SUBDOMAINS[1].name}.{DOMAIN}"), dns.rdatatype.A
        )
        assert server2_rdataset is None


@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.can_create_connection")
def test_clean_zone(mock_can_create, zone_updater):
    mock_can_create.return_value = False

    zone_updater._update_zone()

    assert len(zone_updater._a_records) == len(SUBDOMAINS)
    assert all(
        not healthy_ip.is_healthy
        for record in zone_updater._a_records
        for healthy_ip in record.healthy_ips
    )

    with zone_updater._zone.reader() as txn:
        server1_rdataset = txn.get(
            dns.name.from_text(f"{SUBDOMAINS[0].name}.{DOMAIN}"), dns.rdatatype.A
        )
        assert server1_rdataset is None

        server2_rdataset = txn.get(
            dns.name.from_text(f"{SUBDOMAINS[1].name}.{DOMAIN}"), dns.rdatatype.A
        )
        assert server2_rdataset is None


@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.can_create_connection")
def test_updater_thread(mock_can_create, zone_updater):
    mock_can_create.return_value = True

    # Start the updater thread
    zone_updater.start()
    assert zone_updater._updater_thread is not None
    assert zone_updater._updater_thread.is_alive()

    # Stop the updater thread
    result = zone_updater.stop()
    assert result is True
    assert not zone_updater._updater_thread.is_alive()

    # Verify can_create_connection was called multiple times
    assert mock_can_create.call_count > 0


@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.can_create_connection")
def test_start_already_running(mock_can_create, zone_updater):
    mock_can_create.return_value = True

    zone_updater.start()
    thread = zone_updater._updater_thread

    zone_updater.start()

    # Verify the thread is the same (wasn't restarted)
    assert zone_updater._updater_thread is thread

    # Clean up
    result = zone_updater.stop()
    assert result is True


def test_stop_not_running(zone_updater):
    assert zone_updater._updater_thread is None

    result = zone_updater.stop()
    assert result is True


@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.can_create_connection")
def test_serial_update_after_zone_update(mock_can_create, zone_updater):
    initial_serial = None
    with zone_updater._zone.reader() as txn:
        soa_rdataset = txn.get(dns.name.empty, dns.rdatatype.SOA)
        initial_serial = soa_rdataset[0].serial

    mock_can_create.return_value = False
    zone_updater._update_zone()

    with zone_updater._zone.reader() as txn:
        soa_rdataset = txn.get(dns.name.empty, dns.rdatatype.SOA)
        new_serial = soa_rdataset[0].serial

    assert new_serial > initial_serial


@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.can_create_connection")
def test_serial_update_no_changes(mock_can_create, zone_updater):
    initial_serial = None
    with zone_updater._zone.reader() as txn:
        soa_rdataset = txn.get(dns.name.empty, dns.rdatatype.SOA)
        initial_serial = soa_rdataset[0].serial

    mock_can_create.side_effect = lambda ip, port, timeout: ip in [
        simple_ip.ip for simple_ip in IPS if simple_ip.is_healthy
    ]
    zone_updater._update_zone()

    with zone_updater._zone.reader() as txn:
        soa_rdataset = txn.get(dns.name.empty, dns.rdatatype.SOA)
        new_serial = soa_rdataset[0].serial

    assert new_serial == initial_serial
