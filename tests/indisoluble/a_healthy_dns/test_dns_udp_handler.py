#!/usr/bin/env python3

import pytest

import dns.message
import dns.rdatatype
import dns.rcode
import dns.exception

from unittest.mock import Mock, patch

import indisoluble.a_healthy_dns.dns_udp_handler as duh

from indisoluble.a_healthy_dns.dns_server_config import DNSServerConfig


@pytest.fixture
def config():
    return DNSServerConfig(
        hosted_zone="dev.example.com",
        name_servers=["ns1.example.com", "ns2.example.com"],
        resolutions={"www": ["192.168.1.1", "192.168.1.2"]},
        ttl_a=300,
        ttl_ns=86400,
        soa_serial=1234567890,
        soa_refresh=7200,
        soa_retry=3600,
        soa_expire=1209600,
    )


@pytest.fixture
def dns_response():
    return dns.message.make_response(
        dns.message.make_query("dev.example.com", dns.rdatatype.A)
    )


def test_handle_a_record_success(config, dns_response):
    qname = "www.dev.example.com."
    duh._handle_a_record(dns_response, qname, config)

    assert len(dns_response.answer) == 1
    rrset = dns_response.answer[0]
    assert rrset.name.to_text() == qname
    assert rrset.rdtype == dns.rdatatype.A
    assert rrset.ttl == config.ttl_a
    assert len(rrset) == 2
    addresses = [rdata.address for rdata in rrset]
    assert "192.168.1.1" in addresses
    assert "192.168.1.2" in addresses


def test_handle_a_record_unknown_domain(config, dns_response):
    qname = "unknown.dev.example.com."
    duh._handle_a_record(dns_response, qname, config)

    assert dns_response.rcode() == dns.rcode.NXDOMAIN
    assert len(dns_response.answer) == 0


def test_handle_ns_record_success(config, dns_response):
    qname = "dev.example.com."
    duh._handle_ns_record(dns_response, qname, config)

    assert len(dns_response.answer) == 1
    rrset = dns_response.answer[0]
    assert rrset.name.to_text() == qname
    assert rrset.rdtype == dns.rdatatype.NS
    assert rrset.ttl == config.ttl_ns
    assert len(rrset) == 2
    ns_targets = [rdata.target.to_text() for rdata in rrset]
    assert "ns1.example.com." in ns_targets
    assert "ns2.example.com." in ns_targets


def test_handle_ns_record_unknown_zone(config, dns_response):
    qname = "unknown.com."
    duh._handle_ns_record(dns_response, qname, config)

    assert dns_response.rcode() == dns.rcode.NXDOMAIN
    assert len(dns_response.answer) == 0


def test_handle_soa_record_success(config, dns_response):
    qname = "dev.example.com."
    duh._handle_soa_record(dns_response, qname, config)

    assert len(dns_response.answer) == 1
    rrset = dns_response.answer[0]
    assert rrset.name.to_text() == qname
    assert rrset.rdtype == dns.rdatatype.SOA
    assert rrset.ttl == config.ttl_a
    assert len(rrset) == 1
    soa = rrset[0]
    assert soa.mname.to_text() == "ns1.example.com."
    assert soa.rname.to_text() == "hostmaster.dev.example.com."
    assert soa.serial == config.soa_serial
    assert soa.refresh == config.soa_refresh
    assert soa.retry == config.soa_retry
    assert soa.expire == config.soa_expire
    assert soa.minimum == config.ttl_a


def test_handle_soa_record_unknown_zone(config, dns_response):
    qname = "unknown.com."
    duh._handle_soa_record(dns_response, qname, config)

    assert dns_response.rcode() == dns.rcode.NXDOMAIN
    assert len(dns_response.answer) == 0


def test_handle_valid_a_query(config):
    # Set up mocks
    mock_query = dns.message.make_query("www.dev.example.com", dns.rdatatype.A)

    mock_server = Mock()
    mock_server.config = config

    sock_mock = Mock()

    # Use patch as a context manager to limit its scope
    with patch("dns.message.from_wire", return_value=mock_query) as mock_from_wire:
        handler = duh.DNSUDPHandler(
            request=(b"dummy_data", sock_mock),
            client_address=("127.0.0.1", 53535),
            server=mock_server,
        )
        handler.handle()

        # Verify from_wire was called
        assert mock_from_wire.called

    # Verify the response
    assert sock_mock.sendto.called

    args = sock_mock.sendto.call_args[0]
    wire_response = args[0]
    response = dns.message.from_wire(wire_response)

    assert len(response.answer) == 1
    rrset = response.answer[0]
    assert rrset.name.to_text() == "www.dev.example.com."
    assert rrset.rdtype == dns.rdatatype.A
    assert rrset.ttl == config.ttl_a
    assert len(rrset) == 2
    addresses = [rdata.address for rdata in rrset]
    assert "192.168.1.1" in addresses
    assert "192.168.1.2" in addresses


@patch("dns.message.from_wire")
def test_handle_query_exception(mock_from_wire, config):
    # Set up mocks
    mock_from_wire.side_effect = dns.exception.DNSException("Test exception")

    # Create a mock server and handler
    mock_server = Mock()
    mock_server.config = config

    sock_mock = Mock()

    handler = duh.DNSUDPHandler(
        request=(b"invalid_data", sock_mock),
        client_address=("127.0.0.1", 53535),
        server=mock_server,
    )

    # The handler should handle the exception gracefully
    handler.handle()
    assert not sock_mock.sendto.called


def test_handle_query_without_question(config):
    # Set up mocks
    mock_query = dns.message.Message()

    mock_server = Mock()
    mock_server.config = config

    sock_mock = Mock()

    # Use patch as a context manager to limit its scope
    with patch("dns.message.from_wire", return_value=mock_query) as mock_from_wire:
        handler = duh.DNSUDPHandler(
            request=(b"dummy_data", sock_mock),
            client_address=("127.0.0.1", 53535),
            server=mock_server,
        )
        handler.handle()

        # Verify from_wire was called
        assert mock_from_wire.called

    # Verify the response
    assert sock_mock.sendto.called

    args = sock_mock.sendto.call_args[0]
    wire_response = args[0]
    response = dns.message.from_wire(wire_response)

    assert response.rcode() == dns.rcode.FORMERR
    assert len(response.answer) == 0


def test_handle_unsupported_query_type(config):
    # Set up mocks
    mock_query = dns.message.make_query("dev.example.com", dns.rdatatype.MX)

    mock_server = Mock()
    mock_server.config = config

    sock_mock = Mock()

    # Use patch as a context manager to limit its scope
    with patch("dns.message.from_wire", return_value=mock_query) as mock_from_wire:
        handler = duh.DNSUDPHandler(
            request=(b"dummy_data", sock_mock),
            client_address=("127.0.0.1", 53535),
            server=mock_server,
        )
        handler.handle()

        # Verify from_wire was called
        assert mock_from_wire.called

    # Verify the response
    assert sock_mock.sendto.called

    args = sock_mock.sendto.call_args[0]
    wire_response = args[0]
    response = dns.message.from_wire(wire_response)

    assert response.rcode() == dns.rcode.NOTIMP
    assert len(response.answer) == 0
