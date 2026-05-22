#!/usr/bin/env python3

from typing import List
from unittest.mock import Mock, call, patch

import dns.dnssec
import dns.name
import dns.node
import dns.rdataset
import dns.rdatatype
import pytest

from dns.dnssecalgs.rsa import PrivateRSASHA256

from indisoluble.a_healthy_dns.dns_server_config_factory import DnsServerConfig
from indisoluble.a_healthy_dns.dns_server_zone_updater import DnsServerZoneUpdater
from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp
from indisoluble.a_healthy_dns.records.a_healthy_record import AHealthyRecord
from indisoluble.a_healthy_dns.records.dnssec import ExtendedPrivateKey
from indisoluble.a_healthy_dns.records.zone_origins import ZoneOrigins

_MIN_INTERVAL = 30
_CONNECTION_TIMEOUT = 5
_MAKE_NS_RECORD = "indisoluble.a_healthy_dns.dns_server_zone_updater.make_ns_record"
_ITER_SOA_RECORD = "indisoluble.a_healthy_dns.dns_server_zone_updater.iter_soa_record"
_ITER_RRSIG_KEY = "indisoluble.a_healthy_dns.dns_server_zone_updater.iter_rrsig_key"
_CAN_CREATE_CONNECTION = (
    "indisoluble.a_healthy_dns.dns_server_zone_updater.can_create_connection"
)
_UINT32_CURRENT_TIME = (
    "indisoluble.a_healthy_dns.records.soa_record.uint32_current_time"
)


def _get_rrsig_rdatasets(
    node: dns.node.Node, rdatatype: dns.rdatatype.RdataType
) -> List[dns.rdataset.Rdataset]:
    return [
        rd
        for rd in node.rdatasets
        if rd.rdtype == dns.rdatatype.RRSIG
        and any(rrsig.type_covered == rdatatype for rrsig in rd)
    ]


def _make_config(
    zone_origins,
    name_servers,
    a_records,
    ext_private_key=None,
):
    return DnsServerConfig(
        zone_origins=zone_origins,
        primary_name_server=name_servers[0],
        name_servers=frozenset(name_servers),
        a_records=frozenset(a_records),
        ext_private_key=ext_private_key,
    )


def _make_updater(config):
    return DnsServerZoneUpdater(
        min_interval=_MIN_INTERVAL,
        connection_timeout=_CONNECTION_TIMEOUT,
        config=config,
    )


def _healthy_ip_count(a_record):
    return len([ip for ip in a_record.healthy_ips if ip.is_healthy])


def _assert_apex_records_exist(zone, name_servers):
    ns_rdataset = zone.get_rdataset(dns.name.empty, dns.rdatatype.NS)
    soa_rdataset = zone.get_rdataset(dns.name.empty, dns.rdatatype.SOA)

    assert ns_rdataset is not None
    assert len(ns_rdataset) == len(name_servers)
    assert soa_rdataset is not None
    assert len(soa_rdataset) == 1


def _assert_a_records_match_health(zone, a_records):
    for a_record in a_records:
        a_rdataset = zone.get_rdataset(a_record.subdomain, dns.rdatatype.A)
        ip_count = _healthy_ip_count(a_record)

        if ip_count == 0:
            assert a_rdataset is None
        else:
            assert a_rdataset is not None
            assert len(a_rdataset) == ip_count


def _assert_rrsig_exists(node, rdatatype):
    rrsig_rdatasets = _get_rrsig_rdatasets(node, rdatatype)
    assert len(rrsig_rdatasets) == 1


def _connection_result_from_config(config, ip, port, timeout):
    assert timeout == float(_CONNECTION_TIMEOUT)
    return next(
        healthy_ip
        for record in config.a_records
        for healthy_ip in record.healthy_ips
        if healthy_ip.ip == ip and healthy_ip.health_port == port
    ).is_healthy


@pytest.fixture
def zone_origins():
    return ZoneOrigins("example.com", [])


@pytest.fixture
def a_record_all_ips_healthy(zone_origins):
    subdomain = dns.name.from_text("www", origin=zone_origins.primary)
    healthy_ips = [
        AHealthyIp(ip="192.168.1.1", health_port=8080, is_healthy=True),
        AHealthyIp(ip="192.168.1.2", health_port=8080, is_healthy=True),
    ]

    return AHealthyRecord(subdomain=subdomain, healthy_ips=healthy_ips)


@pytest.fixture
def a_record_ip_unhealthy(zone_origins):
    subdomain = dns.name.from_text("api", origin=zone_origins.primary)
    healthy_ips = [AHealthyIp(ip="192.168.1.3", health_port=8080, is_healthy=False)]

    return AHealthyRecord(subdomain=subdomain, healthy_ips=healthy_ips)


@pytest.fixture
def name_servers():
    return ["ns1.dns.example.net", "ns2.dns.example.net"]


@pytest.fixture
def ext_private_key():
    private_key = PrivateRSASHA256.generate(key_size=2048)
    dnskey = dns.dnssec.make_dnskey(private_key.public_key(), dns.dnssec.RSASHA256)

    return ExtendedPrivateKey(private_key=private_key, dnskey=dnskey)


@pytest.fixture
def mock_ext_private_key():
    return ExtendedPrivateKey(
        private_key=Mock(spec=dns.dnssec.PrivateKey),
        dnskey=Mock(spec=dns.dnssec.DNSKEY),
    )


@pytest.fixture
def basic_config(
    zone_origins, name_servers, a_record_all_ips_healthy, a_record_ip_unhealthy
):
    return _make_config(
        zone_origins,
        name_servers,
        [a_record_all_ips_healthy, a_record_ip_unhealthy],
    )


@pytest.fixture
def config_with_dnssec(
    zone_origins,
    name_servers,
    a_record_all_ips_healthy,
    a_record_ip_unhealthy,
    ext_private_key,
):
    return _make_config(
        zone_origins,
        name_servers,
        [a_record_all_ips_healthy, a_record_ip_unhealthy],
        ext_private_key=ext_private_key,
    )


@pytest.fixture
def config_with_mock_dnssec(
    zone_origins,
    name_servers,
    a_record_all_ips_healthy,
    a_record_ip_unhealthy,
    mock_ext_private_key,
):
    return _make_config(
        zone_origins,
        name_servers,
        [a_record_all_ips_healthy, a_record_ip_unhealthy],
        ext_private_key=mock_ext_private_key,
    )


@pytest.fixture
def updater_no_dnssec(basic_config):
    return _make_updater(basic_config)


@pytest.fixture
def updater_with_dnssec(config_with_dnssec):
    return _make_updater(config_with_dnssec)


class TestInitializationValidation:
    @pytest.mark.parametrize("min_interval", [0, -1])
    def test_rejects_non_positive_min_interval(self, min_interval, basic_config):
        with pytest.raises(ValueError, match="Minimum interval must be positive"):
            DnsServerZoneUpdater(
                min_interval=min_interval,
                connection_timeout=_CONNECTION_TIMEOUT,
                config=basic_config,
            )

    @pytest.mark.parametrize("connection_timeout", [0, -1])
    def test_rejects_non_positive_connection_timeout(
        self, connection_timeout, basic_config
    ):
        with pytest.raises(ValueError, match="Connection timeout must be positive"):
            DnsServerZoneUpdater(
                min_interval=_MIN_INTERVAL,
                connection_timeout=connection_timeout,
                config=basic_config,
            )


class TestInitializationWiring:
    @patch(_MAKE_NS_RECORD)
    @patch(_ITER_SOA_RECORD)
    @patch(_ITER_RRSIG_KEY)
    def test_prepares_zone_records_without_dnssec(
        self,
        mock_iter_rrsig_key,
        mock_iter_soa_record,
        mock_make_ns_record,
        basic_config,
    ):
        mock_make_ns_record.return_value = Mock()
        mock_iter_soa_record.return_value = iter([Mock()])

        updater = _make_updater(basic_config)

        assert updater.zone.origin == basic_config.zone_origins.primary
        assert len(list(updater.zone.keys())) == 0
        mock_make_ns_record.assert_called_once_with(
            _MIN_INTERVAL, basic_config.name_servers
        )
        mock_iter_soa_record.assert_called_once_with(
            _MIN_INTERVAL,
            basic_config.zone_origins.primary,
            basic_config.primary_name_server,
        )
        mock_iter_rrsig_key.assert_not_called()

    @patch(_MAKE_NS_RECORD)
    @patch(_ITER_SOA_RECORD)
    @patch(_ITER_RRSIG_KEY)
    def test_prepares_zone_records_with_dnssec(
        self,
        mock_iter_rrsig_key,
        mock_iter_soa_record,
        mock_make_ns_record,
        config_with_mock_dnssec,
    ):
        mock_make_ns_record.return_value = Mock()
        mock_iter_soa_record.return_value = iter([Mock()])
        mock_iter_rrsig_key.return_value = iter([Mock()])

        updater = _make_updater(config_with_mock_dnssec)

        assert updater.zone.origin == config_with_mock_dnssec.zone_origins.primary
        assert len(list(updater.zone.keys())) == 0
        mock_make_ns_record.assert_called_once_with(
            _MIN_INTERVAL, config_with_mock_dnssec.name_servers
        )
        mock_iter_soa_record.assert_called_once_with(
            _MIN_INTERVAL,
            config_with_mock_dnssec.zone_origins.primary,
            config_with_mock_dnssec.primary_name_server,
        )
        mock_iter_rrsig_key.assert_called_once_with(
            _MIN_INTERVAL, config_with_mock_dnssec.ext_private_key
        )

    @patch(_MAKE_NS_RECORD)
    @patch(_ITER_SOA_RECORD)
    @patch(_ITER_RRSIG_KEY)
    def test_uses_calculated_interval_when_work_can_exceed_minimum(
        self,
        mock_iter_rrsig_key,
        mock_iter_soa_record,
        mock_make_ns_record,
        config_with_mock_dnssec,
    ):
        mock_make_ns_record.return_value = Mock()
        mock_iter_soa_record.return_value = iter([Mock()])
        mock_iter_rrsig_key.return_value = iter([Mock()])
        expected_interval = 21

        DnsServerZoneUpdater(
            min_interval=1,
            connection_timeout=_CONNECTION_TIMEOUT,
            config=config_with_mock_dnssec,
        )

        mock_make_ns_record.assert_called_once_with(
            expected_interval, config_with_mock_dnssec.name_servers
        )
        mock_iter_soa_record.assert_called_once_with(
            expected_interval,
            config_with_mock_dnssec.zone_origins.primary,
            config_with_mock_dnssec.primary_name_server,
        )
        mock_iter_rrsig_key.assert_called_once_with(
            expected_interval, config_with_mock_dnssec.ext_private_key
        )


class TestInitializeZone:
    def test_creates_apex_records_and_healthy_a_records(
        self,
        updater_no_dnssec,
        name_servers,
        a_record_all_ips_healthy,
        a_record_ip_unhealthy,
    ):
        assert len(list(updater_no_dnssec.zone.keys())) == 0

        updater_no_dnssec.initialize_zone()

        assert len(list(updater_no_dnssec.zone.keys())) > 0
        _assert_apex_records_exist(updater_no_dnssec.zone, name_servers)
        _assert_a_records_match_health(
            updater_no_dnssec.zone,
            [a_record_all_ips_healthy, a_record_ip_unhealthy],
        )

    def test_creates_dnssec_records_and_signatures(
        self,
        updater_with_dnssec,
        name_servers,
        a_record_all_ips_healthy,
        a_record_ip_unhealthy,
    ):
        assert len(list(updater_with_dnssec.zone.keys())) == 0

        updater_with_dnssec.initialize_zone()

        assert len(list(updater_with_dnssec.zone.keys())) > 0
        root_node = updater_with_dnssec.zone.get_node(dns.name.empty)
        assert root_node is not None

        _assert_apex_records_exist(updater_with_dnssec.zone, name_servers)
        _assert_rrsig_exists(root_node, dns.rdatatype.NS)
        _assert_rrsig_exists(root_node, dns.rdatatype.SOA)

        dnskey_rdataset = updater_with_dnssec.zone.get_rdataset(
            dns.name.empty, dns.rdatatype.DNSKEY
        )
        nsec_rdataset = updater_with_dnssec.zone.get_rdataset(
            dns.name.empty, dns.rdatatype.NSEC
        )
        assert dnskey_rdataset is not None
        assert len(dnskey_rdataset) == 1
        assert nsec_rdataset is not None
        assert len(nsec_rdataset) == 1
        _assert_rrsig_exists(root_node, dns.rdatatype.DNSKEY)
        _assert_rrsig_exists(root_node, dns.rdatatype.NSEC)

        for a_record in (a_record_all_ips_healthy, a_record_ip_unhealthy):
            a_rdataset = updater_with_dnssec.zone.get_rdataset(
                a_record.subdomain, dns.rdatatype.A
            )
            ip_count = _healthy_ip_count(a_record)

            if ip_count == 0:
                assert a_rdataset is None
                assert updater_with_dnssec.zone.get_node(a_record.subdomain) is None
            else:
                assert a_rdataset is not None
                assert len(a_rdataset) == ip_count

                a_node = updater_with_dnssec.zone.get_node(a_record.subdomain)
                assert a_node is not None
                _assert_rrsig_exists(a_node, dns.rdatatype.A)

                a_nsec_rdataset = updater_with_dnssec.zone.get_rdataset(
                    a_record.subdomain, dns.rdatatype.NSEC
                )
                assert a_nsec_rdataset is not None
                assert len(a_nsec_rdataset) == 1
                _assert_rrsig_exists(a_node, dns.rdatatype.NSEC)

    def test_skips_a_record_when_no_ips_are_healthy(
        self, zone_origins, name_servers, a_record_ip_unhealthy
    ):
        updater = _make_updater(
            _make_config(zone_origins, name_servers, [a_record_ip_unhealthy])
        )

        updater.initialize_zone()

        _assert_apex_records_exist(updater.zone, name_servers)
        assert (
            updater.zone.get_rdataset(a_record_ip_unhealthy.subdomain, dns.rdatatype.A)
            is None
        )

    @patch(_UINT32_CURRENT_TIME)
    def test_replaces_existing_zone_records_when_initialized_twice(
        self,
        mock_time,
        updater_no_dnssec,
        name_servers,
        a_record_all_ips_healthy,
        a_record_ip_unhealthy,
    ):
        timestamps = [1000, 1001]
        a_records = [a_record_all_ips_healthy, a_record_ip_unhealthy]
        mock_time.side_effect = timestamps

        updater_no_dnssec.initialize_zone()

        first_ns_rdataset = updater_no_dnssec.zone.get_rdataset(
            dns.name.empty, dns.rdatatype.NS
        )
        first_soa_rdataset = updater_no_dnssec.zone.get_rdataset(
            dns.name.empty, dns.rdatatype.SOA
        )
        first_a_records = {
            record.subdomain: updater_no_dnssec.zone.get_rdataset(
                record.subdomain, dns.rdatatype.A
            )
            for record in a_records
        }
        _assert_apex_records_exist(updater_no_dnssec.zone, name_servers)
        _assert_a_records_match_health(updater_no_dnssec.zone, a_records)
        assert first_soa_rdataset[0].serial == timestamps[0]

        updater_no_dnssec.initialize_zone()

        second_ns_rdataset = updater_no_dnssec.zone.get_rdataset(
            dns.name.empty, dns.rdatatype.NS
        )
        second_soa_rdataset = updater_no_dnssec.zone.get_rdataset(
            dns.name.empty, dns.rdatatype.SOA
        )
        second_a_records = {
            record.subdomain: updater_no_dnssec.zone.get_rdataset(
                record.subdomain, dns.rdatatype.A
            )
            for record in a_records
        }

        assert second_ns_rdataset == first_ns_rdataset
        assert second_soa_rdataset is not None
        assert len(second_soa_rdataset) == 1
        assert second_soa_rdataset[0].serial == timestamps[1]
        assert second_a_records == first_a_records


class TestUpdateRefresh:
    @pytest.mark.parametrize(
        "can_create_connection_value",
        [
            True,
            False,
        ],
    )
    @patch(_CAN_CREATE_CONNECTION)
    def test_updates_health_statuses_from_connection_checks(
        self, mock_can_create_connection, can_create_connection_value, basic_config
    ):
        mock_can_create_connection.return_value = can_create_connection_value
        updater = _make_updater(basic_config)

        updater.update(should_abort=lambda: False)

        expected_calls = [
            call(
                healthy_ip.ip,
                healthy_ip.health_port,
                timeout=float(_CONNECTION_TIMEOUT),
            )
            for record in basic_config.a_records
            for healthy_ip in record.healthy_ips
        ]
        mock_can_create_connection.assert_has_calls(expected_calls, any_order=True)
        assert mock_can_create_connection.call_count == len(expected_calls)

        for record in basic_config.a_records:
            a_rdataset = updater.zone.get_rdataset(record.subdomain, dns.rdatatype.A)
            if can_create_connection_value:
                assert a_rdataset is not None
            else:
                assert a_rdataset is None

    @patch(_CAN_CREATE_CONNECTION)
    def test_keeps_zone_unchanged_when_abort_happens_before_last_check(
        self, mock_can_create_connection, basic_config
    ):
        mock_can_create_connection.return_value = True
        updater = _make_updater(basic_config)
        total_ips = sum(len(record.healthy_ips) for record in basic_config.a_records)
        should_abort_call_count = 0

        def should_abort_on_last_ip():
            nonlocal should_abort_call_count
            should_abort_call_count += 1
            return should_abort_call_count == total_ips

        updater.update(should_abort=should_abort_on_last_ip)

        assert mock_can_create_connection.call_count == total_ips - 1
        assert len(list(updater.zone.keys())) == 0

    @patch(_CAN_CREATE_CONNECTION)
    def test_first_update_recreates_zone_even_without_health_changes(
        self, mock_can_create_connection, basic_config, name_servers
    ):
        mock_can_create_connection.side_effect = lambda ip, port, timeout: (
            _connection_result_from_config(basic_config, ip, port, timeout)
        )
        updater = _make_updater(basic_config)

        updater.update()

        total_ips = sum(len(record.healthy_ips) for record in basic_config.a_records)
        assert mock_can_create_connection.call_count == total_ips
        _assert_apex_records_exist(updater.zone, name_servers)
        _assert_a_records_match_health(updater.zone, basic_config.a_records)
        assert updater.zone.get_rdataset(dns.name.empty, dns.rdatatype.DNSKEY) is None

    @patch(_CAN_CREATE_CONNECTION)
    def test_recreates_dnssec_zone_when_signature_is_near_expiration(
        self, mock_can_create_connection, config_with_dnssec
    ):
        mock_can_create_connection.side_effect = lambda ip, port, timeout: (
            _connection_result_from_config(config_with_dnssec, ip, port, timeout)
        )
        updater = _make_updater(config_with_dnssec)

        with patch.object(updater, "_is_zone_sign_near_to_expire", return_value=True):
            updater.update()

        total_ips = sum(
            len(record.healthy_ips) for record in config_with_dnssec.a_records
        )
        root_node = updater.zone.get_node(dns.name.empty)
        dnskey_rdataset = updater.zone.get_rdataset(
            dns.name.empty, dns.rdatatype.DNSKEY
        )

        assert mock_can_create_connection.call_count == total_ips
        assert root_node is not None
        assert dnskey_rdataset is not None
        assert len(dnskey_rdataset) == 1
        _assert_rrsig_exists(root_node, dns.rdatatype.DNSKEY)


class TestStaticARecords:
    @pytest.mark.parametrize(
        "ip_addresses",
        [
            ["10.0.0.1"],
            ["10.0.0.1", "10.0.0.2"],
        ],
    )
    @patch(_CAN_CREATE_CONNECTION)
    def test_ips_without_health_port_skip_tcp_check_and_appear_in_zone(
        self, mock_can_create_connection, ip_addresses, zone_origins, name_servers
    ):
        subdomain = dns.name.from_text("static", origin=zone_origins.primary)
        ips = [
            AHealthyIp(ip=addr, health_port=None, is_healthy=False)
            for addr in ip_addresses
        ]
        a_record = AHealthyRecord(subdomain=subdomain, healthy_ips=ips)
        updater = _make_updater(_make_config(zone_origins, name_servers, [a_record]))

        updater.update()

        mock_can_create_connection.assert_not_called()
        a_rdataset = updater.zone.get_rdataset(subdomain, dns.rdatatype.A)
        assert a_rdataset is not None
        assert len(a_rdataset) == len(ip_addresses)
