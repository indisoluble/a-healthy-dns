#!/usr/bin/env python3

import dns.name
import dns.rdataclass
import dns.rdatatype
import pytest

from indisoluble.a_healthy_dns.records.ns_record import make_ns_record
from indisoluble.a_healthy_dns.records.time import _RFC8767_MAX_TTL as RFC8767_MAX_TTL


def _assert_ns_rdataset(rdataset, *, ttl, name_servers):
    assert rdataset is not None
    assert rdataset.ttl == ttl
    assert rdataset.rdtype == dns.rdatatype.NS
    assert rdataset.rdclass == dns.rdataclass.IN

    assert {rdata.target for rdata in rdataset} == {
        dns.name.from_text(name_server, origin=None) for name_server in name_servers
    }


class TestNsRecordGeneration:
    @pytest.mark.parametrize(
        "max_interval,name_servers,expected_ttl",
        [
            (
                60,
                frozenset(["ns1.example.com", "ns2.example.com"]),
                3600,
            ),
            (
                45,
                frozenset(["ns1.example.com"]),
                2700,
            ),
        ],
    )
    def test_make_ns_record_returns_expected_rdataset(
        self, max_interval, name_servers, expected_ttl
    ):
        result = make_ns_record(max_interval, name_servers)

        _assert_ns_rdataset(
            result,
            ttl=expected_ttl,
            name_servers=name_servers,
        )

    def test_caps_ttl_to_rfc8767_max(self):
        max_interval = 100_000_000
        name_servers = frozenset(["ns1.example.com"])

        result = make_ns_record(max_interval, name_servers)

        _assert_ns_rdataset(
            result,
            ttl=RFC8767_MAX_TTL,
            name_servers=name_servers,
        )
