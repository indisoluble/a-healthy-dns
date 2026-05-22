#!/usr/bin/env python3

import dns.name
import dns.rdataclass
import dns.rdatatype
import pytest

from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp
from indisoluble.a_healthy_dns.records.a_healthy_record import AHealthyRecord
from indisoluble.a_healthy_dns.records.a_record import make_a_record
from indisoluble.a_healthy_dns.records.time import _RFC8767_MAX_TTL as RFC8767_MAX_TTL

_SUBDOMAIN = dns.name.from_text("test.example.com")
_HEALTH_PORT = 80


def _make_healthy_record(ip_statuses):
    healthy_ips = [
        AHealthyIp(ip, _HEALTH_PORT, is_healthy) for ip, is_healthy in ip_statuses
    ]
    return AHealthyRecord(subdomain=_SUBDOMAIN, healthy_ips=healthy_ips)


def _assert_a_rdataset(rdataset, *, ttl, expected_ips):
    assert rdataset is not None
    assert rdataset.ttl == ttl
    assert rdataset.rdtype == dns.rdatatype.A
    assert rdataset.rdclass == dns.rdataclass.IN

    assert {str(rdata) for rdata in rdataset} == set(expected_ips)


class TestARecordGeneration:
    @pytest.mark.parametrize(
        "max_interval,ip_statuses,expected_ttl,expected_ips",
        [
            (
                60,
                [
                    ("192.168.1.1", True),
                    ("192.168.1.2", True),
                ],
                120,
                {"192.168.1.1", "192.168.1.2"},
            ),
            (
                45,
                [
                    ("192.168.1.1", True),
                    ("192.168.1.2", False),
                    ("192.168.1.3", True),
                ],
                90,
                {"192.168.1.1", "192.168.1.3"},
            ),
        ],
        ids=["all-healthy", "mixed-healthy-and-unhealthy"],
    )
    def test_make_a_record_returns_only_healthy_ips(
        self, max_interval, ip_statuses, expected_ttl, expected_ips
    ):
        healthy_record = _make_healthy_record(ip_statuses)

        result = make_a_record(max_interval, healthy_record)

        _assert_a_rdataset(
            result,
            ttl=expected_ttl,
            expected_ips=expected_ips,
        )

    def test_make_a_record_returns_none_when_no_ips_are_healthy(self):
        healthy_record = _make_healthy_record(
            [
                ("192.168.1.1", False),
                ("192.168.1.2", False),
            ]
        )

        assert make_a_record(60, healthy_record) is None

    def test_caps_ttl_to_rfc8767_max(self):
        max_interval = 1_500_000_000
        healthy_record = _make_healthy_record([("192.168.1.1", True)])

        result = make_a_record(max_interval, healthy_record)

        _assert_a_rdataset(
            result,
            ttl=RFC8767_MAX_TTL,
            expected_ips={"192.168.1.1"},
        )
