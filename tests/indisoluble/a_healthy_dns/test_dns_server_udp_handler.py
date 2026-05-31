#!/usr/bin/env python3

import logging

import dns.exception
import dns.flags
import dns.message
import dns.name
import dns.opcode
import dns.rcode
import dns.rdataclass
import dns.rdatatype
import dns.rdataset
import dns.update
import pytest

from unittest.mock import MagicMock, patch

from indisoluble.a_healthy_dns.dns_server_udp_handler import (
    _CLASSIC_UDP_PAYLOAD_SIZE,
    _DNS_TRAFFIC_JUNK,
    _DNS_TRAFFIC_NOISE,
    _DNS_TRAFFIC_NORMAL,
    _DNS_TRAFFIC_SUSPICIOUS,
    _RFC8482_HINFO_CPU,
    _RFC8482_HINFO_OS,
    DnsServerUdpHandler,
)
from indisoluble.a_healthy_dns.dns_server_config_factory import DnsServerConfig
from indisoluble.a_healthy_dns.dns_server_zone_updater import DnsServerZoneUpdater
from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp
from indisoluble.a_healthy_dns.records.a_healthy_record import AHealthyRecord
from indisoluble.a_healthy_dns.records.zone_origins import ZoneOrigins

# Captured before any test patches dns.message.from_wire so we can still parse
# response wire bytes inside tests that mock from_wire.
_real_from_wire = dns.message.from_wire

_TEST_QUERY_ID = 13551
_TEST_SOURCE_HOST = "127.0.0.1"
_TEST_SOURCE_PORT = 12345
_SOA_MNAME = "ns1.example.com."
_SOA_RNAME = "hostmaster.example.com."
_SOA_SERIAL = 1
_SOA_REFRESH = 7200
_SOA_RETRY = 3600
_SOA_EXPIRE = 1209600


class _FakeNode:
    def __init__(self, *rdatasets):
        self._rdatasets = {
            (rdataset.rdclass, rdataset.rdtype): rdataset for rdataset in rdatasets
        }

    def get_rdataset(self, rdclass, rdtype):
        return self._rdatasets.get((rdclass, rdtype))


class _FakeReaderContext:
    def __init__(self, transaction):
        self._transaction = transaction

    # Implements context manager protocol.
    def __enter__(self):
        return self._transaction

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class _FakeTransaction:
    def __init__(self, *, nodes=None, soa_rdataset=None, names=None):
        self._nodes = nodes or {}
        self._soa_rdataset = soa_rdataset
        self._names = list(self._nodes) if names is None else list(names)

    def get_node(self, name):
        return self._nodes.get(name)

    def get(self, name, rdtype):
        if name == dns.name.empty and rdtype == dns.rdatatype.SOA:
            return self._soa_rdataset

        return None

    def iterate_names(self):
        return iter(self._names)


class _FakeZone:
    rdclass = dns.rdataclass.IN

    def __init__(self, origin, transaction):
        self.origin = origin
        self.reader_calls = 0
        self._transaction = transaction

    def reader(self):
        self.reader_calls += 1
        return _FakeReaderContext(self._transaction)


def _make_multi_question_wire(*question_names):
    queries = [
        dns.message.make_query(question_name, dns.rdatatype.A)
        for question_name in question_names
    ]

    wire = bytearray(queries[0].to_wire())
    wire[4:6] = len(queries).to_bytes(2, byteorder="big")

    for query in queries[1:]:
        wire.extend(query.to_wire()[12:])

    return bytes(wire)


def _make_query_with_opcode(opcode):
    query = dns.message.make_query("test.example.com.", dns.rdatatype.A)
    query.set_opcode(opcode)
    return query


def _make_update_query():
    query = dns.update.Update("example.com.")
    query.add("www", 300, "A", "192.0.2.1")
    return query


def _make_a_rdataset(*ip_addresses, ttl=300):
    return dns.rdataset.from_text(
        dns.rdataclass.IN, dns.rdatatype.A, ttl, *ip_addresses
    )


def _make_soa_rdataset(*, ttl=300, minimum=60):
    return dns.rdataset.from_text(
        dns.rdataclass.IN,
        dns.rdatatype.SOA,
        ttl,
        (
            f"{_SOA_MNAME} {_SOA_RNAME} {_SOA_SERIAL} {_SOA_REFRESH} "
            f"{_SOA_RETRY} {_SOA_EXPIRE} {minimum}"
        ),
    )


def _soa_authority_ttl(soa_rdataset):
    return min(soa_rdataset.ttl, next(iter(soa_rdataset)).minimum)


def _make_hinfo_rdataset(ttl):
    return dns.rdataset.from_text(
        dns.rdataclass.IN,
        dns.rdatatype.HINFO,
        ttl,
        f'"{_RFC8482_HINFO_CPU}" "{_RFC8482_HINFO_OS}"',
    )


def _make_zone(zone_origins, transaction):
    return _FakeZone(zone_origins.primary, transaction)


def _make_server(zone, zone_origins):
    server = MagicMock()
    server.zone = zone
    server.zone_origins = zone_origins
    return server


def _make_handler(zone, zone_origins):
    handler = object.__new__(DnsServerUdpHandler)
    handler.server = _make_server(zone, zone_origins)
    handler.client_address = (_TEST_SOURCE_HOST, _TEST_SOURCE_PORT)
    return handler


def _make_request(wire_data):
    mock_sock = MagicMock()
    return (wire_data, mock_sock), mock_sock


def _handle_wire(wire_data, client_address, server):
    request, mock_sock = _make_request(wire_data)
    DnsServerUdpHandler(request, client_address, server)
    return mock_sock


def _sent_wire(mock_sock, client_address):
    mock_sock.sendto.assert_called_once()
    sent_wire, destination = mock_sock.sendto.call_args[0]
    assert destination == client_address
    return sent_wire


def _sent_response(mock_sock, client_address, from_wire=dns.message.from_wire):
    return from_wire(_sent_wire(mock_sock, client_address))


def _update_test_response(response, query_name, query_type, zone, zone_origins):
    question = dns.message.make_query(query_name, query_type).question[0]
    _make_handler(zone, zone_origins)._update_response(
        response, question, _TEST_QUERY_ID
    )


def _assert_log_record(caplog, level, message_fragment, traffic_marker=None):
    assert any(
        record.levelno == level
        and message_fragment in record.getMessage()
        and (traffic_marker is None or traffic_marker in record.getMessage())
        for record in caplog.records
    )


def _assert_log_context(caplog, *, query_id=_TEST_QUERY_ID):
    assert f"source={_TEST_SOURCE_HOST}:{_TEST_SOURCE_PORT}" in caplog.text
    assert f"id={query_id}" in caplog.text


def _assert_section_counts(response, *, additional=0, authority=0, answer=0):
    assert len(response.additional) == additional
    assert len(response.authority) == authority
    assert len(response.answer) == answer


def _assert_response_header(
    response,
    *,
    query_id,
    rcode,
    aa,
    tc=False,
    opcode=None,
    rd=None,
):
    assert response.id == query_id
    assert response.rcode() == rcode
    assert bool(response.flags & dns.flags.QR)
    assert bool(response.flags & dns.flags.AA) == aa
    assert bool(response.flags & dns.flags.TC) == tc
    assert not bool(response.flags & dns.flags.RA)

    if opcode is not None:
        assert response.opcode() == opcode

    if rd is not None:
        assert bool(response.flags & dns.flags.RD) == rd


def _assert_answer_rrset(response, *, name, rdtype, rdataset):
    _assert_section_counts(response, answer=1)
    assert response.answer[0].name == name
    assert response.answer[0].rdclass == rdataset.rdclass
    assert response.answer[0].rdtype == rdtype
    assert response.answer[0].ttl == rdataset.ttl
    assert set(response.answer[0]) == set(rdataset)


def _assert_soa_authority(response, *, name, expected_ttl):
    assert len(response.authority) == 1
    assert response.authority[0].name == name
    assert response.authority[0].rdclass == dns.rdataclass.IN
    assert response.authority[0].rdtype == dns.rdatatype.SOA
    assert response.authority[0].ttl == expected_ttl


def _assert_no_authority_or_additional(response):
    assert len(response.additional) == 0
    assert len(response.authority) == 0


@pytest.fixture
def zone_origins():
    return ZoneOrigins("example.com", [])


@pytest.fixture
def dns_response():
    return dns.message.make_response(dns.message.make_query("dummy", dns.rdatatype.A))


@pytest.fixture
def dns_client_address():
    return (_TEST_SOURCE_HOST, _TEST_SOURCE_PORT)


@pytest.fixture
def dns_request():
    query = dns.message.make_query("test.example.com.", dns.rdatatype.A)
    return _make_request(query.to_wire())[0]


@pytest.fixture
def soa_rdataset():
    return _make_soa_rdataset()


class TestUpdateResponse:
    def test_relative_name_found_returns_authoritative_answer(
        self, dns_response, zone_origins, caplog
    ):
        query_name = dns.name.from_text("test", origin=None)
        rdataset = _make_a_rdataset("192.0.2.1")
        transaction = _FakeTransaction(
            nodes={dns.name.from_text("test", origin=None): _FakeNode(rdataset)}
        )
        zone = _make_zone(zone_origins, transaction)

        with caplog.at_level(logging.INFO):
            _update_test_response(
                dns_response, query_name, dns.rdatatype.A, zone, zone_origins
            )

        assert zone.reader_calls == 1
        assert dns_response.rcode() == dns.rcode.NOERROR
        assert bool(dns_response.flags & dns.flags.AA)
        _assert_no_authority_or_additional(dns_response)
        _assert_answer_rrset(
            dns_response,
            name=query_name,
            rdtype=dns.rdatatype.A,
            rdataset=rdataset,
        )

        _assert_log_record(
            caplog,
            logging.INFO,
            "Answered DNS query from hosted zone",
            _DNS_TRAFFIC_NORMAL,
        )
        _assert_log_context(caplog)
        assert "qname=test" in caplog.text
        assert "qtype=A" in caplog.text

    def test_absolute_name_found_relativizes_lookup_and_preserves_answer_name(
        self, dns_response, zone_origins
    ):
        query_name = dns.name.from_text("test", origin=zone_origins.primary)
        rdataset = _make_a_rdataset("192.0.2.1")
        transaction = _FakeTransaction(
            nodes={dns.name.from_text("test", origin=None): _FakeNode(rdataset)}
        )
        zone = _make_zone(zone_origins, transaction)

        _update_test_response(
            dns_response, query_name, dns.rdatatype.A, zone, zone_origins
        )

        assert dns_response.rcode() == dns.rcode.NOERROR
        assert bool(dns_response.flags & dns.flags.AA)
        _assert_no_authority_or_additional(dns_response)
        _assert_answer_rrset(
            dns_response,
            name=query_name,
            rdtype=dns.rdatatype.A,
            rdataset=rdataset,
        )

    def test_multiple_rdata_values_are_preserved_in_answer(
        self, dns_response, zone_origins
    ):
        query_name = dns.name.from_text("many", origin=zone_origins.primary)
        rdataset = _make_a_rdataset("192.0.2.1", "192.0.2.2", "192.0.2.3")
        transaction = _FakeTransaction(
            nodes={dns.name.from_text("many", origin=None): _FakeNode(rdataset)}
        )
        zone = _make_zone(zone_origins, transaction)

        _update_test_response(
            dns_response, query_name, dns.rdatatype.A, zone, zone_origins
        )

        assert dns_response.rcode() == dns.rcode.NOERROR
        assert bool(dns_response.flags & dns.flags.AA)
        _assert_answer_rrset(
            dns_response,
            name=query_name,
            rdtype=dns.rdatatype.A,
            rdataset=rdataset,
        )

    def test_any_query_at_existing_owner_returns_synthesized_hinfo(
        self, dns_response, zone_origins, caplog
    ):
        query_name = dns.name.from_text("test", origin=zone_origins.primary)
        a_rdataset = _make_a_rdataset("192.0.2.1")
        soa_rdataset = _make_soa_rdataset(ttl=30, minimum=60)
        hinfo_rdataset = _make_hinfo_rdataset(_soa_authority_ttl(soa_rdataset))
        transaction = _FakeTransaction(
            nodes={dns.name.from_text("test", origin=None): _FakeNode(a_rdataset)},
            soa_rdataset=soa_rdataset,
        )
        zone = _make_zone(zone_origins, transaction)

        with caplog.at_level(logging.INFO):
            _update_test_response(
                dns_response,
                query_name,
                dns.rdatatype.ANY,
                zone,
                zone_origins,
            )

        assert dns_response.rcode() == dns.rcode.NOERROR
        assert bool(dns_response.flags & dns.flags.AA)
        _assert_no_authority_or_additional(dns_response)
        _assert_answer_rrset(
            dns_response,
            name=query_name,
            rdtype=dns.rdatatype.HINFO,
            rdataset=hinfo_rdataset,
        )

        _assert_log_record(
            caplog,
            logging.INFO,
            "Answered RFC 8482 ANY query with synthesized HINFO",
            _DNS_TRAFFIC_NORMAL,
        )

    def test_any_query_at_empty_non_terminal_returns_synthesized_hinfo(
        self, dns_response, zone_origins, soa_rdataset, caplog
    ):
        query_name = dns.name.from_text("empty", origin=zone_origins.primary)
        hinfo_rdataset = _make_hinfo_rdataset(_soa_authority_ttl(soa_rdataset))
        transaction = _FakeTransaction(
            soa_rdataset=soa_rdataset,
            names=[dns.name.from_text("leaf.empty", origin=None)],
        )
        zone = _make_zone(zone_origins, transaction)

        with caplog.at_level(logging.INFO):
            _update_test_response(
                dns_response,
                query_name,
                dns.rdatatype.ANY,
                zone,
                zone_origins,
            )

        assert dns_response.rcode() == dns.rcode.NOERROR
        assert bool(dns_response.flags & dns.flags.AA)
        _assert_no_authority_or_additional(dns_response)
        _assert_answer_rrset(
            dns_response,
            name=query_name,
            rdtype=dns.rdatatype.HINFO,
            rdataset=hinfo_rdataset,
        )

        _assert_log_record(
            caplog,
            logging.INFO,
            "Answered RFC 8482 ANY query for empty non-terminal",
            _DNS_TRAFFIC_NORMAL,
        )

    def test_any_query_at_absent_owner_returns_nxdomain_with_soa_authority(
        self, dns_response, zone_origins, soa_rdataset
    ):
        query_name = dns.name.from_text("nonexistent", origin=zone_origins.primary)
        transaction = _FakeTransaction(soa_rdataset=soa_rdataset)
        zone = _make_zone(zone_origins, transaction)

        _update_test_response(
            dns_response, query_name, dns.rdatatype.ANY, zone, zone_origins
        )

        assert dns_response.rcode() == dns.rcode.NXDOMAIN
        assert bool(dns_response.flags & dns.flags.AA)
        assert len(dns_response.answer) == 0
        _assert_soa_authority(
            dns_response,
            name=zone_origins.primary,
            expected_ttl=next(iter(soa_rdataset)).minimum,
        )

    def test_any_query_at_alias_owner_preserves_alias_answer_name(
        self, dns_response, soa_rdataset
    ):
        zone_origins = ZoneOrigins("example.com", ["alias.example.net"])
        query_name = dns.name.from_text("test.alias.example.net.")
        a_rdataset = _make_a_rdataset("192.0.2.1")
        hinfo_rdataset = _make_hinfo_rdataset(_soa_authority_ttl(soa_rdataset))
        transaction = _FakeTransaction(
            nodes={dns.name.from_text("test", origin=None): _FakeNode(a_rdataset)},
            soa_rdataset=soa_rdataset,
        )
        zone = _make_zone(zone_origins, transaction)

        _update_test_response(
            dns_response,
            query_name,
            dns.rdatatype.ANY,
            zone,
            zone_origins,
        )

        assert dns_response.rcode() == dns.rcode.NOERROR
        assert bool(dns_response.flags & dns.flags.AA)
        _assert_answer_rrset(
            dns_response,
            name=query_name,
            rdtype=dns.rdatatype.HINFO,
            rdataset=hinfo_rdataset,
        )

    def test_absolute_name_outside_zone_origins_returns_refused_without_zone_lookup(
        self, dns_response, zone_origins, caplog
    ):
        query_name = dns.name.from_text("test", origin=dns.name.from_text("other.com"))
        transaction = _FakeTransaction()
        zone = _make_zone(zone_origins, transaction)

        with caplog.at_level(logging.INFO):
            _update_test_response(
                dns_response, query_name, dns.rdatatype.A, zone, zone_origins
            )

        assert zone.reader_calls == 0
        assert dns_response.rcode() == dns.rcode.REFUSED
        assert not bool(dns_response.flags & dns.flags.AA)
        _assert_section_counts(dns_response)

        _assert_log_record(
            caplog,
            logging.INFO,
            "Refused DNS query outside hosted or alias zones",
            _DNS_TRAFFIC_NOISE,
        )
        _assert_log_context(caplog)

    def test_domain_not_found_returns_nxdomain_with_soa_authority(
        self, dns_response, zone_origins, soa_rdataset, caplog
    ):
        query_name = dns.name.from_text("nonexistent", origin=zone_origins.primary)
        transaction = _FakeTransaction(soa_rdataset=soa_rdataset)
        zone = _make_zone(zone_origins, transaction)

        with caplog.at_level(logging.INFO):
            _update_test_response(
                dns_response, query_name, dns.rdatatype.A, zone, zone_origins
            )

        assert dns_response.rcode() == dns.rcode.NXDOMAIN
        assert bool(dns_response.flags & dns.flags.AA)
        assert len(dns_response.answer) == 0
        assert len(dns_response.additional) == 0
        _assert_soa_authority(
            dns_response,
            name=zone_origins.primary,
            expected_ttl=next(iter(soa_rdataset)).minimum,
        )

        _assert_log_record(
            caplog, logging.INFO, "returning NXDOMAIN", _DNS_TRAFFIC_NORMAL
        )
        _assert_log_context(caplog)

    def test_negative_response_uses_lower_of_soa_ttl_and_minimum(
        self, dns_response, zone_origins
    ):
        query_name = dns.name.from_text("nonexistent", origin=zone_origins.primary)
        soa_rdataset = _make_soa_rdataset(ttl=30, minimum=60)
        transaction = _FakeTransaction(soa_rdataset=soa_rdataset)
        zone = _make_zone(zone_origins, transaction)

        _update_test_response(
            dns_response, query_name, dns.rdatatype.A, zone, zone_origins
        )

        assert dns_response.rcode() == dns.rcode.NXDOMAIN
        _assert_soa_authority(
            dns_response,
            name=zone_origins.primary,
            expected_ttl=30,
        )

    def test_empty_non_terminal_returns_nodata_with_soa_authority(
        self, dns_response, zone_origins, soa_rdataset, caplog
    ):
        query_name = dns.name.from_text("empty", origin=zone_origins.primary)
        transaction = _FakeTransaction(
            soa_rdataset=soa_rdataset,
            names=[dns.name.from_text("leaf.empty", origin=None)],
        )
        zone = _make_zone(zone_origins, transaction)

        with caplog.at_level(logging.INFO):
            _update_test_response(
                dns_response, query_name, dns.rdatatype.A, zone, zone_origins
            )

        assert dns_response.rcode() == dns.rcode.NOERROR
        assert bool(dns_response.flags & dns.flags.AA)
        assert len(dns_response.answer) == 0
        _assert_soa_authority(
            dns_response,
            name=zone_origins.primary,
            expected_ttl=next(iter(soa_rdataset)).minimum,
        )

        _assert_log_record(
            caplog, logging.INFO, "returning NODATA", _DNS_TRAFFIC_NORMAL
        )

    @pytest.mark.parametrize(
        "soa_rdataset",
        [
            None,
            dns.rdataset.from_text(
                dns.rdataclass.IN,
                dns.rdatatype.SOA,
                300,
            ),
        ],
        ids=["missing-soa-rdataset", "empty-soa-rdataset"],
    )
    def test_domain_not_found_without_usable_soa_omits_authority(
        self, dns_response, zone_origins, soa_rdataset
    ):
        query_name = dns.name.from_text("nonexistent", origin=zone_origins.primary)
        transaction = _FakeTransaction(soa_rdataset=soa_rdataset)
        zone = _make_zone(zone_origins, transaction)

        _update_test_response(
            dns_response, query_name, dns.rdatatype.A, zone, zone_origins
        )

        assert dns_response.rcode() == dns.rcode.NXDOMAIN
        assert bool(dns_response.flags & dns.flags.AA)
        _assert_section_counts(dns_response)

    def test_record_type_not_found_returns_nodata_with_soa_authority(
        self, dns_response, zone_origins, soa_rdataset, caplog
    ):
        query_name = dns.name.from_text("test", origin=zone_origins.primary)
        transaction = _FakeTransaction(
            nodes={dns.name.from_text("test", origin=None): _FakeNode()},
            soa_rdataset=soa_rdataset,
        )
        zone = _make_zone(zone_origins, transaction)

        with caplog.at_level(logging.INFO):
            _update_test_response(
                dns_response, query_name, dns.rdatatype.A, zone, zone_origins
            )

        assert dns_response.rcode() == dns.rcode.NOERROR
        assert bool(dns_response.flags & dns.flags.AA)
        assert len(dns_response.answer) == 0
        assert len(dns_response.additional) == 0
        _assert_soa_authority(
            dns_response,
            name=zone_origins.primary,
            expected_ttl=next(iter(soa_rdataset)).minimum,
        )

        _assert_log_record(
            caplog, logging.INFO, "returning NODATA", _DNS_TRAFFIC_NORMAL
        )
        _assert_log_context(caplog)


class TestHandlerValidQuery:
    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_valid_query_calls_update_response_and_sends_response_to_client(
        self, mock_update_response, dns_request, dns_client_address, zone_origins
    ):
        zone = _make_zone(zone_origins, _FakeTransaction())
        server = _make_server(zone, zone_origins)
        mock_update_response.side_effect = lambda response, *args: setattr(
            response, "flags", response.flags | dns.flags.AA
        )

        DnsServerUdpHandler(dns_request, dns_client_address, server)

        query_data, mock_sock = dns_request
        query = dns.message.from_wire(query_data)
        question = query.question[0]
        call_args = mock_update_response.call_args[0]

        mock_update_response.assert_called_once()
        assert call_args[1] == question
        assert call_args[2] == query.id

        response = _sent_response(mock_sock, dns_client_address)
        _assert_response_header(
            response,
            query_id=query.id,
            rcode=dns.rcode.NOERROR,
            aa=True,
        )


class TestHandlerUdpWireEncoding:
    def test_oversized_udp_answer_sets_tc_and_respects_classic_udp_limit(
        self, dns_client_address
    ):
        zone_origins = ZoneOrigins("example.com", [])
        ip_addresses = [f"192.0.2.{octet}" for octet in range(1, 101)]
        a_record = AHealthyRecord(
            subdomain=dns.name.from_text("many", origin=zone_origins.primary),
            healthy_ips=[
                AHealthyIp(ip=ip, health_port=None, is_healthy=True)
                for ip in ip_addresses
            ],
        )
        config = DnsServerConfig(
            zone_origins=zone_origins,
            primary_name_server="ns1.example.net.",
            name_servers=frozenset(["ns1.example.net."]),
            a_records=frozenset([a_record]),
            ext_private_key=None,
        )
        updater = DnsServerZoneUpdater(
            min_interval=30, connection_timeout=2, config=config
        )
        updater.initialize_zone()

        server = _make_server(updater.zone, zone_origins)
        query = dns.message.make_query("many.example.com.", dns.rdatatype.A)
        mock_sock = _handle_wire(query.to_wire(), dns_client_address, server)

        sent_wire = _sent_wire(mock_sock, dns_client_address)
        response = dns.message.from_wire(sent_wire)

        assert len(sent_wire) <= _CLASSIC_UDP_PAYLOAD_SIZE
        _assert_response_header(
            response,
            query_id=query.id,
            rcode=dns.rcode.NOERROR,
            aa=True,
            tc=True,
        )


class TestMalformedWireInput:
    @patch("dns.message.from_wire")
    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_recoverable_parse_exception_returns_formerr_and_preserves_id(
        self,
        mock_update_response,
        mock_from_wire,
        dns_request,
        dns_client_address,
        zone_origins,
    ):
        zone = _make_zone(zone_origins, _FakeTransaction())
        server = _make_server(zone, zone_origins)
        mock_from_wire.side_effect = dns.exception.DNSException("Test exception")

        DnsServerUdpHandler(dns_request, dns_client_address, server)

        query_data, mock_sock = dns_request
        mock_from_wire.assert_called_once_with(query_data)

        response = _sent_response(mock_sock, dns_client_address, _real_from_wire)
        _assert_response_header(
            response,
            query_id=int.from_bytes(query_data[:2], "big"),
            rcode=dns.rcode.FORMERR,
            aa=False,
        )
        mock_update_response.assert_not_called()

    @pytest.mark.parametrize("wire_data", [b"", b"\x00\x01\x00\x00"])
    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_short_packet_drops_without_response(
        self,
        mock_update_response,
        wire_data,
        dns_client_address,
        zone_origins,
        caplog,
    ):
        zone = _make_zone(zone_origins, _FakeTransaction())
        server = _make_server(zone, zone_origins)

        with caplog.at_level(logging.DEBUG):
            mock_sock = _handle_wire(wire_data, dns_client_address, server)

        mock_sock.sendto.assert_not_called()
        mock_update_response.assert_not_called()

        _assert_log_record(
            caplog, logging.INFO, "Ignoring malformed DNS packet", _DNS_TRAFFIC_JUNK
        )
        assert f"source={_TEST_SOURCE_HOST}:{_TEST_SOURCE_PORT}" in caplog.text
        assert "packet is shorter than the 12-byte DNS header" in caplog.text
        assert "Stack trace for malformed DNS packet" in caplog.text

    @pytest.mark.parametrize(
        "wire_data,expected_problem",
        [
            (
                b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00",
                "packet does not match the DNS message wire format",
            ),
            (
                b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
                b"\xc0\x0c\x00\x01\x00\x01",
                "packet contains an invalid DNS compression pointer",
            ),
            (
                b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
                b"\x40\x00\x00\x01\x00\x01",
                "packet uses an unsupported DNS label encoding",
            ),
            (
                b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
                b"\x03www\x00\x00\x01\x00\x01junk",
                "packet has trailing bytes after a complete DNS message",
            ),
            (
                bytes(range(32)),
                "packet does not match the DNS message wire format",
            ),
        ],
    )
    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_malformed_wire_with_recoverable_header_returns_formerr(
        self,
        mock_update_response,
        wire_data,
        expected_problem,
        dns_client_address,
        zone_origins,
        caplog,
    ):
        zone = _make_zone(zone_origins, _FakeTransaction())
        server = _make_server(zone, zone_origins)

        with caplog.at_level(logging.DEBUG):
            mock_sock = _handle_wire(wire_data, dns_client_address, server)

        sent_wire = _sent_wire(mock_sock, dns_client_address)
        assert len(sent_wire) == 12
        assert sent_wire[0] == wire_data[0]
        assert sent_wire[1] == wire_data[1]
        assert sent_wire[2] & 0x80  # QR=1
        assert (sent_wire[3] & 0x0F) == dns.rcode.FORMERR

        mock_update_response.assert_not_called()

        _assert_log_record(
            caplog,
            logging.INFO,
            "Malformed DNS query; replying FORMERR",
            _DNS_TRAFFIC_JUNK,
        )
        assert f"source={_TEST_SOURCE_HOST}:{_TEST_SOURCE_PORT}" in caplog.text
        assert f"problem={expected_problem}" in caplog.text
        assert "Stack trace for malformed DNS query" in caplog.text

    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_malformed_wire_formerr_preserves_header_opcode_and_rd(
        self, mock_update_response, dns_client_address, zone_origins
    ):
        request_flags = dns.opcode.to_flags(dns.opcode.STATUS) | dns.flags.RD
        wire_data = (
            b"\x12\x34"
            + request_flags.to_bytes(2, "big")
            + b"\x00\x01\x00\x00\x00\x00\x00\x00"
        )
        zone = _make_zone(zone_origins, _FakeTransaction())
        server = _make_server(zone, zone_origins)
        mock_sock = _handle_wire(wire_data, dns_client_address, server)

        response = _sent_response(mock_sock, dns_client_address, _real_from_wire)
        _assert_response_header(
            response,
            query_id=int.from_bytes(wire_data[:2], "big"),
            rcode=dns.rcode.FORMERR,
            aa=False,
            opcode=dns.opcode.STATUS,
            rd=True,
        )
        mock_update_response.assert_not_called()


class TestInboundResponsePackets:
    @pytest.mark.parametrize(
        "wire_data",
        [
            dns.message.make_response(
                dns.message.make_query("test.example.com.", dns.rdatatype.A)
            ).to_wire(),
            b"\x12\x34\x81\x00\x00\x01\x00\x00\x00\x00\x00\x00",
        ],
        ids=["well-formed-response", "malformed-response"],
    )
    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_dns_response_packet_logs_warning_and_drops(
        self,
        mock_update_response,
        wire_data,
        dns_client_address,
        zone_origins,
        caplog,
    ):
        zone = _make_zone(zone_origins, _FakeTransaction())
        server = _make_server(zone, zone_origins)

        with caplog.at_level(logging.WARNING):
            mock_sock = _handle_wire(wire_data, dns_client_address, server)

        mock_update_response.assert_not_called()
        mock_sock.sendto.assert_not_called()

        _assert_log_record(
            caplog,
            logging.WARNING,
            "Ignoring DNS response packet received on query socket",
            _DNS_TRAFFIC_SUSPICIOUS,
        )
        assert f"source={_TEST_SOURCE_HOST}:{_TEST_SOURCE_PORT}" in caplog.text
        assert "problem=response flag is set" in caplog.text


class TestResponseConstructionFailure:
    @patch("dns.message.make_response")
    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_make_response_failure_logs_info_and_drops(
        self,
        mock_update_response,
        mock_make_response,
        dns_request,
        dns_client_address,
        zone_origins,
        caplog,
    ):
        zone = _make_zone(zone_origins, _FakeTransaction())
        server = _make_server(zone, zone_origins)
        mock_make_response.side_effect = dns.exception.FormError(
            "cannot build response"
        )

        with caplog.at_level(logging.DEBUG):
            DnsServerUdpHandler(dns_request, dns_client_address, server)

        mock_update_response.assert_not_called()
        dns_request[1].sendto.assert_not_called()

        _assert_log_record(
            caplog,
            logging.INFO,
            "Unable to build DNS response; dropping packet",
            _DNS_TRAFFIC_JUNK,
        )
        assert f"source={_TEST_SOURCE_HOST}:{_TEST_SOURCE_PORT}" in caplog.text
        assert "problem=cannot build response" in caplog.text
        assert "Stack trace for DNS response construction failure" in caplog.text


class TestRejectedQueries:
    @pytest.mark.parametrize(
        "query_factory",
        [
            lambda: _make_query_with_opcode(dns.opcode.IQUERY),
            lambda: _make_query_with_opcode(dns.opcode.STATUS),
            lambda: _make_query_with_opcode(dns.opcode.NOTIFY),
            lambda: _make_query_with_opcode(15),
            _make_update_query,
        ],
        ids=["iquery", "status", "notify", "unassigned-opcode", "update"],
    )
    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_query_with_unsupported_opcode_returns_notimp(
        self,
        mock_update_response,
        query_factory,
        dns_client_address,
        zone_origins,
        caplog,
    ):
        zone = _make_zone(zone_origins, _FakeTransaction())
        server = _make_server(zone, zone_origins)
        query = query_factory()

        with caplog.at_level(logging.WARNING):
            mock_sock = _handle_wire(query.to_wire(), dns_client_address, server)

        response = _sent_response(mock_sock, dns_client_address)
        _assert_response_header(
            response,
            query_id=query.id,
            rcode=dns.rcode.NOTIMP,
            aa=False,
            opcode=query.opcode(),
        )
        _assert_section_counts(response)
        mock_update_response.assert_not_called()

        _assert_log_record(
            caplog,
            logging.WARNING,
            "DNS query uses unsupported opcode",
            _DNS_TRAFFIC_SUSPICIOUS,
        )
        _assert_log_context(caplog, query_id=query.id)
        assert f"opcode={dns.opcode.to_text(query.opcode())}" in caplog.text

    @pytest.mark.parametrize(
        "query_data",
        [
            dns.message.Message().to_wire(),
            _make_multi_question_wire("example.com.", "test.com."),
        ],
        ids=["zero-question", "multi-question"],
    )
    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_query_with_invalid_question_count_returns_formerr(
        self,
        mock_update_response,
        query_data,
        dns_client_address,
        zone_origins,
        caplog,
    ):
        zone = _make_zone(zone_origins, _FakeTransaction())
        server = _make_server(zone, zone_origins)

        with caplog.at_level(logging.INFO):
            mock_sock = _handle_wire(query_data, dns_client_address, server)

        response = _sent_response(mock_sock, dns_client_address)
        _assert_response_header(
            response,
            query_id=dns.message.from_wire(query_data).id,
            rcode=dns.rcode.FORMERR,
            aa=False,
        )
        _assert_section_counts(response)
        mock_update_response.assert_not_called()

        _assert_log_record(
            caplog,
            logging.INFO,
            "DNS query has invalid question count",
            _DNS_TRAFFIC_JUNK,
        )
        _assert_log_context(caplog, query_id=response.id)

    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_query_with_non_in_class_returns_refused(
        self, mock_update_response, dns_client_address, zone_origins, caplog
    ):
        zone = _make_zone(zone_origins, _FakeTransaction())
        server = _make_server(zone, zone_origins)
        query = dns.message.make_query(
            "test.example.com.", dns.rdatatype.A, rdclass=dns.rdataclass.CH
        )

        with caplog.at_level(logging.INFO):
            mock_sock = _handle_wire(query.to_wire(), dns_client_address, server)

        response = _sent_response(mock_sock, dns_client_address)
        _assert_response_header(
            response,
            query_id=query.id,
            rcode=dns.rcode.REFUSED,
            aa=False,
        )
        _assert_section_counts(response)
        mock_update_response.assert_not_called()

        _assert_log_record(
            caplog,
            logging.INFO,
            "Refused DNS query with unsupported class",
            _DNS_TRAFFIC_NOISE,
        )
        _assert_log_context(caplog, query_id=query.id)
