#!/usr/bin/env python3

import dns.message
import dns.rcode
import dns.rdatatype
import pytest

from . import support as s


class TestCaseInsensitiveMatching:
    @pytest.mark.parametrize(
        "qname",
        [
            s.MIXED_CASE_SUBDOMAIN_FQDN,
            s.MIXED_CASE_ALIAS_SUBDOMAIN_FQDN,
        ],
    )
    def test_mixed_case_existing_owner_returns_same_a_answer(self, live_server, qname):
        host, port = live_server
        query = dns.message.make_query(qname, dns.rdatatype.A)
        response = s.udp_query(host, port, query)

        assert response.rcode() == dns.rcode.NOERROR
        assert response.id == query.id
        s.assert_section_counts(response, answer=1)
        assert response.answer[0].rdtype == dns.rdatatype.A
        assert any(str(rdata) == s.SUBDOMAIN_IP for rdata in response.answer[0])
        s.assert_response_flags(response)

    @pytest.mark.parametrize(
        "qname,rdtype,expected_rcode,expected_soa_name",
        [
            (
                s.MIXED_CASE_ABSENT_FQDN,
                dns.rdatatype.A,
                dns.rcode.NXDOMAIN,
                s.ZONE_FQDN,
            ),
            (
                s.MIXED_CASE_SUBDOMAIN_FQDN,
                dns.rdatatype.AAAA,
                dns.rcode.NOERROR,
                s.ZONE_FQDN,
            ),
            (
                s.MIXED_CASE_ALIAS_ABSENT_FQDN,
                dns.rdatatype.A,
                dns.rcode.NXDOMAIN,
                s.ALIAS_ZONE_FQDN,
            ),
            (
                s.MIXED_CASE_ALIAS_SUBDOMAIN_FQDN,
                dns.rdatatype.AAAA,
                dns.rcode.NOERROR,
                s.ALIAS_ZONE_FQDN,
            ),
        ],
        ids=[
            "primary-nxdomain",
            "primary-nodata",
            "alias-nxdomain",
            "alias-nodata",
        ],
    )
    def test_mixed_case_negative_lookup_uses_case_insensitive_zone_match(
        self, live_server, qname, rdtype, expected_rcode, expected_soa_name
    ):
        host, port = live_server
        query = dns.message.make_query(qname, rdtype)
        response = s.udp_query(host, port, query)

        assert response.rcode() == expected_rcode
        assert response.id == query.id
        s.assert_section_counts(response, authority=1)
        assert response.authority[0].name.to_text().lower() == expected_soa_name.lower()
        s.assert_response_flags(response)

    def test_mixed_case_out_of_zone_name_remains_out_of_zone(self, live_server):
        host, port = live_server
        query = dns.message.make_query(s.MIXED_CASE_OUT_OF_ZONE_FQDN, dns.rdatatype.A)
        response = s.udp_query(host, port, query)

        assert response.rcode() == dns.rcode.REFUSED
        s.assert_section_counts(response)
        s.assert_response_flags(response, aa=False)
