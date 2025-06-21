#!/usr/bin/env python3

import dns.name

from indisoluble.a_healthy_dns.records.a_healthy_record import AHealthyRecord
from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp


def test_init_with_valid_parameters():
    subdomain = dns.name.from_text("test.example.com")
    healthy_ips = frozenset(
        [AHealthyIp("192.168.1.1", 80, True), AHealthyIp("192.168.1.2", 80, True)]
    )

    record = AHealthyRecord(subdomain=subdomain, healthy_ips=healthy_ips)

    assert record.subdomain == subdomain
    assert record.healthy_ips == healthy_ips


def test_equality_with_same_subdomain():
    subdomain = dns.name.from_text("test.example.com")

    record1 = AHealthyRecord(
        subdomain=subdomain,
        healthy_ips=frozenset([AHealthyIp("192.168.1.1", 80, True)]),
    )
    record2 = AHealthyRecord(
        subdomain=subdomain,
        healthy_ips=frozenset([AHealthyIp("192.168.1.2", 443, False)]),
    )

    assert record1 == record2
    assert set([record1]) == set([record2])
    assert set([record1, record2]) == set([record1])
    assert set([record1, record2]) == set([record1])
    assert set([record1, record2, record2]) == set([record1])


def test_equality_with_different_subdomain():
    healthy_ip = AHealthyIp("192.168.1.1", 80, True)

    record1 = AHealthyRecord(
        subdomain=dns.name.from_text("test1.example.com"),
        healthy_ips=frozenset([healthy_ip]),
    )
    record2 = AHealthyRecord(
        subdomain=dns.name.from_text("test2.example.com"),
        healthy_ips=frozenset([healthy_ip]),
    )

    assert record1 != record2
    assert set([record1]) != set([record2])


def test_equality_with_non_healthy_a_record():
    record = AHealthyRecord(
        subdomain=dns.name.from_text("test.example.com"),
        healthy_ips=frozenset([AHealthyIp("192.168.1.1", 80, True)]),
    )
    assert record != "test.example.com"


def test_repr():
    subdomain = dns.name.from_text("test.example.com")
    healthy_ip1 = AHealthyIp("192.168.1.1", 80, True)
    healthy_ip2 = AHealthyIp("192.168.1.2", 80, True)
    record = AHealthyRecord(
        subdomain=subdomain, healthy_ips=frozenset([healthy_ip1, healthy_ip2])
    )

    as_text = f"{record}"

    assert as_text.startswith(f"AHealthyRecord(subdomain={subdomain}, healthy_ips=[")
    assert f"{healthy_ip1}" in as_text
    assert f"{healthy_ip2}" in as_text


def test_updated_ips_with_new_ips():
    subdomain = dns.name.from_text("test.example.com")
    original_ips = frozenset(
        [AHealthyIp("192.168.1.1", 80, True), AHealthyIp("192.168.1.2", 80, True)]
    )

    record = AHealthyRecord(subdomain=subdomain, healthy_ips=original_ips)

    new_ips = frozenset(
        [AHealthyIp("192.168.1.3", 80, True), AHealthyIp("192.168.1.4", 443, True)]
    )
    updated_record = record.updated_ips(new_ips)

    assert updated_record is not record
    assert updated_record.subdomain == record.subdomain
    assert updated_record.healthy_ips == new_ips


def test_updated_ips_with_same_ips():
    subdomain = dns.name.from_text("test.example.com")
    healthy_ips = frozenset(
        [AHealthyIp("192.168.1.1", 80, True), AHealthyIp("192.168.1.2", 80, True)]
    )

    record = AHealthyRecord(subdomain=subdomain, healthy_ips=healthy_ips)

    updated_record = record.updated_ips(healthy_ips)

    assert updated_record is record
    assert updated_record.healthy_ips == healthy_ips
