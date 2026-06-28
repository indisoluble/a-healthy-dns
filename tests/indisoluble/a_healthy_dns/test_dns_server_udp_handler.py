#!/usr/bin/env python3

import logging

import dns.exception
import dns.flags
import dns.message
import dns.rcode
import dns.rdatatype

from unittest.mock import patch

from indisoluble.a_healthy_dns.records.zone_origins import ZoneOrigins

from tests.indisoluble.a_healthy_dns.rfc_conformance import support as s


def _make_handler_inputs():
    zone_origins = ZoneOrigins("example.com", [])
    zone = s.make_zone(zone_origins, s.FakeTransaction())
    server = s.make_server(zone, zone_origins)
    client_address = (s.TEST_SOURCE_HOST, s.TEST_SOURCE_PORT)
    query = dns.message.make_query("test.example.com.", dns.rdatatype.A)
    return query, client_address, server


class TestHandlerDispatch:
    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_valid_query_builds_response_delegates_update_and_sends_once(
        self, mock_update_response
    ):
        query, client_address, server = _make_handler_inputs()
        mock_update_response.side_effect = lambda response, *args: setattr(
            response, "flags", response.flags | dns.flags.AA
        )

        mock_sock = s.handle_wire(query.to_wire(), client_address, server)

        question = query.question[0]
        call_args = mock_update_response.call_args[0]
        mock_update_response.assert_called_once()
        assert call_args[1] == question
        assert call_args[2] == query.id

        response = s.sent_response(mock_sock, client_address)
        s.assert_response_header(
            response,
            query_id=query.id,
            rcode=dns.rcode.NOERROR,
            aa=True,
        )


class TestResponseConstructionFailure:
    @patch("dns.message.make_response")
    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_make_response_failure_logs_info_and_drops(
        self, mock_update_response, mock_make_response, caplog
    ):
        query, client_address, server = _make_handler_inputs()
        mock_make_response.side_effect = dns.exception.FormError(
            "cannot build response"
        )

        with caplog.at_level(logging.DEBUG):
            mock_sock = s.handle_wire(query.to_wire(), client_address, server)

        mock_update_response.assert_not_called()
        mock_sock.sendto.assert_not_called()
        s.assert_log_record(
            caplog,
            logging.INFO,
            "Unable to build DNS response; dropping packet",
            s.DNS_TRAFFIC_JUNK,
        )
        assert f"source={s.TEST_SOURCE_HOST}:{s.TEST_SOURCE_PORT}" in caplog.text
        assert "problem=cannot build response" in caplog.text
        assert "Stack trace for DNS response construction failure" in caplog.text
