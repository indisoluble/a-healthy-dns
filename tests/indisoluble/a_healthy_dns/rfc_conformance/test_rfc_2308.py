#!/usr/bin/env python3

import dns.message
import dns.name
import dns.rcode
import dns.rdatatype
import pytest

from . import support as s


class TestNegativeResponses:
    @pytest.mark.parametrize(
        "qname,rdtype,expected_rcode,expected_soa_name",
        [
            (s.ABSENT_FQDN, dns.rdatatype.A, dns.rcode.NXDOMAIN, s.ZONE_FQDN),
            (s.SUBDOMAIN_FQDN, dns.rdatatype.AAAA, dns.rcode.NOERROR, s.ZONE_FQDN),
            (
                s.ALIAS_ABSENT_FQDN,
                dns.rdatatype.A,
                dns.rcode.NXDOMAIN,
                s.ALIAS_ZONE_FQDN,
            ),
            (
                s.ALIAS_SUBDOMAIN_FQDN,
                dns.rdatatype.AAAA,
                dns.rcode.NOERROR,
                s.ALIAS_ZONE_FQDN,
            ),
        ],
        ids=[
            "nxdomain-primary",
            "nodata-primary",
            "nxdomain-alias",
            "nodata-alias",
        ],
    )
    def test_nxdomain_and_nodata_responses_include_apex_soa_authority(
        self, live_server, qname, rdtype, expected_rcode, expected_soa_name
    ):
        host, port = live_server
        query = dns.message.make_query(qname, rdtype)
        response = s.udp_query(host, port, query)

        assert response.rcode() == expected_rcode
        assert response.id == query.id
        s.assert_section_counts(response, authority=1)
        assert response.authority[0].rdtype == dns.rdatatype.SOA
        assert response.authority[0].name == dns.name.from_text(expected_soa_name)
        soa_rdata = next(iter(response.authority[0]))
        assert response.authority[0].ttl == soa_rdata.minimum
        s.assert_response_flags(response)

    def test_negative_response_soa_ttl_uses_lower_of_soa_ttl_and_minimum(
        self, dns_response, zone_origins
    ):
        query_name = dns.name.from_text("nonexistent", origin=zone_origins.primary)
        soa_rdataset = s.make_soa_rdataset(ttl=30, minimum=60)
        transaction = s.FakeTransaction(soa_rdataset=soa_rdataset)
        zone = s.make_zone(zone_origins, transaction)

        s.update_test_response(
            dns_response, query_name, dns.rdatatype.A, zone, zone_origins
        )

        assert dns_response.rcode() == dns.rcode.NXDOMAIN
        s.assert_soa_authority(
            dns_response,
            name=zone_origins.primary,
            expected_ttl=30,
        )
