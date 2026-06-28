#!/usr/bin/env python3

import dns.flags
import dns.message
import dns.name
import dns.rcode
import dns.rdatatype
import pytest

from . import support as s


class TestAuthoritativePositiveResponses:
    def test_a_query_returns_authoritative_noerror_answer(self, live_server):
        host, port = live_server
        query = dns.message.make_query(s.SUBDOMAIN_FQDN, dns.rdatatype.A)
        response = s.udp_query(host, port, query)

        assert response.rcode() == dns.rcode.NOERROR
        assert response.id == query.id
        s.assert_section_counts(response, answer=1)
        assert response.answer[0].rdtype == dns.rdatatype.A
        assert any(str(rdata) == s.SUBDOMAIN_IP for rdata in response.answer[0])
        s.assert_response_flags(response)

    def test_soa_query_returns_authoritative_apex_answer(self, live_server):
        host, port = live_server
        query = dns.message.make_query(s.ZONE_FQDN, dns.rdatatype.SOA)
        response = s.udp_query(host, port, query)

        assert response.rcode() == dns.rcode.NOERROR
        assert response.id == query.id
        s.assert_section_counts(response, answer=1)
        assert response.answer[0].rdtype == dns.rdatatype.SOA
        assert response.answer[0].name == dns.name.from_text(s.ZONE_FQDN)
        s.assert_response_flags(response)

    def test_ns_query_returns_authoritative_apex_answer(self, live_server):
        host, port = live_server
        query = dns.message.make_query(s.ZONE_FQDN, dns.rdatatype.NS)
        response = s.udp_query(host, port, query)

        assert response.rcode() == dns.rcode.NOERROR
        assert response.id == query.id
        s.assert_section_counts(response, answer=1)
        assert response.answer[0].rdtype == dns.rdatatype.NS
        assert {str(rdata.target) for rdata in response.answer[0]} == {s.NS}
        s.assert_response_flags(response)

    def test_alias_a_query_returns_authoritative_primary_zone_data(self, live_server):
        host, port = live_server
        query = dns.message.make_query(s.ALIAS_SUBDOMAIN_FQDN, dns.rdatatype.A)
        response = s.udp_query(host, port, query)

        assert response.rcode() == dns.rcode.NOERROR
        assert response.id == query.id
        s.assert_section_counts(response, answer=1)
        assert response.answer[0].name == dns.name.from_text(s.ALIAS_SUBDOMAIN_FQDN)
        assert response.answer[0].rdtype == dns.rdatatype.A
        assert any(str(rdata) == s.SUBDOMAIN_IP for rdata in response.answer[0])
        s.assert_response_flags(response)


class TestAuthoritativeScope:
    @pytest.mark.parametrize(
        "qname",
        [
            s.OUT_OF_ZONE_FQDN,
            s.MIXED_CASE_OUT_OF_ZONE_FQDN,
        ],
    )
    def test_out_of_zone_query_returns_refused_without_aa(self, live_server, qname):
        host, port = live_server
        query = dns.message.make_query(qname, dns.rdatatype.A)
        response = s.udp_query(host, port, query)

        assert response.rcode() == dns.rcode.REFUSED
        assert response.id == query.id
        s.assert_section_counts(response)
        assert not bool(response.flags & dns.flags.AA)
        s.assert_response_flags(response, aa=False)
