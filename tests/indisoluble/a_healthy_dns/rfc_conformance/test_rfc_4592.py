#!/usr/bin/env python3

import dns.flags
import dns.name
import dns.rcode
import dns.rdatatype

from . import support as s


class TestOwnerNameExistence:
    def test_exact_owner_name_with_rrset_exists_and_returns_answer(
        self, dns_response, zone_origins
    ):
        query_name = dns.name.from_text("test", origin=None)
        rdataset = s.make_a_rdataset("192.0.2.1")
        transaction = s.FakeTransaction(
            nodes={dns.name.from_text("test", origin=None): s.FakeNode(rdataset)}
        )
        zone = s.make_zone(zone_origins, transaction)

        s.update_test_response(
            dns_response, query_name, dns.rdatatype.A, zone, zone_origins
        )

        assert dns_response.rcode() == dns.rcode.NOERROR
        assert bool(dns_response.flags & dns.flags.AA)
        s.assert_no_authority_or_additional(dns_response)
        s.assert_answer_rrset(
            dns_response,
            name=query_name,
            rdtype=dns.rdatatype.A,
            rdataset=rdataset,
        )

    def test_absolute_owner_name_relativizes_lookup_and_preserves_answer_name(
        self, dns_response, zone_origins
    ):
        query_name = dns.name.from_text("test", origin=zone_origins.primary)
        rdataset = s.make_a_rdataset("192.0.2.1")
        transaction = s.FakeTransaction(
            nodes={dns.name.from_text("test", origin=None): s.FakeNode(rdataset)}
        )
        zone = s.make_zone(zone_origins, transaction)

        s.update_test_response(
            dns_response, query_name, dns.rdatatype.A, zone, zone_origins
        )

        assert dns_response.rcode() == dns.rcode.NOERROR
        assert bool(dns_response.flags & dns.flags.AA)
        s.assert_answer_rrset(
            dns_response,
            name=query_name,
            rdtype=dns.rdatatype.A,
            rdataset=rdataset,
        )

    def test_empty_non_terminal_owner_name_exists_and_returns_nodata(
        self, dns_response, zone_origins, soa_rdataset
    ):
        query_name = dns.name.from_text("empty", origin=zone_origins.primary)
        transaction = s.FakeTransaction(
            soa_rdataset=soa_rdataset,
            names=[dns.name.from_text("leaf.empty", origin=None)],
        )
        zone = s.make_zone(zone_origins, transaction)

        s.update_test_response(
            dns_response, query_name, dns.rdatatype.A, zone, zone_origins
        )

        assert dns_response.rcode() == dns.rcode.NOERROR
        assert bool(dns_response.flags & dns.flags.AA)
        assert len(dns_response.answer) == 0
        s.assert_soa_authority(
            dns_response,
            name=zone_origins.primary,
            expected_ttl=next(iter(soa_rdataset)).minimum,
        )
