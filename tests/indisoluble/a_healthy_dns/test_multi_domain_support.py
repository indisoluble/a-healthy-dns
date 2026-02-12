#!/usr/bin/env python3

"""Tests for multi-domain support functionality."""

import dns.name
import dns.message
import dns.rcode
import dns.rdataclass
import dns.rdatatype

import pytest

from unittest.mock import MagicMock

from indisoluble.a_healthy_dns.dns_server_udp_handler import (
    _normalize_query_name,
    _update_response,
)


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


def test_normalize_query_name_for_primary_zone(primary_zone, alias_zones):
    """Test that queries for the primary zone are not modified."""
    query_name = dns.name.from_text("www.primary.com.")
    normalized = _normalize_query_name(query_name, primary_zone, alias_zones)
    assert normalized == query_name


def test_normalize_query_name_for_alias_zone(primary_zone, alias_zones):
    """Test that queries for alias zones are normalized to the primary zone."""
    query_name = dns.name.from_text("www.alias1.com.")
    normalized = _normalize_query_name(query_name, primary_zone, alias_zones)
    expected = dns.name.from_text("www.primary.com.")
    assert normalized == expected


def test_normalize_query_name_for_second_alias_zone(primary_zone, alias_zones):
    """Test that queries for the second alias zone are normalized correctly."""
    query_name = dns.name.from_text("api.alias2.com.")
    normalized = _normalize_query_name(query_name, primary_zone, alias_zones)
    expected = dns.name.from_text("api.primary.com.")
    assert normalized == expected


def test_normalize_query_name_for_alias_zone_apex(primary_zone, alias_zones):
    """Test that queries for the alias zone apex are normalized to primary apex."""
    query_name = dns.name.from_text("alias1.com.")
    normalized = _normalize_query_name(query_name, primary_zone, alias_zones)
    assert normalized == primary_zone


def test_normalize_query_name_for_unknown_zone(primary_zone, alias_zones):
    """Test that queries for unknown zones return None."""
    query_name = dns.name.from_text("www.unknown.com.")
    normalized = _normalize_query_name(query_name, primary_zone, alias_zones)
    assert normalized is None


def test_normalize_query_name_for_relative_name(primary_zone, alias_zones):
    """Test that relative names are passed through unchanged."""
    query_name = dns.name.from_text("www", origin=None)
    normalized = _normalize_query_name(query_name, primary_zone, alias_zones)
    assert normalized == query_name


def test_update_response_with_alias_zone_query(
    mock_zone, mock_reader, mock_rdata, mock_rdataset, primary_zone, alias_zones
):
    """Test that queries for alias zones return data from the primary zone."""
    # Setup
    query_name = dns.name.from_text("www.alias1.com.")
    query_type = dns.rdatatype.A
    
    # Mock the zone reader to return the data
    mock_rdataset.__iter__.return_value = [mock_rdata]
    
    mock_node = MagicMock()
    mock_node.get_rdataset.return_value = mock_rdataset
    
    mock_reader.get_node.return_value = mock_node
    mock_zone.reader.return_value.__enter__.return_value = mock_reader
    
    # Create response
    query = dns.message.make_query(query_name, query_type)
    response = dns.message.make_response(query)
    
    # Call function
    _update_response(response, query_name, query_type, mock_zone, alias_zones)
    
    # Assertions
    assert response.rcode() == dns.rcode.NOERROR
    assert len(response.answer) == 1
    # The response should use the original query name (alias), not the normalized one
    assert response.answer[0].name == query_name


def test_update_response_with_unknown_zone_query(
    mock_zone, mock_reader, primary_zone, alias_zones
):
    """Test that queries for unknown zones return NXDOMAIN."""
    # Setup
    query_name = dns.name.from_text("www.unknown.com.")
    query_type = dns.rdatatype.A
    
    # Create response
    query = dns.message.make_query(query_name, query_type)
    response = dns.message.make_response(query)
    
    # Call function
    _update_response(response, query_name, query_type, mock_zone, alias_zones)
    
    # Assertions
    assert response.rcode() == dns.rcode.NXDOMAIN
    assert len(response.answer) == 0


def test_normalize_query_name_with_empty_alias_zones(primary_zone):
    """Test normalization with no alias zones configured."""
    alias_zones = frozenset()
    query_name = dns.name.from_text("www.primary.com.")
    normalized = _normalize_query_name(query_name, primary_zone, alias_zones)
    assert normalized == query_name


def test_normalize_query_name_with_empty_alias_zones_unknown_domain(primary_zone):
    """Test normalization with no alias zones for unknown domain returns None."""
    alias_zones = frozenset()
    query_name = dns.name.from_text("www.unknown.com.")
    normalized = _normalize_query_name(query_name, primary_zone, alias_zones)
    assert normalized is None
