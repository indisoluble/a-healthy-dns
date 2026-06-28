#!/usr/bin/env python3

import logging

import dns.flags
import dns.message
import dns.opcode
import dns.rcode
import dns.rdatatype
import pytest

from unittest.mock import patch

from . import support as s


class TestBasicDnsRobustness:
    def test_soa_query_for_served_zone_receives_soa_answer(self, live_server):
        host, port = live_server
        query = dns.message.make_query(s.ZONE_FQDN, dns.rdatatype.SOA)
        response = s.udp_query(host, port, query)

        assert response.rcode() == dns.rcode.NOERROR
        s.assert_section_counts(response, answer=1)
        assert response.answer[0].rdtype == dns.rdatatype.SOA
        s.assert_response_flags(response)

    def test_unsupported_known_rr_type_at_existing_owner_receives_nodata(
        self, live_server
    ):
        host, port = live_server
        query = dns.message.make_query(s.SUBDOMAIN_FQDN, dns.rdatatype.AAAA)
        response = s.udp_query(host, port, query)

        assert response.rcode() == dns.rcode.NOERROR
        s.assert_section_counts(response, authority=1)
        assert response.answer == []
        assert response.authority[0].rdtype == dns.rdatatype.SOA
        s.assert_response_flags(response)

    @pytest.mark.parametrize(
        "query_factory",
        [
            lambda: s.make_opcode_query(dns.opcode.STATUS),
            lambda: s.make_opcode_query(dns.opcode.NOTIFY),
            lambda: s.make_opcode_query(15),
            s.make_update_query,
        ],
        ids=["status", "notify", "unassigned-opcode", "update"],
    )
    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_unknown_or_unimplemented_opcodes_return_notimp(
        self,
        mock_update_response,
        query_factory,
        dns_client_address,
        zone_origins,
        caplog,
    ):
        zone = s.make_zone(zone_origins, s.FakeTransaction())
        server = s.make_server(zone, zone_origins)
        query = query_factory()

        with caplog.at_level(logging.WARNING):
            mock_sock = s.handle_wire(query.to_wire(), dns_client_address, server)

        response = s.sent_response(mock_sock, dns_client_address)
        s.assert_response_header(
            response,
            query_id=query.id,
            rcode=dns.rcode.NOTIMP,
            aa=False,
            opcode=query.opcode(),
        )
        s.assert_section_counts(response)
        mock_update_response.assert_not_called()
        s.assert_log_record(
            caplog,
            logging.WARNING,
            "DNS query uses unsupported opcode",
            s.DNS_TRAFFIC_SUSPICIOUS,
        )

    def test_request_flags_receive_response_without_copying_unsupported_bits(
        self, live_server
    ):
        host, port = live_server
        query = dns.message.make_query(s.ZONE_FQDN, dns.rdatatype.SOA)
        query.flags |= dns.flags.AD | dns.flags.CD | s.RESERVED_HEADER_FLAG
        wire = s.udp_query_wire(host, port, query)

        flags = int.from_bytes(wire[2:4], "big")
        assert flags & dns.flags.QR
        assert (flags & dns.flags.RD) == (query.flags & dns.flags.RD)
        assert not (flags & dns.flags.RA)
        assert not (flags & dns.flags.AD)
        assert not (flags & dns.flags.CD)
        assert not (flags & s.RESERVED_HEADER_FLAG)
