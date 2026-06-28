#!/usr/bin/env python3

import dns.message
import dns.name
import dns.rcode
import dns.rdatatype
import pytest

from . import support as s


class TestUnknownNonMetaRrTypes:
    @pytest.mark.parametrize(
        "qname,expected_rcode,expected_soa_name",
        [
            (s.SUBDOMAIN_FQDN, dns.rcode.NOERROR, s.ZONE_FQDN),
            (s.ABSENT_FQDN, dns.rcode.NXDOMAIN, s.ZONE_FQDN),
            (s.ALIAS_SUBDOMAIN_FQDN, dns.rcode.NOERROR, s.ALIAS_ZONE_FQDN),
            (s.ALIAS_ABSENT_FQDN, dns.rcode.NXDOMAIN, s.ALIAS_ZONE_FQDN),
        ],
        ids=[
            "existing-owner",
            "absent-owner",
            "alias-existing-owner",
            "alias-absent-owner",
        ],
    )
    def test_unknown_numeric_non_meta_type_gets_normal_dns_response(
        self, live_server, qname, expected_rcode, expected_soa_name
    ):
        host, port = live_server
        query = dns.message.make_query(qname, s.UNKNOWN_NON_META_RDTYPE)
        response = s.udp_query(host, port, query)

        assert response.rcode() == expected_rcode
        assert response.id == query.id
        s.assert_section_counts(response, authority=1)
        assert response.answer == []
        assert response.authority[0].rdtype == dns.rdatatype.SOA
        assert response.authority[0].name == dns.name.from_text(expected_soa_name)
        s.assert_response_flags(response)
