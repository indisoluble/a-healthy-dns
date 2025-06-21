#!/usr/bin/env python3

import dns.rdataclass
import dns.rdatatype

from indisoluble.a_healthy_dns.records.ns_record import make_ns_record


def test_make_ns_record_with_valid_name_servers():
    max_interval = 60
    expected_ttl = 3600  # max_interval * 2 * 30
    name_servers = frozenset(["ns1.example.com", "ns2.example.com"])

    result = make_ns_record(max_interval, name_servers)

    assert result is not None
    assert result.ttl == expected_ttl
    assert result.rdtype == dns.rdatatype.NS
    assert result.rdclass == dns.rdataclass.IN

    rdataset_str = str(result)
    assert all(ns in rdataset_str for ns in name_servers)


def test_make_ns_record_with_single_name_server():
    max_interval = 45
    expected_ttl = 2700  # max_interval * 2 * 30
    name_servers = frozenset(["ns1.example.com"])

    result = make_ns_record(max_interval, name_servers)

    assert result is not None
    assert result.ttl == expected_ttl
    assert result.rdtype == dns.rdatatype.NS
    assert result.rdclass == dns.rdataclass.IN

    assert "ns1.example.com" in str(result)
