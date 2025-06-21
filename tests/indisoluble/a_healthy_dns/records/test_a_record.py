#!/usr/bin/env python3

import dns.name
import dns.rdataclass
import dns.rdatatype

from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp
from indisoluble.a_healthy_dns.records.a_healthy_record import AHealthyRecord
from indisoluble.a_healthy_dns.records.a_record import make_a_record


def test_make_a_record_with_healthy_ips():
    max_interval = 60
    expected_ttl = 120  # max_interval * 2
    subdomain = dns.name.from_text("test.example.com")
    healthy_ips = [
        AHealthyIp("192.168.1.1", 80, True),
        AHealthyIp("192.168.1.2", 80, True),
    ]
    healthy_record = AHealthyRecord(subdomain=subdomain, healthy_ips=healthy_ips)

    result = make_a_record(max_interval, healthy_record)

    assert result is not None
    assert result.ttl == expected_ttl
    assert result.rdtype == dns.rdatatype.A
    assert result.rdclass == dns.rdataclass.IN

    rdataset_str = str(result)
    assert all(ip.ip in rdataset_str for ip in healthy_ips)


def test_make_a_record_with_mixed_healthy_and_unhealthy_ips():
    max_interval = 45
    expected_ttl = 90  # max_interval * 2
    subdomain = dns.name.from_text("test.example.com")
    healthy_ips = [
        AHealthyIp("192.168.1.1", 80, True),
        AHealthyIp("192.168.1.2", 80, False),
        AHealthyIp("192.168.1.3", 80, True),
    ]
    healthy_record = AHealthyRecord(subdomain=subdomain, healthy_ips=healthy_ips)

    result = make_a_record(max_interval, healthy_record)

    assert result is not None
    assert result.ttl == expected_ttl
    assert result.rdtype == dns.rdatatype.A
    assert result.rdclass == dns.rdataclass.IN

    rdataset_str = str(result)
    assert all(ip.ip in rdataset_str for ip in healthy_ips if ip.is_healthy)
    assert all(ip.ip not in rdataset_str for ip in healthy_ips if not ip.is_healthy)


def test_make_a_record_with_no_healthy_ips():
    max_interval = 60
    subdomain = dns.name.from_text("test.example.com")
    healthy_ips = [
        AHealthyIp("192.168.1.1", 80, False),
        AHealthyIp("192.168.1.2", 80, False),
    ]
    healthy_record = AHealthyRecord(subdomain=subdomain, healthy_ips=healthy_ips)

    result = make_a_record(max_interval, healthy_record)

    assert result is None
