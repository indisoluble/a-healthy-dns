#!/usr/bin/env python3

import logging

import dns.opcode
import dns.rcode

from unittest.mock import patch

from . import support as s


class TestIqueryObsolescence:
    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_iquery_returns_notimp_without_aa(
        self, mock_update_response, dns_client_address, zone_origins, caplog
    ):
        zone = s.make_zone(zone_origins, s.FakeTransaction())
        server = s.make_server(zone, zone_origins)
        query = s.make_query_with_opcode(dns.opcode.IQUERY)

        with caplog.at_level(logging.WARNING):
            mock_sock = s.handle_wire(query.to_wire(), dns_client_address, server)

        response = s.sent_response(mock_sock, dns_client_address)
        s.assert_response_header(
            response,
            query_id=query.id,
            rcode=dns.rcode.NOTIMP,
            aa=False,
            opcode=dns.opcode.IQUERY,
        )
        s.assert_section_counts(response)
        mock_update_response.assert_not_called()

        s.assert_log_record(
            caplog,
            logging.WARNING,
            "DNS query uses unsupported opcode",
            s.DNS_TRAFFIC_SUSPICIOUS,
        )
