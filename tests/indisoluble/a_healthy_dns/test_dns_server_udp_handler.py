#!/usr/bin/env python3

import dns.exception
import dns.flags
import dns.message
import dns.name
import dns.opcode
import dns.rcode
import dns.rdataclass
import dns.rdatatype
import dns.zone

import pytest

from unittest.mock import MagicMock, patch

from indisoluble.a_healthy_dns.dns_server_udp_handler import (
    _update_response,
    DnsServerUdpHandler,
)
from indisoluble.a_healthy_dns.records.zone_origins import ZoneOrigins

# Captured before any test patches dns.message.from_wire so we can still parse
# response wire bytes inside tests that mock from_wire.
_real_from_wire = dns.message.from_wire


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
    _update_response(
        mock_dns_response, query_name, query_type, mock_zone, mock_zone_origins
    )

    # Assertions
    mock_zone.reader.assert_called_once()
    mock_reader.get_node.assert_called_once_with(query_name)
    mock_node.get_rdataset.assert_called_once_with(mock_zone.rdclass, query_type)
    mock_reader.get.assert_not_called()  # SOA lookup should not be needed when node is found

    assert mock_dns_response.rcode() == dns.rcode.NOERROR

    assert len(mock_dns_response.additional) == 0
    assert len(mock_dns_response.authority) == 0

    assert len(mock_dns_response.answer) == 1
    assert mock_dns_response.answer[0].name == query_name
    assert mock_dns_response.answer[0].rdclass == mock_rdataset.rdclass
    assert mock_dns_response.answer[0].rdtype == query_type
    assert mock_dns_response.answer[0].ttl == mock_rdataset.ttl
    assert list(mock_dns_response.answer[0]) == [mock_rdata]


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
        mock_dns_response, query_name, query_type, mock_zone, mock_zone_origins
    )

    # Assertions
    mock_zone.reader.assert_called_once()
    mock_reader.get_node.assert_called_once_with(
        query_name.relativize(mock_zone_origins.primary)
    )
    mock_node.get_rdataset.assert_called_once_with(mock_zone.rdclass, query_type)
    mock_reader.get.assert_not_called()  # SOA lookup should not be needed when node is found

    assert mock_dns_response.rcode() == dns.rcode.NOERROR

    assert len(mock_dns_response.additional) == 0
    assert len(mock_dns_response.authority) == 0

    assert len(mock_dns_response.answer) == 1
    assert mock_dns_response.answer[0].name == query_name
    assert mock_dns_response.answer[0].rdclass == mock_rdataset.rdclass
    assert mock_dns_response.answer[0].rdtype == query_type
    assert mock_dns_response.answer[0].ttl == mock_rdataset.ttl
    assert list(mock_dns_response.answer[0]) == [mock_rdata]


def test_update_response_with_absolute_name_outside_zone_origins(
    mock_zone, mock_dns_response, mock_zone_origins
):
    # Setup
    query_name = dns.name.from_text("test", origin=dns.name.from_text("other.com"))
    query_type = dns.rdatatype.A

    # Call function
    _update_response(
        mock_dns_response, query_name, query_type, mock_zone, mock_zone_origins
    )

    # Assertions
    mock_zone.reader.assert_not_called()

    assert mock_dns_response.rcode() == dns.rcode.REFUSED

    assert len(mock_dns_response.additional) == 0
    assert len(mock_dns_response.authority) == 0

    assert len(mock_dns_response.answer) == 0


def test_update_response_domain_not_found(
    mock_zone, mock_reader, mock_dns_response, mock_zone_origins, mock_soa_rdataset
):
    # Setup
    query_name = dns.name.from_text("nonexistent", origin=mock_zone_origins.primary)
    query_type = dns.rdatatype.A

    # Mock zone.reader.get_node to return None
    mock_reader.get_node.return_value = None
    mock_reader.get.return_value = mock_soa_rdataset

    mock_zone.reader.return_value.__enter__.return_value = mock_reader

    # Call function
    _update_response(
        mock_dns_response, query_name, query_type, mock_zone, mock_zone_origins
    )

    # Assertions
    mock_zone.reader.assert_called_once()
    mock_reader.get_node.assert_called_once_with(
        query_name.relativize(mock_zone_origins.primary)
    )
    mock_reader.get.assert_called_once_with(dns.name.empty, dns.rdatatype.SOA)

    assert mock_dns_response.rcode() == dns.rcode.NXDOMAIN

    assert len(mock_dns_response.additional) == 0
    assert len(mock_dns_response.authority) == 1
    assert mock_dns_response.authority[0].rdtype == dns.rdatatype.SOA
    assert mock_dns_response.authority[0].name == mock_zone_origins.primary
    assert mock_dns_response.authority[0].ttl == mock_soa_rdataset.ttl

    assert len(mock_dns_response.answer) == 0


def test_update_response_record_type_not_found(
    mock_zone, mock_reader, mock_dns_response, mock_zone_origins, mock_soa_rdataset
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
    _update_response(
        mock_dns_response, query_name, query_type, mock_zone, mock_zone_origins
    )

    # Assertions
    mock_zone.reader.assert_called_once()
    mock_reader.get_node.assert_called_once_with(
        query_name.relativize(mock_zone_origins.primary)
    )
    mock_node.get_rdataset.assert_called_once_with(mock_zone.rdclass, query_type)
    mock_reader.get.assert_called_once_with(dns.name.empty, dns.rdatatype.SOA)

    assert mock_dns_response.rcode() == dns.rcode.NOERROR

    assert len(mock_dns_response.additional) == 0
    assert len(mock_dns_response.authority) == 1
    assert mock_dns_response.authority[0].rdtype == dns.rdatatype.SOA
    assert mock_dns_response.authority[0].name == mock_zone_origins.primary
    assert mock_dns_response.authority[0].ttl == mock_soa_rdataset.ttl

    assert len(mock_dns_response.answer) == 0


@patch("indisoluble.a_healthy_dns.dns_server_udp_handler._update_response")
def test_handle_valid_query(
    mock_update_response, mock_dns_request, mock_dns_client_address, mock_server
):
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

    assert mock_update_response.call_not_called()


@pytest.mark.parametrize("wire_data", [b"", b"\x00\x01\x00\x00"])
@patch("indisoluble.a_healthy_dns.dns_server_udp_handler._update_response")
def test_handle_malformed_wire_input_drops_silently(
    mock_update_response, wire_data, mock_dns_client_address, mock_server
):
    mock_sock = MagicMock()
    request = (wire_data, mock_sock)

    _ = DnsServerUdpHandler(request, mock_dns_client_address, mock_server)

    # Payload too short to recover a DNS header: drop silently, no response.
    mock_sock.sendto.assert_not_called()
    assert mock_update_response.call_not_called()


# Wire bytes that fail dns.message.from_wire() but are ≥ 12 bytes so the DNS
# header (and transaction ID) can still be recovered.  The handler must respond
# with FORMERR, preserving the original transaction ID (RFC 1035 §4.1.1).
@pytest.mark.parametrize(
    "wire_data",
    [
        # Valid 12-byte header claiming QDCOUNT=1 but question section missing
        b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00",
        # Self-referential compression pointer (offset 12 points to itself)
        b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\xc0\x0c\x00\x01\x00\x01",
        # Garbage bytes that do not form a valid DNS message
        bytes(range(32)),
    ],
)
@patch("indisoluble.a_healthy_dns.dns_server_udp_handler._update_response")
def test_handle_malformed_wire_with_recoverable_header_returns_formerr(
    mock_update_response, wire_data, mock_dns_client_address, mock_server
):
    mock_sock = MagicMock()
    request = (wire_data, mock_sock)

    _ = DnsServerUdpHandler(request, mock_dns_client_address, mock_server)

    mock_sock.sendto.assert_called_once()
    sent_wire = mock_sock.sendto.call_args[0][0]

    # Minimal 12-byte FORMERR response: transaction ID preserved, QR=1.
    assert len(sent_wire) == 12
    assert sent_wire[0] == wire_data[0]
    assert sent_wire[1] == wire_data[1]
    assert sent_wire[2] & 0x80  # QR=1
    assert (sent_wire[3] & 0x0F) == dns.rcode.FORMERR

    assert mock_update_response.call_not_called()


@pytest.mark.parametrize(
    "opcode",
    [
        dns.opcode.STATUS,
        dns.opcode.NOTIFY,
        # dns.opcode.UPDATE is excluded: dnspython rejects the wire format as
        # malformed when opcode=UPDATE appears in a standard-query-shaped message,
        # so the handler never reaches the opcode check for that case.
    ],
)
@patch("indisoluble.a_healthy_dns.dns_server_udp_handler._update_response")
def test_handle_query_with_unsupported_opcode_returns_notimp(
    mock_update_response, opcode, mock_dns_client_address, mock_server
):
    query = dns.message.make_query("test.example.com.", dns.rdatatype.A)
    query.set_opcode(opcode)
    mock_sock = MagicMock()
    request = (query.to_wire(), mock_sock)

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
    assert bool(response.flags & dns.flags.AA)
    assert bool(response.flags & dns.flags.QR)
    assert not bool(response.flags & dns.flags.RA)
    assert not bool(response.flags & dns.flags.TC)


@pytest.mark.parametrize(
    "query_data",
    [
        dns.message.Message().to_wire(),
        _make_multi_question_wire("example.com.", "test.com."),
    ],
)
@patch("indisoluble.a_healthy_dns.dns_server_udp_handler._update_response")
def test_handle_query_with_invalid_question_count_returns_formerr(
    mock_update_response, query_data, mock_dns_client_address, mock_server
):
    mock_sock = MagicMock()
    request = (query_data, mock_sock)

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
    assert bool(response.flags & dns.flags.AA)
    assert bool(response.flags & dns.flags.QR)
    assert not bool(response.flags & dns.flags.RA)
    assert not bool(response.flags & dns.flags.TC)


@patch("indisoluble.a_healthy_dns.dns_server_udp_handler._update_response")
def test_handle_query_with_non_in_class_returns_refused(
    mock_update_response, mock_dns_client_address, mock_server
):
    query = dns.message.make_query(
        "test.example.com.", dns.rdatatype.A, rdclass=dns.rdataclass.CH
    )
    mock_sock = MagicMock()
    request = (query.to_wire(), mock_sock)

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
    assert bool(response.flags & dns.flags.AA)
    assert bool(response.flags & dns.flags.QR)
    assert not bool(response.flags & dns.flags.RA)
    assert not bool(response.flags & dns.flags.TC)
