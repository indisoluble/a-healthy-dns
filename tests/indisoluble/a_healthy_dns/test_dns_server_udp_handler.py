#!/usr/bin/env python3

import dns.exception
import dns.flags
import dns.message
import dns.name
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


@pytest.fixture
def mock_reader():
    reader = MagicMock(spec=dns.zone.Transaction)
    return reader


@pytest.fixture
def mock_zone(mock_reader):
    zone = MagicMock()
    zone.origin = dns.name.from_text("example.com.")
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
def mock_server(mock_zone):
    server = MagicMock()
    server.zone = mock_zone
    return server


@pytest.fixture
def dns_response():
    return dns.message.make_response(dns.message.make_query("dummy", dns.rdatatype.A))


@pytest.fixture
def dns_request():
    query = dns.message.make_query("test.example.com.", dns.rdatatype.A)
    return (query.to_wire(), MagicMock())


@pytest.fixture
def dns_client_address():
    return ("127.0.0.1", 12345)


def test_update_response_with_relative_name_found(
    mock_zone, mock_reader, mock_rdata, mock_rdataset, dns_response
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
    _update_response(dns_response, query_name, query_type, mock_zone)

    # Assertions
    mock_zone.reader.assert_called_once()
    mock_reader.get_node.assert_called_once_with(query_name)
    mock_node.get_rdataset.assert_called_once_with(mock_zone.rdclass, query_type)
    assert dns_response.rcode() == dns.rcode.NOERROR
    assert len(dns_response.answer) == 1
    assert dns_response.answer[0].name == query_name
    assert dns_response.answer[0].rdclass == mock_rdataset.rdclass
    assert dns_response.answer[0].rdtype == query_type
    assert dns_response.answer[0].ttl == mock_rdataset.ttl
    assert list(dns_response.answer[0]) == [mock_rdata]


def test_update_response_with_absolute_name_found(
    mock_zone, mock_reader, mock_rdata, mock_rdataset, dns_response
):
    # Setup
    query_name = dns.name.from_text("test", mock_zone.origin)
    query_type = dns.rdatatype.A

    # Mock zone.reader.get_node for relative name
    mock_rdataset.__iter__.return_value = [mock_rdata]

    mock_node = MagicMock()
    mock_node.get_rdataset.return_value = mock_rdataset

    mock_reader.get_node.return_value = mock_node

    mock_zone.reader.return_value.__enter__.return_value = mock_reader

    # Call function
    _update_response(dns_response, query_name, query_type, mock_zone)

    # Assertions
    mock_zone.reader.assert_called_once()
    mock_reader.get_node.assert_called_once_with(
        query_name.relativize(mock_zone.origin)
    )
    mock_node.get_rdataset.assert_called_once_with(mock_zone.rdclass, query_type)
    assert dns_response.rcode() == dns.rcode.NOERROR
    assert len(dns_response.answer) == 1
    assert dns_response.answer[0].name == query_name
    assert dns_response.answer[0].rdclass == mock_rdataset.rdclass
    assert dns_response.answer[0].rdtype == query_type
    assert dns_response.answer[0].ttl == mock_rdataset.ttl
    assert list(dns_response.answer[0]) == [mock_rdata]


def test_update_response_domain_not_found(mock_zone, mock_reader, dns_response):
    # Setup
    query_name = dns.name.from_text("nonexistent", mock_zone.origin)
    query_type = dns.rdatatype.A

    # Mock zone.reader.get_node to return None
    mock_reader.get_node.return_value = None

    mock_zone.reader.return_value.__enter__.return_value = mock_reader

    # Call function
    _update_response(dns_response, query_name, query_type, mock_zone)

    # Assertions
    mock_zone.reader.assert_called_once()
    mock_reader.get_node.assert_called_once_with(
        query_name.relativize(mock_zone.origin)
    )
    assert dns_response.rcode() == dns.rcode.NXDOMAIN
    assert len(dns_response.answer) == 0


def test_update_response_record_type_not_found(mock_zone, mock_reader, dns_response):
    # Setup
    query_name = dns.name.from_text("test", mock_zone.origin)
    query_type = dns.rdatatype.A

    # Mock zone.get_node to return a node but get_rdataset returns None
    mock_node = MagicMock()
    mock_node.get_rdataset.return_value = None

    mock_reader.get_node.return_value = mock_node

    mock_zone.reader.return_value.__enter__.return_value = mock_reader

    # Call function
    _update_response(dns_response, query_name, query_type, mock_zone)

    # Assertions
    mock_zone.reader.assert_called_once()
    mock_reader.get_node.assert_called_once_with(
        query_name.relativize(mock_zone.origin)
    )
    mock_node.get_rdataset.assert_called_once_with(mock_zone.rdclass, query_type)
    assert dns_response.rcode() == dns.rcode.NXDOMAIN
    assert len(dns_response.answer) == 0


@patch("indisoluble.a_healthy_dns.dns_server_udp_handler._update_response")
def test_handle_valid_query(
    mock_update_response, dns_request, dns_client_address, mock_server
):
    # No need to call handle() as it's called automatically by the constructor
    _ = DnsServerUdpHandler(dns_request, dns_client_address, mock_server)

    # Get the original query for comparison
    query_data = dns_request[0]
    query = dns.message.from_wire(query_data)
    question = query.question[0]

    # Assertions
    mock_update_response.assert_called_once()
    assert mock_update_response.call_args[0][1] == question.name
    assert mock_update_response.call_args[0][2] == question.rdtype
    assert mock_update_response.call_args[0][3] == mock_server.zone

    # Check response was sent
    mock_sock = dns_request[1]
    mock_sock.sendto.assert_called_once()

    # Verify AA flag is set in the response
    sent_data = mock_sock.sendto.call_args[0][0]
    response = dns.message.from_wire(sent_data)
    assert response.flags & dns.flags.AA


@patch("dns.message.from_wire")
def test_handle_exception_parsing_query(
    mock_from_wire, dns_request, dns_client_address, mock_server
):
    # Setup to simulate an exception when parsing DNS query
    mock_from_wire.side_effect = dns.exception.DNSException("Test exception")

    # No need to call handle() as it's called automatically by the constructor
    with patch("logging.warning") as mock_logging:
        _ = DnsServerUdpHandler(dns_request, dns_client_address, mock_server)

        mock_logging.assert_called_once()
        assert "Failed to parse DNS query" in mock_logging.call_args[0][0]

    # Assertions
    query_data = dns_request[0]
    mock_from_wire.assert_called_once_with(query_data)

    # Check no response was sent
    mock_sock = dns_request[1]
    mock_sock.sendto.assert_not_called()


@patch("indisoluble.a_healthy_dns.dns_server_udp_handler._update_response")
def test_handle_query_without_question(
    mock_update_response, dns_client_address, mock_server
):
    # Create a request with an empty question section
    query = dns.message.Message()
    mock_sock = MagicMock()
    request = (query.to_wire(), mock_sock)

    # No need to call handle() as it's called automatically by the constructor
    with patch("logging.warning") as mock_logging:
        _ = DnsServerUdpHandler(request, dns_client_address, mock_server)

        mock_logging.assert_called_once()
        assert "Received query without question section" in mock_logging.call_args[0][0]

    # Assertions
    mock_update_response.assert_not_called()

    # Check response was sent with FORMERR
    mock_sock.sendto.assert_called_once()

    sent_data = mock_sock.sendto.call_args[0][0]
    response = dns.message.from_wire(sent_data)
    assert response.rcode() == dns.rcode.FORMERR
