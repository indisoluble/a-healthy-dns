#!/usr/bin/env python3

from indisoluble.a_healthy_dns.records.time import (
    _RFC8767_MAX_TTL as RFC8767_MAX_TTL,
)
from indisoluble.a_healthy_dns.records.time import calculate_a_ttl
from indisoluble.a_healthy_dns.records.time import calculate_dnskey_ttl
from indisoluble.a_healthy_dns.records.time import calculate_ns_ttl
from indisoluble.a_healthy_dns.records.time import calculate_rrsig_lifetime
from indisoluble.a_healthy_dns.records.time import calculate_soa_expire
from indisoluble.a_healthy_dns.records.time import calculate_soa_min_ttl
from indisoluble.a_healthy_dns.records.time import calculate_soa_refresh
from indisoluble.a_healthy_dns.records.time import calculate_soa_retry
from indisoluble.a_healthy_dns.records.time import calculate_soa_ttl


def test_ttl_formulas_derive_from_max_interval():
    max_interval = 60

    assert calculate_a_ttl(max_interval) == 120
    assert calculate_ns_ttl(max_interval) == 3600
    assert calculate_soa_ttl(max_interval) == 3600
    assert calculate_soa_refresh(max_interval) == 1200
    assert calculate_soa_retry(max_interval) == 120
    assert calculate_soa_expire(max_interval) == 600
    assert calculate_soa_min_ttl(max_interval) == 120
    assert calculate_dnskey_ttl(max_interval) == 1200


def test_rrsig_lifetime_derives_from_soa_timing():
    lifetime = calculate_rrsig_lifetime(60)

    assert lifetime.resign == 1200
    assert lifetime.expiration == 3120


def test_ttl_calculators_clamp_to_rfc8767_max():
    max_interval = 1_500_000_000

    assert calculate_a_ttl(max_interval) == RFC8767_MAX_TTL
    assert calculate_ns_ttl(max_interval) == RFC8767_MAX_TTL
    assert calculate_soa_ttl(max_interval) == RFC8767_MAX_TTL
    assert calculate_soa_refresh(max_interval) == RFC8767_MAX_TTL
    assert calculate_soa_retry(max_interval) == RFC8767_MAX_TTL
    assert calculate_soa_expire(max_interval) == RFC8767_MAX_TTL
    assert calculate_soa_min_ttl(max_interval) == RFC8767_MAX_TTL
    assert calculate_dnskey_ttl(max_interval) == RFC8767_MAX_TTL


def test_ttl_calculators_clamp_non_positive_outputs_to_zero():
    assert calculate_a_ttl(0) == 0
    assert calculate_ns_ttl(0) == 0
    assert calculate_soa_ttl(0) == 0
    assert calculate_soa_refresh(0) == 0
    assert calculate_soa_retry(0) == 0
    assert calculate_soa_expire(0) == 0
    assert calculate_soa_min_ttl(0) == 0
    assert calculate_dnskey_ttl(0) == 0


def test_rrsig_lifetime_with_zero_interval_returns_zero_timing():
    lifetime = calculate_rrsig_lifetime(0)

    assert lifetime.resign == 0
    assert lifetime.expiration == 0
