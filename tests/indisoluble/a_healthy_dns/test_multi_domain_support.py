#!/usr/bin/env python3

"""Tests for multi-domain support functionality."""

import dns.name
import dns.message
import dns.rcode
import dns.rdataclass
import dns.rdatatype
import dns.zone

import pytest

from unittest.mock import MagicMock

from indisoluble.a_healthy_dns.dns_server_udp_handler import _update_response


@pytest.fixture
def primary_zone():
    return dns.name.from_text("primary.com.")


@pytest.fixture
def alias_zones():
    return frozenset([
        dns.name.from_text("alias1.com."),
        dns.name.from_text("alias2.com."),
    ])


@pytest.fixture
def mock_zone(primary_zone):
    zone = MagicMock()
    zone.origin = primary_zone
    zone.rdclass = dns.rdataclass.IN
    return zone


@pytest.fixture
def mock_reader():
    reader = MagicMock(spec=dns.zone.Transaction)
    return reader


@pytest.fixture
def mock_rdataset():
    mock_rdataset = MagicMock()
    mock_rdataset.rdclass = dns.rdataclass.IN
    mock_rdataset.rdtype = dns.rdatatype.A
    mock_rdataset.ttl = 300
    return mock_rdataset


@pytest.fixture
def mock_rdata():
    mock_rdata = MagicMock()
    mock_rdata.rdclass = dns.rdataclass.IN
    mock_rdata.rdtype = dns.rdatatype.A
    return mock_rdata


def _setup_successful_lookup(mock_zone, mock_reader, mock_rdataset, mock_rdata):
    mock_rdataset.__iter__.return_value = [mock_rdata]
    mock_node = MagicMock()
    mock_node.get_rdataset.return_value = mock_rdataset
    mock_reader.get_node.return_value = mock_node
    mock_zone.reader.return_value.__enter__.return_value = mock_reader
    return mock_node


def test_update_response_for_primary_zone_query_uses_relative_lookup(
    mock_zone, mock_reader, mock_rdata, mock_rdataset, alias_zones
):
    query_name = dns.name.from_text("www.primary.com.")
    query_type = dns.rdatatype.A

    _setup_successful_lookup(mock_zone, mock_reader, mock_rdataset, mock_rdata)

    query = dns.message.make_query(query_name, query_type)
    response = dns.message.make_response(query)

    _update_response(response, query_name, query_type, mock_zone, alias_zones)

    mock_reader.get_node.assert_called_once_with(dns.name.from_text("www", origin=None))
    assert response.rcode() == dns.rcode.NOERROR
    assert len(response.answer) == 1
    assert response.answer[0].name == query_name


def test_update_response_for_alias_zone_query_uses_relative_lookup(
    mock_zone, mock_reader, mock_rdata, mock_rdataset, alias_zones
):
    query_name = dns.name.from_text("www.alias1.com.")
    query_type = dns.rdatatype.A

    _setup_successful_lookup(mock_zone, mock_reader, mock_rdataset, mock_rdata)

    query = dns.message.make_query(query_name, query_type)
    response = dns.message.make_response(query)

    _update_response(response, query_name, query_type, mock_zone, alias_zones)

    mock_reader.get_node.assert_called_once_with(dns.name.from_text("www", origin=None))
    assert response.rcode() == dns.rcode.NOERROR
    assert len(response.answer) == 1
    assert response.answer[0].name == query_name


def test_update_response_for_second_alias_zone_query_uses_relative_lookup(
    mock_zone, mock_reader, mock_rdata, mock_rdataset, alias_zones
):
    query_name = dns.name.from_text("api.alias2.com.")
    query_type = dns.rdatatype.A

    _setup_successful_lookup(mock_zone, mock_reader, mock_rdataset, mock_rdata)

    query = dns.message.make_query(query_name, query_type)
    response = dns.message.make_response(query)

    _update_response(response, query_name, query_type, mock_zone, alias_zones)

    mock_reader.get_node.assert_called_once_with(dns.name.from_text("api", origin=None))
    assert response.rcode() == dns.rcode.NOERROR
    assert len(response.answer) == 1
    assert response.answer[0].name == query_name


def test_update_response_for_alias_zone_apex_uses_empty_name_lookup(
    mock_zone, mock_reader, mock_rdata, mock_rdataset, alias_zones
):
    query_name = dns.name.from_text("alias1.com.")
    query_type = dns.rdatatype.A

    _setup_successful_lookup(mock_zone, mock_reader, mock_rdataset, mock_rdata)

    query = dns.message.make_query(query_name, query_type)
    response = dns.message.make_response(query)

    _update_response(response, query_name, query_type, mock_zone, alias_zones)

    mock_reader.get_node.assert_called_once_with(dns.name.empty)
    assert response.rcode() == dns.rcode.NOERROR
    assert len(response.answer) == 1
    assert response.answer[0].name == query_name


def test_update_response_with_unknown_zone_query_returns_nxdomain(
    mock_zone, alias_zones
):
    query_name = dns.name.from_text("www.unknown.com.")
    query_type = dns.rdatatype.A

    query = dns.message.make_query(query_name, query_type)
    response = dns.message.make_response(query)

    _update_response(response, query_name, query_type, mock_zone, alias_zones)

    mock_zone.reader.assert_not_called()
    assert response.rcode() == dns.rcode.NXDOMAIN
    assert len(response.answer) == 0


def test_update_response_with_relative_name_uses_lookup_as_is(
    mock_zone, mock_reader, mock_rdata, mock_rdataset, alias_zones
):
    query_name = dns.name.from_text("www", origin=None)
    query_type = dns.rdatatype.A

    _setup_successful_lookup(mock_zone, mock_reader, mock_rdataset, mock_rdata)

    query = dns.message.make_query(query_name, query_type)
    response = dns.message.make_response(query)

    _update_response(response, query_name, query_type, mock_zone, alias_zones)

    mock_reader.get_node.assert_called_once_with(query_name)
    assert response.rcode() == dns.rcode.NOERROR
    assert len(response.answer) == 1
    assert response.answer[0].name == query_name


def test_update_response_with_empty_alias_zones_primary_query(
    mock_zone, mock_reader, mock_rdata, mock_rdataset
):
    alias_zones = frozenset()
    query_name = dns.name.from_text("www.primary.com.")
    query_type = dns.rdatatype.A

    _setup_successful_lookup(mock_zone, mock_reader, mock_rdataset, mock_rdata)

    query = dns.message.make_query(query_name, query_type)
    response = dns.message.make_response(query)

    _update_response(response, query_name, query_type, mock_zone, alias_zones)

    mock_reader.get_node.assert_called_once_with(dns.name.from_text("www", origin=None))
    assert response.rcode() == dns.rcode.NOERROR
    assert len(response.answer) == 1


def test_update_response_with_empty_alias_zones_unknown_domain_returns_nxdomain(
    mock_zone
):
    alias_zones = frozenset()
    query_name = dns.name.from_text("www.unknown.com.")
    query_type = dns.rdatatype.A

    query = dns.message.make_query(query_name, query_type)
    response = dns.message.make_response(query)

    _update_response(response, query_name, query_type, mock_zone, alias_zones)

    mock_zone.reader.assert_not_called()
    assert response.rcode() == dns.rcode.NXDOMAIN
