#!/usr/bin/env python3

import dns.name
import dns.rdatatype
import pytest

from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp
from indisoluble.a_healthy_dns.records.a_healthy_record import AHealthyRecord
from indisoluble.a_healthy_dns.records.a_record import make_a_record
from indisoluble.a_healthy_dns.records.ns_record import make_ns_record
from indisoluble.a_healthy_dns.records.soa_record import iter_soa_record
from indisoluble.a_healthy_dns.records.time import (
    _RFC8767_MAX_TTL as RFC8767_MAX_TTL,
    calculate_a_ttl,
    calculate_ns_ttl,
    calculate_soa_min_ttl,
    calculate_soa_ttl,
)

from . import support as s


class TestTtlBearingResponses:
    @pytest.mark.parametrize(
        "calculator",
        [
            calculate_a_ttl,
            calculate_ns_ttl,
            calculate_soa_ttl,
            calculate_soa_min_ttl,
        ],
    )
    def test_ttl_calculators_clamp_generated_dns_ttls_to_rfc8767_range(
        self, calculator
    ):
        assert calculator(1_500_000_000) == RFC8767_MAX_TTL
        assert calculator(0) == 0

    def test_generated_a_record_ttl_is_clamped_to_rfc8767_range(self):
        healthy_record = AHealthyRecord(
            subdomain=dns.name.from_text("test.example.com"),
            healthy_ips=[AHealthyIp("192.0.2.1", 80, True)],
        )

        rdataset = make_a_record(1_500_000_000, healthy_record)

        assert rdataset.ttl == RFC8767_MAX_TTL
        assert rdataset.rdtype == dns.rdatatype.A

    def test_generated_ns_record_ttl_is_clamped_to_rfc8767_range(self):
        rdataset = make_ns_record(100_000_000, frozenset(["ns1.example.com"]))

        assert rdataset.ttl == RFC8767_MAX_TTL
        assert rdataset.rdtype == dns.rdatatype.NS

    @pytest.mark.parametrize(
        "max_interval,expected_ttl",
        [
            (60, 3600),
            (2_000_000_000, RFC8767_MAX_TTL),
        ],
        ids=["ordinary", "clamped"],
    )
    def test_generated_soa_record_ttl_and_minimum_follow_rfc8767_range(
        self, max_interval, expected_ttl
    ):
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                "indisoluble.a_healthy_dns.records.soa_record._iter_soa_serial",
                lambda: iter([1234567890]),
            )
            soa_iterator = iter_soa_record(
                max_interval,
                dns.name.from_text("example.com"),
                "ns1.example.com.",
            )
            rdataset = next(soa_iterator)

        soa_rdata = next(iter(rdataset))
        assert rdataset.ttl == expected_ttl
        assert 0 <= soa_rdata.minimum <= RFC8767_MAX_TTL

    def test_negative_response_soa_authority_ttl_is_rfc8767_ttl_bearing_value(
        self, dns_response, zone_origins
    ):
        query_name = dns.name.from_text("nonexistent", origin=zone_origins.primary)
        soa_rdataset = s.make_soa_rdataset(ttl=30, minimum=60)
        transaction = s.FakeTransaction(soa_rdataset=soa_rdataset)
        zone = s.make_zone(zone_origins, transaction)

        s.update_test_response(
            dns_response, query_name, dns.rdatatype.A, zone, zone_origins
        )

        assert dns_response.authority[0].ttl == 30
        assert 0 <= dns_response.authority[0].ttl <= RFC8767_MAX_TTL
