#!/usr/bin/env python3

import dns.flags
import dns.message
import dns.name
import dns.rcode
import dns.rdatatype
import pytest

from . import support as s


class TestAnyMinimization:
    @pytest.mark.parametrize(
        "qname",
        [
            s.SUBDOMAIN_FQDN,
            s.ZONE_FQDN,
            s.EMPTY_NON_TERMINAL_FQDN,
            s.ALIAS_SUBDOMAIN_FQDN,
            s.ALIAS_EMPTY_NON_TERMINAL_FQDN,
        ],
        ids=[
            "existing-owner",
            "zone-apex",
            "empty-non-terminal",
            "alias-existing-owner",
            "alias-empty-non-terminal",
        ],
    )
    def test_any_query_at_existing_name_returns_synthesized_hinfo(
        self, live_server, qname
    ):
        host, port = live_server
        query = dns.message.make_query(qname, dns.rdatatype.ANY)
        response = s.udp_query(host, port, query)

        assert response.rcode() == dns.rcode.NOERROR
        assert response.id == query.id
        s.assert_section_counts(response, answer=1)
        assert response.answer[0].name == dns.name.from_text(qname)
        assert response.answer[0].rdtype == dns.rdatatype.HINFO
        assert response.answer[0].ttl == 60
        rdata = next(iter(response.answer[0]))
        assert rdata.cpu == b"RFC8482"
        assert rdata.os == b""
        s.assert_response_flags(response)

    @pytest.mark.parametrize(
        "qname,expected_soa_name",
        [
            (s.ABSENT_FQDN, s.ZONE_FQDN),
            (s.ALIAS_ABSENT_FQDN, s.ALIAS_ZONE_FQDN),
        ],
        ids=["primary-absent-owner", "alias-absent-owner"],
    )
    def test_any_query_at_absent_owner_remains_nxdomain(
        self, live_server, qname, expected_soa_name
    ):
        host, port = live_server
        query = dns.message.make_query(qname, dns.rdatatype.ANY)
        response = s.udp_query(host, port, query)

        assert response.rcode() == dns.rcode.NXDOMAIN
        s.assert_section_counts(response, authority=1)
        assert response.authority[0].name == dns.name.from_text(expected_soa_name)
        s.assert_response_flags(response)

    def test_any_hinfo_ttl_uses_negative_response_soa_ttl(
        self, dns_response, zone_origins
    ):
        query_name = dns.name.from_text("test", origin=zone_origins.primary)
        a_rdataset = s.make_a_rdataset("192.0.2.1")
        soa_rdataset = s.make_soa_rdataset(ttl=30, minimum=60)
        transaction = s.FakeTransaction(
            nodes={dns.name.from_text("test", origin=None): s.FakeNode(a_rdataset)},
            soa_rdataset=soa_rdataset,
        )
        zone = s.make_zone(zone_origins, transaction)

        s.update_test_response(
            dns_response, query_name, dns.rdatatype.ANY, zone, zone_origins
        )

        assert dns_response.rcode() == dns.rcode.NOERROR
        assert bool(dns_response.flags & dns.flags.AA)
        expected_hinfo = s.make_hinfo_rdataset(s.soa_authority_ttl(soa_rdataset))
        s.assert_answer_rrset(
            dns_response,
            name=query_name,
            rdtype=dns.rdatatype.HINFO,
            rdataset=expected_hinfo,
        )
