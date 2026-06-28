#!/usr/bin/env python3

import dns.message
import dns.name
import dns.rcode
import dns.rdatatype
import pytest

from . import support as s


class TestNxdomainCutSemantics:
    def test_absent_name_without_subtree_returns_nxdomain(self, live_server):
        host, port = live_server
        query = dns.message.make_query(s.ABSENT_FQDN, dns.rdatatype.A)
        response = s.udp_query(host, port, query)

        assert response.rcode() == dns.rcode.NXDOMAIN
        s.assert_section_counts(response, authority=1)
        assert response.authority[0].name == dns.name.from_text(s.ZONE_FQDN)
        s.assert_response_flags(response)

    @pytest.mark.parametrize(
        "qname,expected_soa_name",
        [
            (s.EMPTY_NON_TERMINAL_FQDN, s.ZONE_FQDN),
            (s.ALIAS_EMPTY_NON_TERMINAL_FQDN, s.ALIAS_ZONE_FQDN),
        ],
        ids=["primary-empty-non-terminal", "alias-empty-non-terminal"],
    )
    def test_empty_non_terminal_returns_nodata_not_nxdomain(
        self, live_server, qname, expected_soa_name
    ):
        host, port = live_server
        query = dns.message.make_query(qname, dns.rdatatype.A)
        response = s.udp_query(host, port, query)

        assert response.rcode() == dns.rcode.NOERROR
        s.assert_section_counts(response, authority=1)
        assert response.authority[0].name == dns.name.from_text(expected_soa_name)
        s.assert_response_flags(response)
