#!/usr/bin/env python3

import datetime
import threading
import time

import dns.dnssectypes
import dns.name
import dns.rdataset
import dns.rdatatype
import dns.versioned
import pytest

from typing import List, NamedTuple, Tuple
from unittest.mock import patch

from dns.dnssecalgs.rsa import PrivateRSASHA256

from indisoluble.a_healthy_dns.dns_server_zone_factory import (
    ExtendedPrivateKey,
    ExtendedZone,
)
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
    SimpleSubdomain(
        "server5",
        [SimpleHealthyIp("192.168.1.8", False), SimpleHealthyIp("192.168.1.9", False)],
    ),
]
VAL_CONNECTION_TIMEOUT = 2


def _make_a_record(name: dns.name.Name, ips: List[SimpleHealthyIp]) -> HealthyARecord:
    return HealthyARecord(
        name, 300, frozenset(HealthyIp(ip.ip, 8080, ip.is_healthy) for ip in ips)
    )


def _extended_zone() -> ExtendedZone:
    origin = dns.name.from_text(DOMAIN)

    # Create zone
    zone = dns.versioned.Zone(origin)

    # Create NS record
    ns_record = dns.rdataset.ImmutableRdataset(
        dns.rdataset.from_text(
            dns.rdataclass.IN, dns.rdatatype.NS, 300, f"ns1.{DOMAIN}"
        )
    )

    # Create SOA record
    soa_record = dns.rdataset.ImmutableRdataset(
        dns.rdataset.from_text(
            dns.rdataclass.IN,
            dns.rdatatype.SOA,
            300,
            f"ns1.{DOMAIN} admin.{DOMAIN} 1 3600 1800 604800 300",
        )
    )

    # Create A records with different subdomains
    a_records = [
        _make_a_record(dns.name.from_text(sd.name, origin), sd.ips) for sd in SUBDOMAINS
    ]

    return ExtendedZone(zone, ns_record, soa_record, set(a_records), None)


def _zone_updater() -> DnsServerZoneUpdater:
    return DnsServerZoneUpdater(
        _extended_zone(),
        {ARG_TEST_INTERVAL: 1, ARG_CONNECTION_TIMEOUT: VAL_CONNECTION_TIMEOUT},
    )


def _extended_zone_with_priv_key() -> ExtendedZone:
    ext_zone = _extended_zone()

    private_key = PrivateRSASHA256.generate(key_size=2048)
    dnskey = dns.dnssec.make_dnskey(
        private_key.public_key(), dns.dnssectypes.Algorithm.RSASHA256
    )
    ext_priv_key = ExtendedPrivateKey(private_key, dnskey, 86400, 1209600)

    return ExtendedZone(
        ext_zone.zone, ext_zone.ns_rec, ext_zone.soa_rec, ext_zone.a_recs, ext_priv_key
    )


def _zone_updater_with_priv_key() -> DnsServerZoneUpdater:
    return DnsServerZoneUpdater(
        _extended_zone_with_priv_key(),
        {ARG_TEST_INTERVAL: 1, ARG_CONNECTION_TIMEOUT: VAL_CONNECTION_TIMEOUT},
    )


def _subdomains_with_at_least_one_healthy_ip() -> List[dns.name.Name]:
    return [
        dns.name.from_text(sd.name, origin=None)
        for sd in SUBDOMAINS
        if any(ip.is_healthy for ip in sd.ips)
    ]


def _is_ip_healthy(ip: str) -> bool:
    simple_ip = next(
        simple_ip for sd in SUBDOMAINS for simple_ip in sd.ips if simple_ip.ip == ip
    )
    return simple_ip.is_healthy


def _assert_compare_rdatasets(
    records: Tuple[dns.name.Name, dns.rdataset.Rdataset],
    other_records: Tuple[dns.name.Name, dns.rdataset.Rdataset],
    *,
    only_name_identical: bool,
):
    assert len(records) == len(other_records)
    if len(records) > 0:
        if only_name_identical:
            assert all(
                one_rec[0] in [name for name, _ in other_records] for one_rec in records
            )
            assert all(
                one_rec[1] not in [rsets for _, rsets in other_records]
                for one_rec in records
            )
        else:
            assert all(one_rec in other_records for one_rec in records)


@pytest.fixture
def extended_zone():
    return _extended_zone()


@pytest.fixture
def zone_updater():
    return _zone_updater()


@pytest.fixture
def zone_updater_with_priv_key():
    return _zone_updater_with_priv_key()


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


@pytest.mark.parametrize(
    "updater,with_priv_key",
    [(_zone_updater(), False), (_zone_updater_with_priv_key(), True)],
)
@patch("time.time")
@patch.object(DnsServerZoneUpdater, "_update_zone")
def test_start_stop(mock_update_zone, mock_time, updater, with_priv_key):
    # Mock current time to ensure a new SOA serial is calculated
    mock_time.return_value = 1234567890.0

    # Configure mock_update_zone to indicate when called
    update_zone_called = threading.Event()
    mock_update_zone.side_effect = lambda: update_zone_called.set()

    # Check that the updater thread is not started
    assert updater._updater_thread is None

    # Check updater zone is not initialized
    assert updater._zone is not None
    assert len(updater._zone.nodes) == 0

    # Start the updater
    updater.start()

    # Check that the thread is created and alive
    assert updater._updater_thread is not None
    assert updater._updater_thread.is_alive()
    assert updater._updater_thread.daemon is True

    # Check that update_zone was called at least once
    assert update_zone_called.wait(timeout=1)
    assert mock_update_zone.called

    # Stop the updater
    result = updater.stop()

    # Check that the thread is no longer alive
    assert result is True
    assert not updater._updater_thread.is_alive()

    # Check updater zone is initialized
    assert len(list(updater._zone.iterate_rdatasets(dns.rdatatype.NS))) == 1
    ns_rrsigs = list(
        updater._zone.iterate_rdatasets(dns.rdatatype.RRSIG, dns.rdatatype.NS)
    )
    assert len(ns_rrsigs) == (1 if with_priv_key else 0)
    soa_records = list(updater._zone.iterate_rdatasets(dns.rdatatype.SOA))
    assert len(soa_records) == 1
    soa_rdata = soa_records[0][1][0]
    assert soa_rdata.serial == 1234567890
    soa_rrsigs = list(
        updater._zone.iterate_rdatasets(dns.rdatatype.RRSIG, dns.rdatatype.SOA)
    )
    assert len(soa_rrsigs) == (1 if with_priv_key else 0)
    a_records = list(updater._zone.iterate_rdatasets(dns.rdatatype.A))
    healthy_subdomains = _subdomains_with_at_least_one_healthy_ip()
    assert len(a_records) == len(healthy_subdomains)
    assert all([name in healthy_subdomains for name, _ in a_records])
    a_rrsigs = list(
        updater._zone.iterate_rdatasets(dns.rdatatype.RRSIG, dns.rdatatype.A)
    )
    assert len(a_rrsigs) == (len(a_records) if with_priv_key else 0)
    dnskey_records = list(updater._zone.iterate_rdatasets(dns.rdatatype.DNSKEY))
    assert len(dnskey_records) == (1 if with_priv_key else 0)
    assert dnskey_records[0][1].ttl == 86400 if with_priv_key else True
    dnskey_rrsigs = list(
        updater._zone.iterate_rdatasets(dns.rdatatype.RRSIG, dns.rdatatype.DNSKEY)
    )
    assert len(dnskey_rrsigs) == (1 if with_priv_key else 0)
    nsec_records = list(updater._zone.iterate_rdatasets(dns.rdatatype.NSEC))
    assert len(nsec_records) > 0 if with_priv_key else len(nsec_records) == 0
    nsec_rrsigs = list(
        updater._zone.iterate_rdatasets(dns.rdatatype.RRSIG, dns.rdatatype.NSEC)
    )
    assert len(nsec_rrsigs) == (len(nsec_records) if with_priv_key else 0)


@patch.object(DnsServerZoneUpdater, "_initialize_zone")
@patch.object(DnsServerZoneUpdater, "_update_zone")
def test_start_when_already_running(_, mock_initialize_zone, zone_updater):
    # Start the updater
    zone_updater.start()
    original_thread = zone_updater._updater_thread

    # Check zone was initialized
    assert mock_initialize_zone.call_count == 1

    # Try to start again
    zone_updater.start()

    # Verify the thread is the same
    assert zone_updater._updater_thread is original_thread

    # Check zone was not re-initialized
    assert mock_initialize_zone.call_count == 1

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


@pytest.mark.parametrize("is_zone_sign_expire", [False, True])
@patch("time.time")
@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.datetime")
@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.can_create_connection")
def test_update_zone_without_changes(
    mock_can_create_connection,
    mock_datetime,
    mock_time,
    is_zone_sign_expire,
    zone_updater_with_priv_key,
):
    # Mock the connection check to return the current healthy values
    mock_can_create_connection.side_effect = lambda ip, _, __: _is_ip_healthy(ip)

    # Check updater zone is not initialized
    assert zone_updater_with_priv_key._zone is not None
    assert len(zone_updater_with_priv_key._zone.nodes) == 0

    # Mock current time
    mock_time.return_value = 1234567890.0
    mock_datetime.datetime.now.return_value = (
        zone_updater_with_priv_key._zone_key.rrsig_resign_time
    )

    # Initialize the zone
    zone_updater_with_priv_key._initialize_zone()

    # Check that the zone is initialized
    ns_records = list(
        zone_updater_with_priv_key._zone.iterate_rdatasets(dns.rdatatype.NS)
    )
    assert len(ns_records) == 1
    ns_rrsigs = list(
        zone_updater_with_priv_key._zone.iterate_rdatasets(
            dns.rdatatype.RRSIG, dns.rdatatype.NS
        )
    )
    assert len(ns_rrsigs) == 1
    soa_records = list(
        zone_updater_with_priv_key._zone.iterate_rdatasets(dns.rdatatype.SOA)
    )
    assert len(soa_records) == 1
    soa_rrsigs = list(
        zone_updater_with_priv_key._zone.iterate_rdatasets(
            dns.rdatatype.RRSIG, dns.rdatatype.SOA
        )
    )
    assert len(soa_rrsigs) == 1
    a_records = list(
        zone_updater_with_priv_key._zone.iterate_rdatasets(dns.rdatatype.A)
    )
    healthy_subdomains = _subdomains_with_at_least_one_healthy_ip()
    assert len(a_records) == len(healthy_subdomains)
    assert all([name in healthy_subdomains for name, _ in a_records])
    a_rrsigs = list(
        zone_updater_with_priv_key._zone.iterate_rdatasets(
            dns.rdatatype.RRSIG, dns.rdatatype.A
        )
    )
    assert len(a_rrsigs) == len(a_records)
    dnskey_records = list(
        zone_updater_with_priv_key._zone.iterate_rdatasets(dns.rdatatype.DNSKEY)
    )
    assert len(dnskey_records) == 1
    dnskey_rrsigs = list(
        zone_updater_with_priv_key._zone.iterate_rdatasets(
            dns.rdatatype.RRSIG, dns.rdatatype.DNSKEY
        )
    )
    assert len(dnskey_rrsigs) == 1
    nsec_records = list(
        zone_updater_with_priv_key._zone.iterate_rdatasets(dns.rdatatype.NSEC)
    )
    assert len(nsec_records) > 0
    nsec_rrsigs = list(
        zone_updater_with_priv_key._zone.iterate_rdatasets(
            dns.rdatatype.RRSIG, dns.rdatatype.NSEC
        )
    )
    assert len(nsec_rrsigs) == len(nsec_records)

    # Set mock time to a future value to ensure a new soa serial
    # would be calculated if neceesary
    mock_time.return_value += 1.0

    # Mock current time so the zone sign is expired or not
    if is_zone_sign_expire:
        mock_datetime.datetime.now.return_value = (
            zone_updater_with_priv_key._zone_key.rrsig_resign_time
        )
    else:
        mock_datetime.datetime.now.return_value += datetime.timedelta(seconds=1)

    # Update zone
    zone_updater_with_priv_key._update_zone()

    # Check zone did not change
    other_ns_records = list(
        zone_updater_with_priv_key._zone.iterate_rdatasets(dns.rdatatype.NS)
    )
    _assert_compare_rdatasets(ns_records, other_ns_records, only_name_identical=False)
    other_ns_rrsigs = list(
        zone_updater_with_priv_key._zone.iterate_rdatasets(
            dns.rdatatype.RRSIG, dns.rdatatype.NS
        )
    )
    _assert_compare_rdatasets(
        ns_rrsigs, other_ns_rrsigs, only_name_identical=is_zone_sign_expire
    )
    other_soa_records = list(
        zone_updater_with_priv_key._zone.iterate_rdatasets(dns.rdatatype.SOA)
    )
    _assert_compare_rdatasets(
        soa_records, other_soa_records, only_name_identical=is_zone_sign_expire
    )
    other_soa_rrsigs = list(
        zone_updater_with_priv_key._zone.iterate_rdatasets(
            dns.rdatatype.RRSIG, dns.rdatatype.SOA
        )
    )
    _assert_compare_rdatasets(
        soa_rrsigs, other_soa_rrsigs, only_name_identical=is_zone_sign_expire
    )
    other_a_records = list(
        zone_updater_with_priv_key._zone.iterate_rdatasets(dns.rdatatype.A)
    )
    _assert_compare_rdatasets(a_records, other_a_records, only_name_identical=False)
    other_a_rrsigs = list(
        zone_updater_with_priv_key._zone.iterate_rdatasets(
            dns.rdatatype.RRSIG, dns.rdatatype.A
        )
    )
    _assert_compare_rdatasets(
        a_rrsigs, other_a_rrsigs, only_name_identical=is_zone_sign_expire
    )
    other_dnskey_records = list(
        zone_updater_with_priv_key._zone.iterate_rdatasets(dns.rdatatype.DNSKEY)
    )
    _assert_compare_rdatasets(
        dnskey_records, other_dnskey_records, only_name_identical=False
    )
    other_dnskey_rrsigs = list(
        zone_updater_with_priv_key._zone.iterate_rdatasets(
            dns.rdatatype.RRSIG, dns.rdatatype.DNSKEY
        )
    )
    _assert_compare_rdatasets(
        dnskey_rrsigs, other_dnskey_rrsigs, only_name_identical=is_zone_sign_expire
    )
    other_nsec_records = list(
        zone_updater_with_priv_key._zone.iterate_rdatasets(dns.rdatatype.NSEC)
    )
    _assert_compare_rdatasets(
        nsec_records, other_nsec_records, only_name_identical=False
    )
    other_nsec_rrsigs = list(
        zone_updater_with_priv_key._zone.iterate_rdatasets(
            dns.rdatatype.RRSIG, dns.rdatatype.NSEC
        )
    )
    _assert_compare_rdatasets(
        nsec_rrsigs, other_nsec_rrsigs, only_name_identical=is_zone_sign_expire
    )


@pytest.mark.parametrize(
    "updater,with_priv_key",
    [(_zone_updater(), False), (_zone_updater_with_priv_key(), True)],
)
@patch("time.time")
@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.datetime")
@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.can_create_connection")
def test_update_zone_with_all_ips_failing(
    mock_can_create_connection, mock_datetime, mock_time, updater, with_priv_key
):
    # Mock the connection check to always return False
    mock_can_create_connection.return_value = False

    # Check updater zone is not initialized
    assert updater._zone is not None
    assert len(updater._zone.nodes) == 0

    # Mock current time
    mock_time.return_value = 1234567890.0
    mock_datetime.datetime.now.return_value = (
        updater._zone_key.rrsig_resign_time
        if with_priv_key
        else datetime.datetime.now()
    )

    # Initialize the zone
    updater._initialize_zone()

    # Check that the zone is initialized
    ns_records = list(updater._zone.iterate_rdatasets(dns.rdatatype.NS))
    assert len(ns_records) == 1
    ns_rrsigs = list(
        updater._zone.iterate_rdatasets(dns.rdatatype.RRSIG, dns.rdatatype.NS)
    )
    assert len(ns_rrsigs) == (1 if with_priv_key else 0)
    soa_records = list(updater._zone.iterate_rdatasets(dns.rdatatype.SOA))
    assert len(soa_records) == 1
    soa_rrsigs = list(
        updater._zone.iterate_rdatasets(dns.rdatatype.RRSIG, dns.rdatatype.SOA)
    )
    assert len(soa_rrsigs) == (1 if with_priv_key else 0)
    a_records = list(updater._zone.iterate_rdatasets(dns.rdatatype.A))
    healthy_subdomains = _subdomains_with_at_least_one_healthy_ip()
    assert len(a_records) == len(healthy_subdomains)
    assert all([name in healthy_subdomains for name, _ in a_records])
    a_rrsigs = list(
        updater._zone.iterate_rdatasets(dns.rdatatype.RRSIG, dns.rdatatype.A)
    )
    assert len(a_rrsigs) == (len(a_records) if with_priv_key else 0)
    dnskey_records = list(updater._zone.iterate_rdatasets(dns.rdatatype.DNSKEY))
    assert len(dnskey_records) == (1 if with_priv_key else 0)
    dnskey_rrsigs = list(
        updater._zone.iterate_rdatasets(dns.rdatatype.RRSIG, dns.rdatatype.DNSKEY)
    )
    assert len(dnskey_rrsigs) == (1 if with_priv_key else 0)
    nsec_records = list(updater._zone.iterate_rdatasets(dns.rdatatype.NSEC))
    assert len(nsec_records) > 0 if with_priv_key else len(nsec_records) == 0
    nsec_rrsigs = list(
        updater._zone.iterate_rdatasets(dns.rdatatype.RRSIG, dns.rdatatype.NSEC)
    )
    assert len(nsec_rrsigs) == (len(nsec_records) if with_priv_key else 0)

    # Set mock time to a future value to ensure a new soa serial
    # would be calculated if neceesary
    mock_time.return_value += 1.0

    # Mock current time so the zone sign is not expired
    mock_datetime.datetime.now.return_value += datetime.timedelta(seconds=1)

    # Update zone
    updater._update_zone()

    # Check only NS and SOA records are present
    other_ns_records = list(updater._zone.iterate_rdatasets(dns.rdatatype.NS))
    _assert_compare_rdatasets(ns_records, other_ns_records, only_name_identical=False)
    other_ns_rrsigs = list(
        updater._zone.iterate_rdatasets(dns.rdatatype.RRSIG, dns.rdatatype.NS)
    )
    _assert_compare_rdatasets(
        ns_rrsigs, other_ns_rrsigs, only_name_identical=with_priv_key
    )
    other_soa_records = list(updater._zone.iterate_rdatasets(dns.rdatatype.SOA))
    _assert_compare_rdatasets(soa_records, other_soa_records, only_name_identical=True)
    other_soa_rrsigs = list(
        updater._zone.iterate_rdatasets(dns.rdatatype.RRSIG, dns.rdatatype.SOA)
    )
    _assert_compare_rdatasets(
        soa_rrsigs, other_soa_rrsigs, only_name_identical=with_priv_key
    )
    other_a_records = list(updater._zone.iterate_rdatasets(dns.rdatatype.A))
    assert len(other_a_records) == 0
    other_a_rrsigs = list(
        updater._zone.iterate_rdatasets(dns.rdatatype.RRSIG, dns.rdatatype.A)
    )
    assert len(other_a_rrsigs) == 0
    other_dnskey_records = list(updater._zone.iterate_rdatasets(dns.rdatatype.DNSKEY))
    _assert_compare_rdatasets(
        dnskey_records, other_dnskey_records, only_name_identical=False
    )
    other_dnskey_rrsigs = list(
        updater._zone.iterate_rdatasets(dns.rdatatype.RRSIG, dns.rdatatype.DNSKEY)
    )
    _assert_compare_rdatasets(
        dnskey_rrsigs, other_dnskey_rrsigs, only_name_identical=with_priv_key
    )
    other_nsec_records = list(updater._zone.iterate_rdatasets(dns.rdatatype.NSEC))
    assert len(other_nsec_records) == 0
    other_nsec_rrsigs = list(
        updater._zone.iterate_rdatasets(dns.rdatatype.RRSIG, dns.rdatatype.NSEC)
    )
    assert len(other_nsec_rrsigs) == 0


@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.can_create_connection")
def test_refresh_a_record_with_stop_event(mock_can_create_connection, zone_updater):
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

    result = zone_updater._refresh_a_record(a_record)

    assert result is a_record
    assert len(a_record.healthy_ips) > 1
    assert mock_can_create_connection.call_count == 1


@patch.object(DnsServerZoneUpdater, "_refresh_a_record")
def test_refresh_a_recs_with_stop_event(mock_refresh_a_record, zone_updater):
    def side_effect(record):
        zone_updater._stop_event.set()
        return record.updated_ips(
            frozenset(ip.updated_status(not ip.is_healthy) for ip in record.healthy_ips)
        )

    mock_refresh_a_record.side_effect = side_effect

    result = zone_updater._refresh_a_recs()

    assert result is False
    assert len(zone_updater._a_recs) > 1
    assert mock_refresh_a_record.call_count == 1
