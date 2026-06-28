#!/usr/bin/env python3

import logging

import dns.exception
import dns.flags
import dns.message
import dns.name
import dns.opcode
import dns.rcode
import dns.rdataclass
import dns.rdatatype
import pytest

from unittest.mock import patch

from indisoluble.a_healthy_dns.dns_server_config_factory import DnsServerConfig
from indisoluble.a_healthy_dns.dns_server_udp_handler import _CLASSIC_UDP_PAYLOAD_SIZE
from indisoluble.a_healthy_dns.dns_server_zone_updater import DnsServerZoneUpdater
from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp
from indisoluble.a_healthy_dns.records.a_healthy_record import AHealthyRecord
from indisoluble.a_healthy_dns.records.zone_origins import ZoneOrigins

from . import support as s


class TestWireParseFailures:
    @patch("dns.message.from_wire")
    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_recoverable_parse_exception_returns_formerr_and_preserves_id(
        self,
        mock_update_response,
        mock_from_wire,
        dns_request,
        dns_client_address,
        zone_origins,
    ):
        zone = s.make_zone(zone_origins, s.FakeTransaction())
        server = s.make_server(zone, zone_origins)
        mock_from_wire.side_effect = dns.exception.DNSException("Test exception")

        mock_sock = s.handle_wire(dns_request[0], dns_client_address, server)

        mock_from_wire.assert_called_once_with(dns_request[0])
        response = s.sent_response(mock_sock, dns_client_address, s.REAL_FROM_WIRE)
        s.assert_response_header(
            response,
            query_id=int.from_bytes(dns_request[0][:2], "big"),
            rcode=dns.rcode.FORMERR,
            aa=False,
        )
        mock_update_response.assert_not_called()

    @pytest.mark.parametrize("wire_data", [b"", b"\x00\x01\x00\x00"])
    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_short_packet_drops_without_response(
        self,
        mock_update_response,
        wire_data,
        dns_client_address,
        zone_origins,
        caplog,
    ):
        zone = s.make_zone(zone_origins, s.FakeTransaction())
        server = s.make_server(zone, zone_origins)

        with caplog.at_level(logging.DEBUG):
            mock_sock = s.handle_wire(wire_data, dns_client_address, server)

        mock_sock.sendto.assert_not_called()
        mock_update_response.assert_not_called()
        s.assert_log_record(
            caplog,
            logging.INFO,
            "Ignoring malformed DNS packet",
            s.DNS_TRAFFIC_JUNK,
        )
        assert "packet is shorter than the 12-byte DNS header" in caplog.text
        assert "Stack trace for malformed DNS packet" in caplog.text

    @pytest.mark.parametrize(
        "wire_data,expected_problem",
        [
            (
                b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00",
                "packet does not match the DNS message wire format",
            ),
            (
                b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
                b"\xc0\x0c\x00\x01\x00\x01",
                "packet contains an invalid DNS compression pointer",
            ),
            (
                b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
                b"\x40\x00\x00\x01\x00\x01",
                "packet uses an unsupported DNS label encoding",
            ),
            (
                b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
                b"\x03www\x00\x00\x01\x00\x01junk",
                "packet has trailing bytes after a complete DNS message",
            ),
            (
                bytes(range(32)),
                "packet does not match the DNS message wire format",
            ),
        ],
    )
    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_malformed_wire_with_recoverable_header_returns_formerr(
        self,
        mock_update_response,
        wire_data,
        expected_problem,
        dns_client_address,
        zone_origins,
        caplog,
    ):
        zone = s.make_zone(zone_origins, s.FakeTransaction())
        server = s.make_server(zone, zone_origins)

        with caplog.at_level(logging.DEBUG):
            mock_sock = s.handle_wire(wire_data, dns_client_address, server)

        sent_wire = s.sent_wire(mock_sock, dns_client_address)
        assert len(sent_wire) == 12
        assert sent_wire[0] == wire_data[0]
        assert sent_wire[1] == wire_data[1]
        assert sent_wire[2] & 0x80
        assert (sent_wire[3] & 0x0F) == dns.rcode.FORMERR
        mock_update_response.assert_not_called()

        s.assert_log_record(
            caplog,
            logging.INFO,
            "Malformed DNS query; replying FORMERR",
            s.DNS_TRAFFIC_JUNK,
        )
        assert f"problem={expected_problem}" in caplog.text
        assert "Stack trace for malformed DNS query" in caplog.text

    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_malformed_wire_formerr_preserves_header_opcode_and_rd(
        self, mock_update_response, dns_client_address, zone_origins
    ):
        request_flags = dns.opcode.to_flags(dns.opcode.STATUS) | dns.flags.RD
        wire_data = (
            b"\x12\x34"
            + request_flags.to_bytes(2, "big")
            + b"\x00\x01\x00\x00\x00\x00\x00\x00"
        )
        zone = s.make_zone(zone_origins, s.FakeTransaction())
        server = s.make_server(zone, zone_origins)

        mock_sock = s.handle_wire(wire_data, dns_client_address, server)

        response = s.sent_response(mock_sock, dns_client_address, s.REAL_FROM_WIRE)
        s.assert_response_header(
            response,
            query_id=int.from_bytes(wire_data[:2], "big"),
            rcode=dns.rcode.FORMERR,
            aa=False,
            opcode=dns.opcode.STATUS,
            rd=True,
        )
        mock_update_response.assert_not_called()

    def test_malformed_udp_payload_with_header_returns_formerr_over_udp(
        self, live_server
    ):
        host, port = live_server
        response = s.udp_raw_query(host, port, s.MALFORMED_HEADER_ONLY_WIRE)

        assert response.rcode() == dns.rcode.FORMERR
        assert response.id == s.MALFORMED_HEADER_ONLY_ID
        s.assert_section_counts(response)
        s.assert_response_flags(response, aa=False)


class TestResponsePacketsOnQuerySocket:
    @pytest.mark.parametrize(
        "wire_data",
        [
            dns.message.make_response(
                dns.message.make_query("test.example.com.", dns.rdatatype.A)
            ).to_wire(),
            b"\x12\x34\x81\x00\x00\x01\x00\x00\x00\x00\x00\x00",
        ],
        ids=["well-formed-response", "malformed-response"],
    )
    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_dns_response_packet_logs_warning_and_drops(
        self,
        mock_update_response,
        wire_data,
        dns_client_address,
        zone_origins,
        caplog,
    ):
        zone = s.make_zone(zone_origins, s.FakeTransaction())
        server = s.make_server(zone, zone_origins)

        with caplog.at_level(logging.WARNING):
            mock_sock = s.handle_wire(wire_data, dns_client_address, server)

        mock_update_response.assert_not_called()
        mock_sock.sendto.assert_not_called()
        s.assert_log_record(
            caplog,
            logging.WARNING,
            "Ignoring DNS response packet received on query socket",
            s.DNS_TRAFFIC_SUSPICIOUS,
        )
        assert "problem=response flag is set" in caplog.text


class TestQuestionValidation:
    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_zero_question_query_returns_formerr_without_aa(
        self, mock_update_response, dns_client_address, zone_origins, caplog
    ):
        zone = s.make_zone(zone_origins, s.FakeTransaction())
        server = s.make_server(zone, zone_origins)
        query_data = dns.message.Message().to_wire()

        with caplog.at_level(logging.INFO):
            mock_sock = s.handle_wire(query_data, dns_client_address, server)

        response = s.sent_response(mock_sock, dns_client_address)
        s.assert_response_header(
            response,
            query_id=dns.message.from_wire(query_data).id,
            rcode=dns.rcode.FORMERR,
            aa=False,
        )
        s.assert_section_counts(response)
        mock_update_response.assert_not_called()
        s.assert_log_record(
            caplog,
            logging.INFO,
            "DNS query has invalid question count",
            s.DNS_TRAFFIC_JUNK,
        )

    @patch(
        "indisoluble.a_healthy_dns.dns_server_udp_handler.DnsServerUdpHandler._update_response"
    )
    def test_non_in_class_query_returns_refused_without_aa(
        self, mock_update_response, dns_client_address, zone_origins, caplog
    ):
        zone = s.make_zone(zone_origins, s.FakeTransaction())
        server = s.make_server(zone, zone_origins)
        query = dns.message.make_query(
            "test.example.com.", dns.rdatatype.A, rdclass=dns.rdataclass.CH
        )

        with caplog.at_level(logging.INFO):
            mock_sock = s.handle_wire(query.to_wire(), dns_client_address, server)

        response = s.sent_response(mock_sock, dns_client_address)
        s.assert_response_header(
            response,
            query_id=query.id,
            rcode=dns.rcode.REFUSED,
            aa=False,
        )
        s.assert_section_counts(response)
        mock_update_response.assert_not_called()
        s.assert_log_record(
            caplog,
            logging.INFO,
            "Refused DNS query with unsupported class",
            s.DNS_TRAFFIC_NOISE,
        )


class TestUdpSerialization:
    def test_oversized_udp_answer_sets_tc_and_respects_classic_udp_limit(
        self, dns_client_address
    ):
        zone_origins = ZoneOrigins("example.com", [])
        ip_addresses = [f"192.0.2.{octet}" for octet in range(1, 101)]
        a_record = AHealthyRecord(
            subdomain=dns.name.from_text("many", origin=zone_origins.primary),
            healthy_ips=[
                AHealthyIp(ip=ip, health_port=None, is_healthy=True)
                for ip in ip_addresses
            ],
        )
        config = DnsServerConfig(
            zone_origins=zone_origins,
            primary_name_server="ns1.example.net.",
            name_servers=frozenset(["ns1.example.net."]),
            a_records=frozenset([a_record]),
            ext_private_key=None,
        )
        updater = DnsServerZoneUpdater(
            min_interval=30, connection_timeout=2, config=config
        )
        updater.initialize_zone()

        server = s.make_server(updater.zone, zone_origins)
        query = dns.message.make_query("many.example.com.", dns.rdatatype.A)
        mock_sock = s.handle_wire(query.to_wire(), dns_client_address, server)

        sent_wire = s.sent_wire(mock_sock, dns_client_address)
        response = dns.message.from_wire(sent_wire)

        assert len(sent_wire) <= _CLASSIC_UDP_PAYLOAD_SIZE
        s.assert_response_header(
            response,
            query_id=query.id,
            rcode=dns.rcode.NOERROR,
            aa=True,
            tc=True,
        )
