#!/usr/bin/env python3

import dns.flags
import dns.message
import dns.name
import dns.rcode
import dns.rdatatype

from unittest.mock import patch

from . import support as s


class TestUdpReplyRouting:
    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_response_is_sent_to_query_source_address_and_port(
        self, mock_update_response, dns_request, dns_client_address, zone_origins
    ):
        zone = s.make_zone(zone_origins, s.FakeTransaction())
        server = s.make_server(zone, zone_origins)
        mock_update_response.side_effect = lambda response, *args: setattr(
            response, "flags", response.flags | dns.flags.AA
        )

        mock_sock = s.handle_wire(dns_request[0], dns_client_address, server)

        sent_wire = s.sent_wire(mock_sock, dns_client_address)
        response = dns.message.from_wire(sent_wire)
        s.assert_response_header(
            response,
            query_id=dns.message.from_wire(dns_request[0]).id,
            rcode=dns.rcode.NOERROR,
            aa=True,
        )


class TestRrsetAndAuthoritySemantics:
    def test_complete_rrset_response_preserves_all_rdata_values(
        self, dns_response, zone_origins
    ):
        query_name = dns.name.from_text("many", origin=zone_origins.primary)
        rdataset = s.make_a_rdataset("192.0.2.1", "192.0.2.2", "192.0.2.3")
        transaction = s.FakeTransaction(
            nodes={dns.name.from_text("many", origin=None): s.FakeNode(rdataset)}
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

    def test_soa_mname_is_configured_primary_name_server(self, live_server):
        host, port = live_server
        query = dns.message.make_query(s.ZONE_FQDN, dns.rdatatype.SOA)
        response = s.udp_query(host, port, query)

        assert response.rcode() == dns.rcode.NOERROR
        soa_rdata = next(iter(response.answer[0]))
        assert soa_rdata.mname == dns.name.from_text(s.NS)

    def test_authoritative_negative_response_places_soa_in_authority_section(
        self, dns_response, zone_origins, soa_rdataset
    ):
        query_name = dns.name.from_text("nonexistent", origin=zone_origins.primary)
        transaction = s.FakeTransaction(soa_rdataset=soa_rdataset)
        zone = s.make_zone(zone_origins, transaction)

        s.update_test_response(
            dns_response, query_name, dns.rdatatype.A, zone, zone_origins
        )

        assert dns_response.rcode() == dns.rcode.NXDOMAIN
        assert bool(dns_response.flags & dns.flags.AA)
        assert len(dns_response.answer) == 0
        assert len(dns_response.additional) == 0
        s.assert_soa_authority(
            dns_response,
            name=zone_origins.primary,
            expected_ttl=next(iter(soa_rdataset)).minimum,
        )

    def test_out_of_zone_response_is_not_authoritative(
        self, dns_response, zone_origins
    ):
        query_name = dns.name.from_text("test", origin=dns.name.from_text("other.com"))
        transaction = s.FakeTransaction()
        zone = s.make_zone(zone_origins, transaction)

        s.update_test_response(
            dns_response, query_name, dns.rdatatype.A, zone, zone_origins
        )

        assert dns_response.rcode() == dns.rcode.REFUSED
        assert not bool(dns_response.flags & dns.flags.AA)
        assert zone.reader_calls == 0
        s.assert_section_counts(dns_response)
