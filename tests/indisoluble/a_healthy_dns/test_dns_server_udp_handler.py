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
import dns.update
import dns.zone

import pytest

from unittest.mock import MagicMock, patch

from indisoluble.a_healthy_dns.dns_server_udp_handler import (
    _CLASSIC_UDP_PAYLOAD_SIZE,
    _DNS_TRAFFIC_JUNK,
    _DNS_TRAFFIC_NOISE,
    _DNS_TRAFFIC_NORMAL,
    _DNS_TRAFFIC_SUSPICIOUS,
    _update_response,
    DnsServerUdpHandler,
)
from indisoluble.a_healthy_dns.dns_server_config_factory import DnsServerConfig
from indisoluble.a_healthy_dns.dns_server_zone_updater import DnsServerZoneUpdater
from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp
from indisoluble.a_healthy_dns.records.a_healthy_record import AHealthyRecord
from indisoluble.a_healthy_dns.records.time import RFC8767_MAX_TTL
from indisoluble.a_healthy_dns.records.zone_origins import ZoneOrigins

# Captured before any test patches dns.message.from_wire so we can still parse
# response wire bytes inside tests that mock from_wire.
_real_from_wire = dns.message.from_wire

_TEST_QUERY_ID = 13551
_TEST_SOURCE_HOST = "127.0.0.1"
_TEST_SOURCE_PORT = 12345


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


def _assert_log_record(caplog, level, message_fragment, traffic_marker=None):
    assert any(
        record.levelno == level
        and message_fragment in record.getMessage()
        and (traffic_marker is None or traffic_marker in record.getMessage())
        for record in caplog.records
    )


@pytest.fixture
def mock_reader():
    reader = MagicMock(spec=dns.zone.Transaction)
    return reader


@pytest.fixture
def mock_zone_origins():
    return ZoneOrigins("example.com", [])


@pytest.fixture
def mock_zone(mock_reader, mock_zone_origins):
    zone = MagicMock()
    zone.origin = mock_zone_origins.primary
    zone.rdclass = dns.rdataclass.IN
    zone.reader.return_value = mock_reader
    return zone


@pytest.fixture
def mock_rdata():
    mock_rdata = MagicMock()
    mock_rdata.rdclass = dns.rdataclass.IN
    mock_rdata.rdtype = dns.rdatatype.A
    return mock_rdata


@pytest.fixture
def mock_rdataset():
    mock_rdataset = MagicMock()
    mock_rdataset.rdclass = dns.rdataclass.IN
    mock_rdataset.rdtype = dns.rdatatype.A
    mock_rdataset.ttl = 300
    return mock_rdataset


@pytest.fixture
def mock_soa_rdata():
    mock_soa_rdata = MagicMock()
    mock_soa_rdata.rdclass = dns.rdataclass.IN
    mock_soa_rdata.rdtype = dns.rdatatype.SOA
    mock_soa_rdata.minimum = 60
    return mock_soa_rdata


@pytest.fixture
def mock_soa_rdataset(mock_soa_rdata):
    mock_soa_rdataset = MagicMock()
    mock_soa_rdataset.rdclass = dns.rdataclass.IN
    mock_soa_rdataset.rdtype = dns.rdatatype.SOA
    mock_soa_rdataset.ttl = 300
    mock_soa_rdataset.__iter__ = MagicMock(return_value=iter([mock_soa_rdata]))
    return mock_soa_rdataset


@pytest.fixture
def mock_server(mock_zone, mock_zone_origins):
    server = MagicMock()
    server.zone = mock_zone
    server.zone_origins = mock_zone_origins
    return server


@pytest.fixture
def mock_dns_response():
    return dns.message.make_response(dns.message.make_query("dummy", dns.rdatatype.A))


@pytest.fixture
def mock_dns_request():
    query = dns.message.make_query("test.example.com.", dns.rdatatype.A)
    return (query.to_wire(), MagicMock())


@pytest.fixture
def mock_dns_client_address():
    return ("127.0.0.1", 12345)


def test_update_response_with_relative_name_found(
    mock_zone,
    mock_reader,
    mock_rdata,
    mock_rdataset,
    mock_dns_response,
    mock_zone_origins,
    caplog,
):
    # Setup
    query_name = dns.name.from_text("test", origin=None)
    query_type = dns.rdatatype.A

    # Mock zone.reader.get_node for relative name
    mock_rdataset.__iter__.return_value = [mock_rdata]

    mock_node = MagicMock()
    mock_node.get_rdataset.return_value = mock_rdataset

    mock_reader.get_node.return_value = mock_node

    mock_zone.reader.return_value.__enter__.return_value = mock_reader

    # Call function
    with caplog.at_level(logging.INFO):
        _update_response(
            mock_dns_response,
            query_name,
            query_type,
            mock_zone,
            mock_zone_origins,
            _TEST_QUERY_ID,
            _TEST_SOURCE_HOST,
            _TEST_SOURCE_PORT,
        )

    # Assertions
    mock_zone.reader.assert_called_once()
    mock_reader.get_node.assert_called_once_with(query_name)
    mock_node.get_rdataset.assert_called_once_with(mock_zone.rdclass, query_type)
    mock_reader.get.assert_not_called()  # SOA lookup should not be needed when node is found

    assert mock_dns_response.rcode() == dns.rcode.NOERROR
    assert bool(mock_dns_response.flags & dns.flags.AA)

    assert len(mock_dns_response.additional) == 0
    assert len(mock_dns_response.authority) == 0

    assert len(mock_dns_response.answer) == 1
    assert mock_dns_response.answer[0].name == query_name
    assert mock_dns_response.answer[0].rdclass == mock_rdataset.rdclass
    assert mock_dns_response.answer[0].rdtype == query_type
    assert mock_dns_response.answer[0].ttl == mock_rdataset.ttl
    assert list(mock_dns_response.answer[0]) == [mock_rdata]

    _assert_log_record(
        caplog,
        logging.INFO,
        "Answered DNS query from hosted zone",
        _DNS_TRAFFIC_NORMAL,
    )
    assert f"source={_TEST_SOURCE_HOST}:{_TEST_SOURCE_PORT}" in caplog.text
    assert f"id={_TEST_QUERY_ID}" in caplog.text
    assert "qname=test" in caplog.text
    assert "qtype=A" in caplog.text


def test_update_response_caps_answer_ttl_to_rfc8767_max(
    mock_zone,
    mock_reader,
    mock_rdata,
    mock_rdataset,
    mock_dns_response,
    mock_zone_origins,
):
    query_name = dns.name.from_text("test", origin=None)
    query_type = dns.rdatatype.A

    mock_rdataset.ttl = RFC8767_MAX_TTL + 1
    mock_rdataset.__iter__.return_value = [mock_rdata]

    mock_node = MagicMock()
    mock_node.get_rdataset.return_value = mock_rdataset
    mock_reader.get_node.return_value = mock_node
    mock_zone.reader.return_value.__enter__.return_value = mock_reader

    _update_response(
        mock_dns_response,
        query_name,
        query_type,
        mock_zone,
        mock_zone_origins,
        _TEST_QUERY_ID,
        _TEST_SOURCE_HOST,
        _TEST_SOURCE_PORT,
    )

    assert len(mock_dns_response.answer) == 1
    assert mock_dns_response.answer[0].ttl == RFC8767_MAX_TTL


def test_update_response_with_absolute_name_found(
    mock_zone,
    mock_reader,
    mock_rdata,
    mock_rdataset,
    mock_dns_response,
    mock_zone_origins,
):
    # Setup
    query_name = dns.name.from_text("test", origin=mock_zone_origins.primary)
    query_type = dns.rdatatype.A

    # Mock zone.reader.get_node for relative name
    mock_rdataset.__iter__.return_value = [mock_rdata]

    mock_node = MagicMock()
    mock_node.get_rdataset.return_value = mock_rdataset

    mock_reader.get_node.return_value = mock_node

    mock_zone.reader.return_value.__enter__.return_value = mock_reader

    # Call function
    _update_response(
        mock_dns_response,
        query_name,
        query_type,
        mock_zone,
        mock_zone_origins,
        _TEST_QUERY_ID,
        _TEST_SOURCE_HOST,
        _TEST_SOURCE_PORT,
    )

    # Assertions
    mock_zone.reader.assert_called_once()
    mock_reader.get_node.assert_called_once_with(
        query_name.relativize(mock_zone_origins.primary)
    )
    mock_node.get_rdataset.assert_called_once_with(mock_zone.rdclass, query_type)
    mock_reader.get.assert_not_called()  # SOA lookup should not be needed when node is found

    assert mock_dns_response.rcode() == dns.rcode.NOERROR
    assert bool(mock_dns_response.flags & dns.flags.AA)

    assert len(mock_dns_response.additional) == 0
    assert len(mock_dns_response.authority) == 0

    assert len(mock_dns_response.answer) == 1
    assert mock_dns_response.answer[0].name == query_name
    assert mock_dns_response.answer[0].rdclass == mock_rdataset.rdclass
    assert mock_dns_response.answer[0].rdtype == query_type
    assert mock_dns_response.answer[0].ttl == mock_rdataset.ttl
    assert list(mock_dns_response.answer[0]) == [mock_rdata]


def test_update_response_with_absolute_name_outside_zone_origins(
    mock_zone, mock_dns_response, mock_zone_origins, caplog
):
    # Setup
    query_name = dns.name.from_text("test", origin=dns.name.from_text("other.com"))
    query_type = dns.rdatatype.A

    # Call function
    with caplog.at_level(logging.INFO):
        _update_response(
            mock_dns_response,
            query_name,
            query_type,
            mock_zone,
            mock_zone_origins,
            _TEST_QUERY_ID,
            _TEST_SOURCE_HOST,
            _TEST_SOURCE_PORT,
        )

    # Assertions
    mock_zone.reader.assert_not_called()

    assert mock_dns_response.rcode() == dns.rcode.REFUSED
    assert not bool(mock_dns_response.flags & dns.flags.AA)

    assert len(mock_dns_response.additional) == 0
    assert len(mock_dns_response.authority) == 0

    assert len(mock_dns_response.answer) == 0

    _assert_log_record(
        caplog,
        logging.INFO,
        "Refused DNS query outside hosted or alias zones",
        _DNS_TRAFFIC_NOISE,
    )
    assert f"source={_TEST_SOURCE_HOST}:{_TEST_SOURCE_PORT}" in caplog.text
    assert f"id={_TEST_QUERY_ID}" in caplog.text


def test_update_response_domain_not_found(
    mock_zone,
    mock_reader,
    mock_dns_response,
    mock_zone_origins,
    mock_soa_rdata,
    mock_soa_rdataset,
    caplog,
):
    # Setup
    query_name = dns.name.from_text("nonexistent", origin=mock_zone_origins.primary)
    query_type = dns.rdatatype.A

    # Mock zone.reader.get_node to return None
    mock_reader.get_node.return_value = None
    mock_reader.get.return_value = mock_soa_rdataset

    mock_zone.reader.return_value.__enter__.return_value = mock_reader

    # Call function
    with caplog.at_level(logging.INFO):
        _update_response(
            mock_dns_response,
            query_name,
            query_type,
            mock_zone,
            mock_zone_origins,
            _TEST_QUERY_ID,
            _TEST_SOURCE_HOST,
            _TEST_SOURCE_PORT,
        )

    # Assertions
    mock_zone.reader.assert_called_once()
    mock_reader.get_node.assert_called_once_with(
        query_name.relativize(mock_zone_origins.primary)
    )
    mock_reader.get.assert_called_once_with(dns.name.empty, dns.rdatatype.SOA)

    assert mock_dns_response.rcode() == dns.rcode.NXDOMAIN
    assert bool(mock_dns_response.flags & dns.flags.AA)

    assert len(mock_dns_response.additional) == 0
    assert len(mock_dns_response.authority) == 1
    assert mock_dns_response.authority[0].rdtype == dns.rdatatype.SOA
    assert mock_dns_response.authority[0].name == mock_zone_origins.primary
    assert mock_dns_response.authority[0].ttl == mock_soa_rdata.minimum

    assert len(mock_dns_response.answer) == 0

    _assert_log_record(
        caplog, logging.INFO, "returning NXDOMAIN", _DNS_TRAFFIC_NORMAL
    )
    assert f"source={_TEST_SOURCE_HOST}:{_TEST_SOURCE_PORT}" in caplog.text
    assert f"id={_TEST_QUERY_ID}" in caplog.text


@pytest.mark.parametrize(
    "soa_rdataset",
    [
        None,
        pytest.param(
            MagicMock(
                rdclass=dns.rdataclass.IN,
                rdtype=dns.rdatatype.SOA,
                ttl=300,
                **{"__iter__.return_value": iter([])},
            ),
            id="empty-soa-rdataset",
        ),
    ],
    ids=["missing-soa-rdataset", "empty-soa-rdataset"],
)
def test_update_response_domain_not_found_without_soa_authority(
    mock_zone,
    mock_reader,
    mock_dns_response,
    mock_zone_origins,
    soa_rdataset,
):
    query_name = dns.name.from_text("nonexistent", origin=mock_zone_origins.primary)
    query_type = dns.rdatatype.A

    mock_reader.get_node.return_value = None
    mock_reader.get.return_value = soa_rdataset
    mock_zone.reader.return_value.__enter__.return_value = mock_reader

    _update_response(
        mock_dns_response,
        query_name,
        query_type,
        mock_zone,
        mock_zone_origins,
        _TEST_QUERY_ID,
        _TEST_SOURCE_HOST,
        _TEST_SOURCE_PORT,
    )

    assert mock_dns_response.rcode() == dns.rcode.NXDOMAIN
    assert bool(mock_dns_response.flags & dns.flags.AA)
    assert len(mock_dns_response.authority) == 0
    assert len(mock_dns_response.answer) == 0


def test_update_response_record_type_not_found(
    mock_zone,
    mock_reader,
    mock_dns_response,
    mock_zone_origins,
    mock_soa_rdata,
    mock_soa_rdataset,
    caplog,
):
    # Setup
    query_name = dns.name.from_text("test", origin=mock_zone_origins.primary)
    query_type = dns.rdatatype.A

    # Mock zone.get_node to return a node but get_rdataset returns None
    mock_node = MagicMock()
    mock_node.get_rdataset.return_value = None

    mock_reader.get_node.return_value = mock_node
    mock_reader.get.return_value = mock_soa_rdataset

    mock_zone.reader.return_value.__enter__.return_value = mock_reader

    # Call function
    with caplog.at_level(logging.INFO):
        _update_response(
            mock_dns_response,
            query_name,
            query_type,
            mock_zone,
            mock_zone_origins,
            _TEST_QUERY_ID,
            _TEST_SOURCE_HOST,
            _TEST_SOURCE_PORT,
        )

    # Assertions
    mock_zone.reader.assert_called_once()
    mock_reader.get_node.assert_called_once_with(
        query_name.relativize(mock_zone_origins.primary)
    )
    mock_node.get_rdataset.assert_called_once_with(mock_zone.rdclass, query_type)
    mock_reader.get.assert_called_once_with(dns.name.empty, dns.rdatatype.SOA)

    assert mock_dns_response.rcode() == dns.rcode.NOERROR
    assert bool(mock_dns_response.flags & dns.flags.AA)

    assert len(mock_dns_response.additional) == 0
    assert len(mock_dns_response.authority) == 1
    assert mock_dns_response.authority[0].rdtype == dns.rdatatype.SOA
    assert mock_dns_response.authority[0].name == mock_zone_origins.primary
    assert mock_dns_response.authority[0].ttl == mock_soa_rdata.minimum

    assert len(mock_dns_response.answer) == 0

    _assert_log_record(
        caplog, logging.INFO, "returning NODATA", _DNS_TRAFFIC_NORMAL
    )
    assert f"source={_TEST_SOURCE_HOST}:{_TEST_SOURCE_PORT}" in caplog.text
    assert f"id={_TEST_QUERY_ID}" in caplog.text


def test_update_response_caps_negative_response_soa_ttl_to_rfc8767_max(
    mock_zone,
    mock_reader,
    mock_dns_response,
    mock_zone_origins,
    mock_soa_rdata,
    mock_soa_rdataset,
):
    query_name = dns.name.from_text("nonexistent", origin=mock_zone_origins.primary)
    query_type = dns.rdatatype.A

    mock_reader.get_node.return_value = None
    mock_zone.reader.return_value.__enter__.return_value = mock_reader

    mock_soa_rdataset.ttl = RFC8767_MAX_TTL + 10
    mock_soa_rdata.minimum = RFC8767_MAX_TTL + 5
    mock_reader.get.return_value = mock_soa_rdataset

    _update_response(
        mock_dns_response,
        query_name,
        query_type,
        mock_zone,
        mock_zone_origins,
        _TEST_QUERY_ID,
        _TEST_SOURCE_HOST,
        _TEST_SOURCE_PORT,
    )

    assert mock_dns_response.rcode() == dns.rcode.NXDOMAIN
    assert len(mock_dns_response.authority) == 1
    assert mock_dns_response.authority[0].ttl == RFC8767_MAX_TTL


@patch("indisoluble.a_healthy_dns.dns_server_udp_handler._update_response")
def test_handle_valid_query(
    mock_update_response, mock_dns_request, mock_dns_client_address, mock_server
):
    mock_update_response.side_effect = lambda response, *args: setattr(
        response, "flags", response.flags | dns.flags.AA
    )

    # No need to call handle() as it's called automatically by the constructor
    _ = DnsServerUdpHandler(mock_dns_request, mock_dns_client_address, mock_server)

    # Get the original query for comparison
    query_data = mock_dns_request[0]
    query = dns.message.from_wire(query_data)
    question = query.question[0]

    # Assertions
    mock_update_response.assert_called_once()
    assert mock_update_response.call_args[0][1] == question.name
    assert mock_update_response.call_args[0][2] == question.rdtype
    assert mock_update_response.call_args[0][3] == mock_server.zone
    assert mock_update_response.call_args[0][4] == mock_server.zone_origins
    assert mock_update_response.call_args[0][5] == query.id
    assert mock_update_response.call_args[0][6] == mock_dns_client_address[0]
    assert mock_update_response.call_args[0][7] == mock_dns_client_address[1]

    # Check response was sent
    mock_sock = mock_dns_request[1]
    mock_sock.sendto.assert_called_once()

    # Verify response header fields (RFC 1035 §4.1.1)
    sent_data = mock_sock.sendto.call_args[0][0]
    response = dns.message.from_wire(sent_data)
    assert response.id == query.id
    assert bool(response.flags & dns.flags.AA)
    assert bool(response.flags & dns.flags.QR)
    assert not bool(response.flags & dns.flags.RA)
    assert not bool(response.flags & dns.flags.TC)


def test_handle_oversized_udp_answer_sets_tc_and_respects_classic_udp_limit(
    mock_dns_client_address,
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
    updater = DnsServerZoneUpdater(min_interval=30, connection_timeout=2, config=config)
    updater.initialize_zone()

    server = MagicMock()
    server.zone = updater.zone
    server.zone_origins = zone_origins
    query = dns.message.make_query("many.example.com.", dns.rdatatype.A)
    mock_sock = MagicMock()
    request = (query.to_wire(), mock_sock)

    _ = DnsServerUdpHandler(request, mock_dns_client_address, server)

    mock_sock.sendto.assert_called_once()
    sent_wire = mock_sock.sendto.call_args[0][0]
    response = dns.message.from_wire(sent_wire)

    assert len(sent_wire) <= _CLASSIC_UDP_PAYLOAD_SIZE
    assert response.id == query.id
    assert response.rcode() == dns.rcode.NOERROR
    assert bool(response.flags & dns.flags.QR)
    assert bool(response.flags & dns.flags.AA)
    assert bool(response.flags & dns.flags.TC)
    assert not bool(response.flags & dns.flags.RA)


@patch("dns.message.from_wire")
@patch("indisoluble.a_healthy_dns.dns_server_udp_handler._update_response")
def test_handle_exception_parsing_query(
    mock_update_response,
    mock_from_wire,
    mock_dns_request,
    mock_dns_client_address,
    mock_server,
):
    # Simulate a malformed message that passes the 12-byte ShortHeader check
    # but fails full parsing (DNSException).
    mock_from_wire.side_effect = dns.exception.DNSException("Test exception")

    _ = DnsServerUdpHandler(mock_dns_request, mock_dns_client_address, mock_server)

    query_data = mock_dns_request[0]
    mock_from_wire.assert_called_once_with(query_data)

    # The handler must respond with FORMERR (RFC 1035 §4.1.1),
    # preserving the original transaction ID.
    mock_sock = mock_dns_request[1]
    mock_sock.sendto.assert_called_once()

    sent_wire = mock_sock.sendto.call_args[0][0]
    response = _real_from_wire(sent_wire)
    assert response.id == int.from_bytes(query_data[:2], "big")
    assert response.rcode() == dns.rcode.FORMERR
    assert not bool(response.flags & dns.flags.AA)
    assert bool(response.flags & dns.flags.QR)
    assert not bool(response.flags & dns.flags.RA)
    assert not bool(response.flags & dns.flags.TC)

    mock_update_response.assert_not_called()


@pytest.mark.parametrize("wire_data", [b"", b"\x00\x01\x00\x00"])
@patch("indisoluble.a_healthy_dns.dns_server_udp_handler._update_response")
def test_handle_malformed_wire_input_drops_without_response(
    mock_update_response, wire_data, mock_dns_client_address, mock_server, caplog
):
    mock_sock = MagicMock()
    request = (wire_data, mock_sock)

    with caplog.at_level(logging.DEBUG):
        _ = DnsServerUdpHandler(request, mock_dns_client_address, mock_server)

    # Payload too short to recover a DNS header: drop without a DNS response.
    mock_sock.sendto.assert_not_called()
    mock_update_response.assert_not_called()

    _assert_log_record(
        caplog, logging.INFO, "Ignoring malformed DNS packet", _DNS_TRAFFIC_JUNK
    )
    assert f"source={_TEST_SOURCE_HOST}:{_TEST_SOURCE_PORT}" in caplog.text
    assert "packet is shorter than the 12-byte DNS header" in caplog.text
    assert "Stack trace for malformed DNS packet" in caplog.text


# Wire bytes that fail dns.message.from_wire() but are ≥ 12 bytes so the DNS
# header (and transaction ID) can still be recovered.  The handler must respond
# with FORMERR, preserving the original transaction ID (RFC 1035 §4.1.1).
@pytest.mark.parametrize(
    "wire_data,expected_problem",
    [
        (
            # Valid 12-byte header claiming QDCOUNT=1 but question section missing
            b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00",
            "packet does not match the DNS message wire format",
        ),
        (
            # Self-referential compression pointer (offset 12 points to itself)
            b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
            b"\xc0\x0c\x00\x01\x00\x01",
            "packet contains an invalid DNS compression pointer",
        ),
        (
            # Label length byte with unsupported label-type bits set.
            b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
            b"\x40\x00\x00\x01\x00\x01",
            "packet uses an unsupported DNS label encoding",
        ),
        (
            # Valid query followed by extra bytes after the DNS message ends.
            b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
            b"\x03www\x00\x00\x01\x00\x01junk",
            "packet has trailing bytes after a complete DNS message",
        ),
        (
            # Garbage bytes that do not form a valid DNS message
            bytes(range(32)),
            "packet does not match the DNS message wire format",
        ),
    ],
)
@patch("indisoluble.a_healthy_dns.dns_server_udp_handler._update_response")
def test_handle_malformed_wire_with_recoverable_header_returns_formerr(
    mock_update_response,
    wire_data,
    expected_problem,
    mock_dns_client_address,
    mock_server,
    caplog,
):
    mock_sock = MagicMock()
    request = (wire_data, mock_sock)

    with caplog.at_level(logging.DEBUG):
        _ = DnsServerUdpHandler(request, mock_dns_client_address, mock_server)

    mock_sock.sendto.assert_called_once()
    sent_wire = mock_sock.sendto.call_args[0][0]

    # Minimal 12-byte FORMERR response: transaction ID preserved, QR=1.
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


@patch("indisoluble.a_healthy_dns.dns_server_udp_handler._update_response")
def test_handle_malformed_wire_formerr_preserves_header_opcode_and_rd(
    mock_update_response, mock_dns_client_address, mock_server
):
    request_flags = dns.opcode.to_flags(dns.opcode.STATUS) | dns.flags.RD
    wire_data = (
        b"\x12\x34"
        + request_flags.to_bytes(2, "big")
        + b"\x00\x01\x00\x00\x00\x00\x00\x00"
    )
    mock_sock = MagicMock()
    request = (wire_data, mock_sock)

    _ = DnsServerUdpHandler(request, mock_dns_client_address, mock_server)

    mock_sock.sendto.assert_called_once()
    sent_wire = mock_sock.sendto.call_args[0][0]
    response = _real_from_wire(sent_wire)

    assert response.id == int.from_bytes(wire_data[:2], "big")
    assert response.opcode() == dns.opcode.STATUS
    assert bool(response.flags & dns.flags.RD)
    assert response.rcode() == dns.rcode.FORMERR
    assert not bool(response.flags & dns.flags.AA)
    assert bool(response.flags & dns.flags.QR)

    mock_update_response.assert_not_called()


@patch("indisoluble.a_healthy_dns.dns_server_udp_handler._update_response")
def test_handle_dns_response_packet_logs_warning_and_drops(
    mock_update_response, mock_dns_client_address, mock_server, caplog
):
    query = dns.message.make_query("test.example.com.", dns.rdatatype.A)
    response_packet = dns.message.make_response(query)
    mock_sock = MagicMock()
    request = (response_packet.to_wire(), mock_sock)

    with caplog.at_level(logging.DEBUG):
        _ = DnsServerUdpHandler(request, mock_dns_client_address, mock_server)

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


@patch("dns.message.make_response")
@patch("indisoluble.a_healthy_dns.dns_server_udp_handler._update_response")
def test_handle_make_response_failure_logs_info_and_drops(
    mock_update_response,
    mock_make_response,
    mock_dns_request,
    mock_dns_client_address,
    mock_server,
    caplog,
):
    mock_make_response.side_effect = dns.exception.FormError("cannot build response")

    with caplog.at_level(logging.DEBUG):
        _ = DnsServerUdpHandler(mock_dns_request, mock_dns_client_address, mock_server)

    mock_update_response.assert_not_called()
    mock_dns_request[1].sendto.assert_not_called()

    _assert_log_record(
        caplog,
        logging.INFO,
        "Unable to build DNS response; dropping packet",
        _DNS_TRAFFIC_JUNK,
    )
    assert f"source={_TEST_SOURCE_HOST}:{_TEST_SOURCE_PORT}" in caplog.text
    assert "problem=cannot build response" in caplog.text
    assert "Stack trace for DNS response construction failure" in caplog.text


@patch("indisoluble.a_healthy_dns.dns_server_udp_handler._update_response")
def test_handle_malformed_dns_response_packet_logs_warning_and_drops(
    mock_update_response, mock_dns_client_address, mock_server, caplog
):
    response_wire = bytearray(
        b"\x12\x34\x81\x00\x00\x01\x00\x00\x00\x00\x00\x00"
    )
    mock_sock = MagicMock()
    request = (bytes(response_wire), mock_sock)

    with caplog.at_level(logging.WARNING):
        _ = DnsServerUdpHandler(request, mock_dns_client_address, mock_server)

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


@pytest.mark.parametrize(
    "opcode",
    [
        dns.opcode.IQUERY,
        dns.opcode.STATUS,
        dns.opcode.NOTIFY,
    ],
)
@patch("indisoluble.a_healthy_dns.dns_server_udp_handler._update_response")
def test_handle_query_with_unsupported_opcode_returns_notimp(
    mock_update_response, opcode, mock_dns_client_address, mock_server, caplog
):
    query = dns.message.make_query("test.example.com.", dns.rdatatype.A)
    query.set_opcode(opcode)
    mock_sock = MagicMock()
    request = (query.to_wire(), mock_sock)

    with caplog.at_level(logging.WARNING):
        _ = DnsServerUdpHandler(request, mock_dns_client_address, mock_server)

    mock_update_response.assert_not_called()
    mock_sock.sendto.assert_called_once()

    sent_data = mock_sock.sendto.call_args[0][0]
    response = dns.message.from_wire(sent_data)
    assert response.rcode() == dns.rcode.NOTIMP
    assert len(response.answer) == 0
    assert len(response.authority) == 0
    assert len(response.additional) == 0

    # Header field assertions (RFC 1035 §4.1.1)
    assert response.id == query.id
    assert not bool(response.flags & dns.flags.AA)
    assert bool(response.flags & dns.flags.QR)
    assert not bool(response.flags & dns.flags.RA)
    assert not bool(response.flags & dns.flags.TC)

    _assert_log_record(
        caplog,
        logging.WARNING,
        "DNS query uses unsupported opcode",
        _DNS_TRAFFIC_SUSPICIOUS,
    )
    assert f"source={_TEST_SOURCE_HOST}:{_TEST_SOURCE_PORT}" in caplog.text
    assert f"id={query.id}" in caplog.text


@patch("indisoluble.a_healthy_dns.dns_server_udp_handler._update_response")
def test_handle_update_opcode_returns_notimp(
    mock_update_response, mock_dns_client_address, mock_server, caplog
):
    query = dns.update.Update("example.com.")
    query.add("www", 300, "A", "192.0.2.1")
    mock_sock = MagicMock()
    request = (query.to_wire(), mock_sock)

    with caplog.at_level(logging.WARNING):
        _ = DnsServerUdpHandler(request, mock_dns_client_address, mock_server)

    mock_update_response.assert_not_called()
    mock_sock.sendto.assert_called_once()

    sent_data = mock_sock.sendto.call_args[0][0]
    response = dns.message.from_wire(sent_data)
    assert response.rcode() == dns.rcode.NOTIMP
    assert response.opcode() == dns.opcode.UPDATE
    assert len(response.answer) == 0
    assert len(response.authority) == 0
    assert len(response.additional) == 0

    # Header field assertions (RFC 1035 §4.1.1)
    assert response.id == query.id
    assert not bool(response.flags & dns.flags.AA)
    assert bool(response.flags & dns.flags.QR)
    assert not bool(response.flags & dns.flags.RA)
    assert not bool(response.flags & dns.flags.TC)

    _assert_log_record(
        caplog,
        logging.WARNING,
        "DNS query uses unsupported opcode",
        _DNS_TRAFFIC_SUSPICIOUS,
    )
    assert "opcode=UPDATE" in caplog.text
    assert f"source={_TEST_SOURCE_HOST}:{_TEST_SOURCE_PORT}" in caplog.text
    assert f"id={query.id}" in caplog.text


@pytest.mark.parametrize(
    "query_data",
    [
        dns.message.Message().to_wire(),
        _make_multi_question_wire("example.com.", "test.com."),
    ],
)
@patch("indisoluble.a_healthy_dns.dns_server_udp_handler._update_response")
def test_handle_query_with_invalid_question_count_returns_formerr(
    mock_update_response, query_data, mock_dns_client_address, mock_server, caplog
):
    mock_sock = MagicMock()
    request = (query_data, mock_sock)

    with caplog.at_level(logging.INFO):
        _ = DnsServerUdpHandler(request, mock_dns_client_address, mock_server)

    mock_update_response.assert_not_called()
    mock_sock.sendto.assert_called_once()

    sent_data = mock_sock.sendto.call_args[0][0]
    response = dns.message.from_wire(sent_data)
    assert response.rcode() == dns.rcode.FORMERR
    assert len(response.answer) == 0
    assert len(response.authority) == 0
    assert len(response.additional) == 0

    # Header field assertions (RFC 1035 §4.1.1)
    assert response.id == dns.message.from_wire(query_data).id
    assert not bool(response.flags & dns.flags.AA)
    assert bool(response.flags & dns.flags.QR)
    assert not bool(response.flags & dns.flags.RA)
    assert not bool(response.flags & dns.flags.TC)

    _assert_log_record(
        caplog,
        logging.INFO,
        "DNS query has invalid question count",
        _DNS_TRAFFIC_JUNK,
    )
    assert f"source={_TEST_SOURCE_HOST}:{_TEST_SOURCE_PORT}" in caplog.text
    assert f"id={response.id}" in caplog.text


@patch("indisoluble.a_healthy_dns.dns_server_udp_handler._update_response")
def test_handle_query_with_non_in_class_returns_refused(
    mock_update_response, mock_dns_client_address, mock_server, caplog
):
    query = dns.message.make_query(
        "test.example.com.", dns.rdatatype.A, rdclass=dns.rdataclass.CH
    )
    mock_sock = MagicMock()
    request = (query.to_wire(), mock_sock)

    with caplog.at_level(logging.INFO):
        _ = DnsServerUdpHandler(request, mock_dns_client_address, mock_server)

    mock_update_response.assert_not_called()
    mock_sock.sendto.assert_called_once()

    sent_data = mock_sock.sendto.call_args[0][0]
    response = dns.message.from_wire(sent_data)
    assert response.rcode() == dns.rcode.REFUSED
    assert len(response.answer) == 0
    assert len(response.authority) == 0
    assert len(response.additional) == 0

    # Header field assertions (RFC 1035 §4.1.1)
    assert response.id == query.id
    assert not bool(response.flags & dns.flags.AA)
    assert bool(response.flags & dns.flags.QR)
    assert not bool(response.flags & dns.flags.RA)
    assert not bool(response.flags & dns.flags.TC)

    _assert_log_record(
        caplog,
        logging.INFO,
        "Refused DNS query with unsupported class",
        _DNS_TRAFFIC_NOISE,
    )
    assert f"source={_TEST_SOURCE_HOST}:{_TEST_SOURCE_PORT}" in caplog.text
    assert f"id={query.id}" in caplog.text
