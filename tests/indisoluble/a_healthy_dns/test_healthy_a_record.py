#!/usr/bin/env python3

import dns.name
import pytest

from indisoluble.a_healthy_dns.healthy_a_record import HealthyARecord
from indisoluble.a_healthy_dns.healthy_ip import HealthyIp


def test_init_with_valid_parameters():
    subdomain = dns.name.from_text("test.example.com")
    ttl_a = 300
    healthy_ips = frozenset(
        [HealthyIp("192.168.1.1", 80, True), HealthyIp("192.168.1.2", 80, True)]
    )

    record = HealthyARecord(subdomain=subdomain, ttl_a=ttl_a, healthy_ips=healthy_ips)

    assert record.subdomain == subdomain
    assert record.ttl_a == ttl_a
    assert record.healthy_ips == healthy_ips


@pytest.mark.parametrize("invalid_ttl", [0, -1])
def test_init_with_invalid_ttl(invalid_ttl):
    with pytest.raises(ValueError, match="TTL for A records must be positive"):
        HealthyARecord(
            subdomain=dns.name.from_text("test.example.com"),
            ttl_a=invalid_ttl,
            healthy_ips=frozenset([HealthyIp("192.168.1.1", 80, True)]),
        )


def test_equality_with_same_subdomain():
    subdomain = dns.name.from_text("test.example.com")

    record1 = HealthyARecord(
        subdomain=subdomain,
        ttl_a=300,
        healthy_ips=frozenset([HealthyIp("192.168.1.1", 80, True)]),
    )
    record2 = HealthyARecord(
        subdomain=subdomain,
        ttl_a=600,
        healthy_ips=frozenset([HealthyIp("192.168.1.2", 443, False)]),
    )

    assert record1 == record2
    assert set([record1]) == set([record2])
    assert set([record1, record2]) == set([record1])
    assert set([record1, record2]) == set([record1])
    assert set([record1, record2, record2]) == set([record1])


def test_equality_with_different_subdomain():
    ttl_a = 300
    healthy_ip = HealthyIp("192.168.1.1", 80, True)

    record1 = HealthyARecord(
        subdomain=dns.name.from_text("test1.example.com"),
        ttl_a=ttl_a,
        healthy_ips=frozenset([healthy_ip]),
    )
    record2 = HealthyARecord(
        subdomain=dns.name.from_text("test2.example.com"),
        ttl_a=ttl_a,
        healthy_ips=frozenset([healthy_ip]),
    )

    assert record1 != record2
    assert set([record1]) != set([record2])


def test_repr():
    subdomain = dns.name.from_text("test.example.com")
    ttl_a = 300
    healthy_ip1 = HealthyIp("192.168.1.1", 80, True)
    healthy_ip2 = HealthyIp("192.168.1.2", 80, True)
    record = HealthyARecord(
        subdomain=subdomain,
        ttl_a=ttl_a,
        healthy_ips=frozenset([healthy_ip1, healthy_ip2]),
    )

    as_text = f"{record}"

    assert as_text.startswith(
        f"HealthyARecord(subdomain={subdomain}, ttl_a={ttl_a}, healthy_ips=["
    )
    assert f"{healthy_ip1}" in as_text
    assert f"{healthy_ip2}" in as_text
