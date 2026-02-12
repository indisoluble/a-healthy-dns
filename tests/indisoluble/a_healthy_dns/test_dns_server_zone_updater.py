#!/usr/bin/env python3

import dns.dnssec
import dns.name
import dns.node
import dns.rdataset
import dns.rdatatype
import pytest

from typing import List
from unittest.mock import ANY, Mock, patch

from dns.dnssecalgs.rsa import PrivateRSASHA256

from indisoluble.a_healthy_dns.dns_server_config_factory import (
    DnsServerConfig,
    ExtendedPrivateKey,
)
from indisoluble.a_healthy_dns.dns_server_zone_updater import DnsServerZoneUpdater
from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp
from indisoluble.a_healthy_dns.records.a_healthy_record import AHealthyRecord


def _get_rrsig_rdatasets(
    node: dns.node.Node, rdatatype: dns.rdatatype.RdataType
) -> List[dns.rdataset.Rdataset]:
    return [
        rd
        for rd in node.rdatasets
        if rd.rdtype == dns.rdatatype.RRSIG
        and any(rrsig.type_covered == rdatatype for rrsig in rd)
    ]


@pytest.fixture
def origin_name():
    return dns.name.from_text("example.com", origin=dns.name.root)


@pytest.fixture
def a_record_all_ips_healthy(origin_name):
    subdomain = dns.name.from_text("www", origin=origin_name)
    ip1 = AHealthyIp(ip="192.168.1.1", health_port=8080, is_healthy=True)
    ip2 = AHealthyIp(ip="192.168.1.2", health_port=8080, is_healthy=True)

    return AHealthyRecord(subdomain=subdomain, healthy_ips=[ip1, ip2])


@pytest.fixture
def a_record_ip_unhealthy(origin_name):
    subdomain = dns.name.from_text("api", origin=origin_name)
    ip = AHealthyIp(ip="192.168.1.3", health_port=8080, is_healthy=False)

    return AHealthyRecord(subdomain=subdomain, healthy_ips=[ip])


@pytest.fixture
def name_servers():
    return ["ns1.example.com", "ns2.example.com"]


@pytest.fixture
def ext_private_key():
    private_key = PrivateRSASHA256.generate(key_size=2048)
    dnskey = dns.dnssec.make_dnskey(private_key.public_key(), dns.dnssec.RSASHA256)

    return ExtendedPrivateKey(private_key=private_key, dnskey=dnskey)


@pytest.fixture
def basic_config(
    origin_name, name_servers, a_record_all_ips_healthy, a_record_ip_unhealthy
):
    return DnsServerConfig(
        origin_name=origin_name,
        name_servers=frozenset(name_servers),
        a_records=frozenset((a_record_all_ips_healthy, a_record_ip_unhealthy)),
        ext_private_key=None,
        alias_zones=frozenset(),
    )


@pytest.fixture
def config_with_dnssec(
    origin_name,
    name_servers,
    a_record_all_ips_healthy,
    a_record_ip_unhealthy,
    ext_private_key,
):
    return DnsServerConfig(
        origin_name=origin_name,
        name_servers=frozenset(name_servers),
        a_records=frozenset((a_record_all_ips_healthy, a_record_ip_unhealthy)),
        ext_private_key=ext_private_key,
        alias_zones=frozenset(),
    )


@pytest.fixture
def config_with_mock_dnssec(
    origin_name, name_servers, a_record_all_ips_healthy, a_record_ip_unhealthy
):
    mock_private_key = Mock(spec=dns.dnssec.PrivateKey)
    mock_dnskey = Mock(spec=dns.dnssec.DNSKEY)
    ext_private_key = ExtendedPrivateKey(
        private_key=mock_private_key, dnskey=mock_dnskey
    )

    return DnsServerConfig(
        origin_name=origin_name,
        name_servers=frozenset(name_servers),
        a_records=frozenset((a_record_all_ips_healthy, a_record_ip_unhealthy)),
        ext_private_key=ext_private_key,
        alias_zones=frozenset(),
    )


@pytest.fixture
def updater_no_dnssec(basic_config):
    return DnsServerZoneUpdater(
        min_interval=30, connection_timeout=5, config=basic_config
    )


@pytest.fixture
def updater_with_dnssec(config_with_dnssec):
    return DnsServerZoneUpdater(
        min_interval=30, connection_timeout=5, config=config_with_dnssec
    )


@pytest.mark.parametrize("min_interval", [0, -1])
def test_init_with_invalid_min_interval_should_raise_value_error(
    min_interval, basic_config
):
    with pytest.raises(ValueError, match="Minimum interval must be positive"):
        DnsServerZoneUpdater(
            min_interval=min_interval, connection_timeout=5, config=basic_config
        )


@pytest.mark.parametrize("connection_timeout", [0, -1])
def test_init_with_invalid_connection_timeout_should_raise_value_error(
    connection_timeout, basic_config
):
    with pytest.raises(ValueError, match="Connection timeout must be positive"):
        DnsServerZoneUpdater(
            min_interval=10, connection_timeout=connection_timeout, config=basic_config
        )


@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.make_ns_record")
@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.iter_soa_record")
@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.iter_rrsig_key")
def test_init_success_without_dnssec(
    mock_iter_rrsig_key, mock_iter_soa_record, mock_make_ns_record, basic_config
):
    mock_ns_record = Mock()
    mock_soa_record = Mock()
    mock_make_ns_record.return_value = mock_ns_record
    mock_iter_soa_record.return_value = iter([mock_soa_record])

    updater = DnsServerZoneUpdater(
        min_interval=30, connection_timeout=5, config=basic_config
    )

    assert updater is not None
    assert updater.zone is not None
    assert updater.zone.origin == basic_config.origin_name
    assert len(list(updater.zone.keys())) == 0
    mock_make_ns_record.assert_called_once_with(ANY, basic_config.name_servers)
    mock_iter_soa_record.assert_called_once_with(ANY, basic_config.origin_name, ANY)
    mock_iter_rrsig_key.assert_not_called()


@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.make_ns_record")
@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.iter_soa_record")
@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.iter_rrsig_key")
def test_init_success_with_dnssec(
    mock_iter_rrsig_key,
    mock_iter_soa_record,
    mock_make_ns_record,
    config_with_mock_dnssec,
):
    mock_ns_record = Mock()
    mock_soa_record = Mock()
    mock_rrsig_key_iter = Mock()
    mock_make_ns_record.return_value = mock_ns_record
    mock_iter_soa_record.return_value = mock_soa_record
    mock_iter_rrsig_key.return_value = mock_rrsig_key_iter

    # Create updater
    updater = DnsServerZoneUpdater(
        min_interval=30, connection_timeout=5, config=config_with_mock_dnssec
    )

    assert updater is not None
    assert updater.zone is not None
    assert updater.zone.origin == config_with_mock_dnssec.origin_name
    assert len(list(updater.zone.keys())) == 0

    mock_make_ns_record.assert_called_once_with(
        ANY, config_with_mock_dnssec.name_servers
    )
    mock_iter_soa_record.assert_called_once_with(
        ANY, config_with_mock_dnssec.origin_name, ANY
    )
    mock_iter_rrsig_key.assert_called_once_with(
        ANY, config_with_mock_dnssec.ext_private_key
    )


def test_initialize_zone_creates_zone_with_basic_records(
    updater_no_dnssec, name_servers, a_record_all_ips_healthy, a_record_ip_unhealthy
):
    assert len(list(updater_no_dnssec.zone.keys())) == 0

    updater_no_dnssec.update(check_ips=False)

    assert len(list(updater_no_dnssec.zone.keys())) > 0

    ns_rdataset = updater_no_dnssec.zone.get_rdataset(dns.name.empty, dns.rdatatype.NS)
    assert ns_rdataset is not None
    assert len(ns_rdataset) == len(name_servers)

    soa_rdataset = updater_no_dnssec.zone.get_rdataset(
        dns.name.empty, dns.rdatatype.SOA
    )
    assert soa_rdataset is not None
    assert len(soa_rdataset) == 1

    for record in (a_record_all_ips_healthy, a_record_ip_unhealthy):
        a_rdataset = updater_no_dnssec.zone.get_rdataset(
            record.subdomain, dns.rdatatype.A
        )
        ip_count = len([ip for ip in record.healthy_ips if ip.is_healthy])
        if ip_count == 0:
            assert a_rdataset is None
        else:
            assert a_rdataset is not None
            assert len(a_rdataset) == ip_count


def test_initialize_zone_creates_zone_with_basic_and_rrsig_records(
    updater_with_dnssec, name_servers, a_record_all_ips_healthy, a_record_ip_unhealthy
):
    assert len(list(updater_with_dnssec.zone.keys())) == 0

    updater_with_dnssec.update(check_ips=False)

    assert len(list(updater_with_dnssec.zone.keys())) > 0

    root_node = updater_with_dnssec.zone.get_node(dns.name.empty)
    assert root_node is not None

    ns_rdataset = updater_with_dnssec.zone.get_rdataset(
        dns.name.empty, dns.rdatatype.NS
    )
    ns_rrsig_rdatasets = _get_rrsig_rdatasets(root_node, dns.rdatatype.NS)
    assert ns_rdataset is not None
    assert len(ns_rdataset) == len(name_servers)
    assert len(ns_rrsig_rdatasets) == 1

    soa_rdataset = updater_with_dnssec.zone.get_rdataset(
        dns.name.empty, dns.rdatatype.SOA
    )
    soa_rrsig_rdatasets = _get_rrsig_rdatasets(root_node, dns.rdatatype.SOA)
    assert soa_rdataset is not None
    assert len(soa_rdataset) == 1
    assert len(soa_rrsig_rdatasets) == 1

    dnskey_rdataset = updater_with_dnssec.zone.get_rdataset(
        dns.name.empty, dns.rdatatype.DNSKEY
    )
    dnskey_rrsig_rdatasets = _get_rrsig_rdatasets(root_node, dns.rdatatype.DNSKEY)
    assert dnskey_rdataset is not None
    assert len(dnskey_rdataset) == 1
    assert len(dnskey_rrsig_rdatasets) == 1

    nsec_rdataset = updater_with_dnssec.zone.get_rdataset(
        dns.name.empty, dns.rdatatype.NSEC
    )
    nsec_rrsig_rdatasets = _get_rrsig_rdatasets(root_node, dns.rdatatype.NSEC)
    assert nsec_rdataset is not None
    assert len(nsec_rdataset) == 1
    assert len(nsec_rrsig_rdatasets) == 1

    for record in (a_record_all_ips_healthy, a_record_ip_unhealthy):
        a_rdataset = updater_with_dnssec.zone.get_rdataset(
            record.subdomain, dns.rdatatype.A
        )
        ip_count = len([ip for ip in record.healthy_ips if ip.is_healthy])

        if ip_count == 0:
            assert a_rdataset is None
            assert updater_with_dnssec.zone.get_node(record.subdomain) is None
        else:
            assert a_rdataset is not None
            assert len(a_rdataset) == ip_count

            a_node = updater_with_dnssec.zone.get_node(record.subdomain)
            assert a_node is not None

            a_rrsig_rdatasets = _get_rrsig_rdatasets(a_node, dns.rdatatype.A)
            assert len(a_rrsig_rdatasets) == 1

            a_nsec_rdataset = updater_with_dnssec.zone.get_rdataset(
                record.subdomain, dns.rdatatype.NSEC
            )
            a_nsec_rrsig_rdatasets = _get_rrsig_rdatasets(a_node, dns.rdatatype.NSEC)
            assert a_nsec_rdataset is not None
            assert len(a_nsec_rdataset) == 1
            assert len(a_nsec_rrsig_rdatasets) == 1


def test_initialize_zone_with_no_healthy_ips(
    origin_name, name_servers, a_record_ip_unhealthy
):
    config = DnsServerConfig(
        origin_name=origin_name,
        name_servers=frozenset(name_servers),
        a_records=frozenset([a_record_ip_unhealthy]),
        ext_private_key=None,
        alias_zones=frozenset(),
    )

    updater = DnsServerZoneUpdater(min_interval=30, connection_timeout=5, config=config)

    # Initialize the zone
    updater.update(check_ips=False)

    # Should have NS and SOA records
    ns_rdataset = updater.zone.get_rdataset(dns.name.empty, dns.rdatatype.NS)
    assert ns_rdataset is not None

    soa_rdataset = updater.zone.get_rdataset(dns.name.empty, dns.rdatatype.SOA)
    assert soa_rdataset is not None

    # Should NOT have A record for the unhealthy subdomain
    test_rdataset = updater.zone.get_rdataset(
        a_record_ip_unhealthy.subdomain, dns.rdatatype.A
    )
    assert test_rdataset is None


@patch("indisoluble.a_healthy_dns.records.soa_record.uint32_current_time")
def test_initialize_zone_twice(
    mock_time,
    updater_no_dnssec,
    name_servers,
    a_record_all_ips_healthy,
    a_record_ip_unhealthy,
):
    multiple_a_records = (a_record_all_ips_healthy, a_record_ip_unhealthy)

    timestamps = [1000, 1001]
    mock_time.side_effect = timestamps

    # Initialize the zone first time
    updater_no_dnssec.update(check_ips=False)

    # Verify we have the expected records
    first_ns_rdataset = updater_no_dnssec.zone.get_rdataset(
        dns.name.empty, dns.rdatatype.NS
    )
    assert first_ns_rdataset is not None
    assert len(first_ns_rdataset) == len(name_servers)

    first_soa_rdataset = updater_no_dnssec.zone.get_rdataset(
        dns.name.empty, dns.rdatatype.SOA
    )
    assert first_soa_rdataset is not None
    assert len(first_soa_rdataset) == 1
    assert first_soa_rdataset[0].serial == timestamps[0]

    first_a_records = {}
    for record in multiple_a_records:
        a_rdataset = updater_no_dnssec.zone.get_rdataset(
            record.subdomain, dns.rdatatype.A
        )
        first_a_records[record.subdomain] = a_rdataset

        ip_count = len([ip for ip in record.healthy_ips if ip.is_healthy])
        if ip_count > 0:
            assert a_rdataset is not None
            assert len(a_rdataset) == ip_count
        else:
            assert a_rdataset is None

    # Initialize the zone second time
    updater_no_dnssec.update(check_ips=False)

    # Verify we have the expected records
    second_ns_rdataset = updater_no_dnssec.zone.get_rdataset(
        dns.name.empty, dns.rdatatype.NS
    )
    assert second_ns_rdataset == first_ns_rdataset

    second_soa_rdataset = updater_no_dnssec.zone.get_rdataset(
        dns.name.empty, dns.rdatatype.SOA
    )
    assert second_soa_rdataset is not None
    assert len(first_soa_rdataset) == 1
    assert second_soa_rdataset[0].serial == timestamps[1]

    second_a_records = {
        record.subdomain: updater_no_dnssec.zone.get_rdataset(
            record.subdomain, dns.rdatatype.A
        )
        for record in multiple_a_records
    }
    assert second_a_records == first_a_records


@pytest.mark.parametrize("can_create_connection_value", [True, False])
@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.can_create_connection")
def test_refresh_records_with_same_status_for_all_ips_and_no_abort(
    mock_can_create_connection, can_create_connection_value, basic_config
):
    mock_can_create_connection.return_value = can_create_connection_value

    # Create updater after mocking can_create_connection
    updater = DnsServerZoneUpdater(
        min_interval=30, connection_timeout=5, config=basic_config
    )
    assert len(list(updater.zone.keys())) == 0

    updater.update(should_abort=lambda: False)

    expected_calls = [
        (healthy_ip.ip, healthy_ip.health_port)
        for record in basic_config.a_records
        for healthy_ip in record.healthy_ips
    ]
    assert mock_can_create_connection.call_count == len(expected_calls)
    assert all(
        any(
            expected[0] == call[0][0] and expected[1] == call[0][1]
            for call in mock_can_create_connection.call_args_list
        )
        for expected in expected_calls
    )

    assert all(
        rd if can_create_connection_value else not rd
        for rd in (
            updater.zone.get_rdataset(rec.subdomain, dns.rdatatype.A)
            for rec in basic_config.a_records
        )
    )


@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.can_create_connection")
def test_refresh_records_keeps_zone_unchanged_when_abort_on_last_ip(
    mock_can_create_connection, basic_config
):
    mock_can_create_connection.return_value = True

    # Create updater after mocking can_create_connection
    updater = DnsServerZoneUpdater(
        min_interval=30, connection_timeout=5, config=basic_config
    )

    assert len(list(updater.zone.keys())) == 0

    total_ips = sum(len(record.healthy_ips) for record in basic_config.a_records)
    call_count = 0

    def should_abort_on_last_ip():
        nonlocal call_count
        call_count += 1

        return call_count == total_ips

    updater.update(should_abort=should_abort_on_last_ip)

    assert mock_can_create_connection.call_count == total_ips - 1

    assert len(list(updater.zone.keys())) == 0


@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.can_create_connection")
def test_update_for_the_first_time_without_dnssec_still_recreates_zone(
    mock_can_create_connection, basic_config
):
    def mock_connection_check(ip, port, timeout):
        return next(
            healthy_ip
            for records in basic_config.a_records
            for healthy_ip in records.healthy_ips
            if healthy_ip.ip == ip and healthy_ip.health_port == port
        ).is_healthy

    mock_can_create_connection.side_effect = mock_connection_check

    # Create updater after mocking can_create_connection
    updater = DnsServerZoneUpdater(
        min_interval=30, connection_timeout=5, config=basic_config
    )

    assert len(list(updater.zone.keys())) == 0

    updater.update()

    total_ips = sum(len(record.healthy_ips) for record in basic_config.a_records)
    assert mock_can_create_connection.call_count == total_ips

    assert len(list(updater.zone.keys())) > 0

    root_node = updater.zone.get_node(dns.name.empty)
    assert root_node is not None

    ns_rdataset = updater.zone.get_rdataset(dns.name.empty, dns.rdatatype.NS)
    assert ns_rdataset is not None

    soa_rdataset = updater.zone.get_rdataset(dns.name.empty, dns.rdatatype.SOA)
    assert soa_rdataset is not None

    for record in basic_config.a_records:
        a_rdataset = updater.zone.get_rdataset(record.subdomain, dns.rdatatype.A)
        ip_count = len([ip for ip in record.healthy_ips if ip.is_healthy])
        if ip_count == 0:
            assert a_rdataset is None
        else:
            assert a_rdataset is not None
            assert len(a_rdataset) == ip_count

    dnskey_rdataset = updater.zone.get_rdataset(dns.name.empty, dns.rdatatype.DNSKEY)
    assert dnskey_rdataset is None


@patch("indisoluble.a_healthy_dns.dns_server_zone_updater.can_create_connection")
def test_update_with_sign_near_to_expire_recreates_zone(
    mock_can_create_connection, config_with_dnssec
):
    def mock_connection_check(ip, port, timeout):
        return next(
            healthy_ip
            for records in config_with_dnssec.a_records
            for healthy_ip in records.healthy_ips
            if healthy_ip.ip == ip and healthy_ip.health_port == port
        ).is_healthy

    mock_can_create_connection.side_effect = mock_connection_check

    # Create updater after mocking can_create_connection
    updater = DnsServerZoneUpdater(
        min_interval=30, connection_timeout=5, config=config_with_dnssec
    )

    assert len(list(updater.zone.keys())) == 0

    with patch.object(updater, "_is_zone_sign_near_to_expire", return_value=True):
        updater.update()

    total_ips = sum(len(record.healthy_ips) for record in config_with_dnssec.a_records)
    assert mock_can_create_connection.call_count == total_ips

    assert len(list(updater.zone.keys())) > 0

    root_node = updater.zone.get_node(dns.name.empty)
    assert root_node is not None

    dnskey_rdataset = updater.zone.get_rdataset(dns.name.empty, dns.rdatatype.DNSKEY)
    dnskey_rrsig_rdatasets = _get_rrsig_rdatasets(root_node, dns.rdatatype.DNSKEY)
    assert dnskey_rdataset is not None
    assert len(dnskey_rdataset) == 1
    assert len(dnskey_rrsig_rdatasets) == 1
