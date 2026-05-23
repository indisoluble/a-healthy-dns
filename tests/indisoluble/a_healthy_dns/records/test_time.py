#!/usr/bin/env python3

import pytest

from indisoluble.a_healthy_dns.records.time import (
    _RFC8767_MAX_TTL as RFC8767_MAX_TTL,
    calculate_a_ttl,
    calculate_dnskey_ttl,
    calculate_ns_ttl,
    calculate_rrsig_lifetime,
    calculate_soa_expire,
    calculate_soa_min_ttl,
    calculate_soa_refresh,
    calculate_soa_retry,
    calculate_soa_ttl,
)

_MAX_INTERVAL = 60
_OVERSIZED_INTERVAL = 1_500_000_000
_NON_POSITIVE_INTERVALS = [0, -60]
_NON_POSITIVE_INTERVAL_IDS = ["zero-interval", "negative-interval"]

_TTL_CASES = [
    ("a-ttl", calculate_a_ttl, 120),
    ("ns-ttl", calculate_ns_ttl, 3600),
    ("soa-ttl", calculate_soa_ttl, 3600),
    ("soa-refresh", calculate_soa_refresh, 1200),
    ("soa-retry", calculate_soa_retry, 120),
    ("soa-expire", calculate_soa_expire, 600),
    ("soa-min-ttl", calculate_soa_min_ttl, 120),
    ("dnskey-ttl", calculate_dnskey_ttl, 1200),
]

_TTL_EXPECTATION_PARAMS = [
    (calculator, expected) for case_id, calculator, expected in _TTL_CASES
]
_TTL_CALCULATOR_PARAMS = [calculator for case_id, calculator, expected in _TTL_CASES]
_TTL_IDS = [case_id for case_id, calculator, expected in _TTL_CASES]


class TestTtlCalculations:
    @pytest.mark.parametrize(
        "calculator,expected", _TTL_EXPECTATION_PARAMS, ids=_TTL_IDS
    )
    def test_ttl_calculators_derive_values_from_max_interval(self, calculator, expected):
        assert calculator(_MAX_INTERVAL) == expected

    @pytest.mark.parametrize("calculator", _TTL_CALCULATOR_PARAMS, ids=_TTL_IDS)
    def test_ttl_calculators_clamp_values_to_rfc8767_max(self, calculator):
        assert calculator(_OVERSIZED_INTERVAL) == RFC8767_MAX_TTL

    @pytest.mark.parametrize(
        "max_interval", _NON_POSITIVE_INTERVALS, ids=_NON_POSITIVE_INTERVAL_IDS
    )
    @pytest.mark.parametrize("calculator", _TTL_CALCULATOR_PARAMS, ids=_TTL_IDS)
    def test_ttl_calculators_clamp_non_positive_outputs_to_zero(
        self, calculator, max_interval
    ):
        assert calculator(max_interval) == 0


class TestRRSigLifetimeCalculation:
    def test_rrsig_lifetime_derives_resign_and_expiration_from_soa_timing(self):
        lifetime = calculate_rrsig_lifetime(_MAX_INTERVAL)

        assert lifetime.resign == 1200
        assert lifetime.expiration == 3120

    @pytest.mark.parametrize(
        "max_interval", _NON_POSITIVE_INTERVALS, ids=_NON_POSITIVE_INTERVAL_IDS
    )
    def test_rrsig_lifetime_returns_zero_timing_for_non_positive_interval(
        self, max_interval
    ):
        lifetime = calculate_rrsig_lifetime(max_interval)

        assert lifetime.resign == 0
        assert lifetime.expiration == 0
