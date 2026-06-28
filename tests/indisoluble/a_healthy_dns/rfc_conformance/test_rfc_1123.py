#!/usr/bin/env python3

import dns.flags
import dns.message
import dns.opcode
import dns.rcode
import dns.rdatatype
import pytest

from . import support as s


class TestUdpService:
    def test_dns_server_answers_basic_query_over_udp(self, live_server):
        host, port = live_server
        query = dns.message.make_query(s.SUBDOMAIN_FQDN, dns.rdatatype.A)
        response = s.udp_query(host, port, query)

        assert response.rcode() == dns.rcode.NOERROR
        assert response.id == query.id
        s.assert_response_flags(response)


class TestResponseWireEncoding:
    def test_response_wire_uses_standard_name_compression(self, live_server):
        host, port = live_server
        query = dns.message.make_query(s.ZONE_FQDN, dns.rdatatype.SOA)
        wire = s.udp_query_wire(host, port, query)
        response = dns.message.from_wire(wire)

        assert response.rcode() == dns.rcode.NOERROR
        assert response.id == query.id
        assert s.scan_wire_for_compressed_names(wire)

    @pytest.mark.parametrize(
        "query_factory",
        [
            lambda: dns.message.make_query(s.ZONE_FQDN, dns.rdatatype.SOA),
            s.make_status_query,
        ],
        ids=["noerror-soa", "notimp-status"],
    )
    def test_unused_response_header_bits_remain_clear(self, live_server, query_factory):
        host, port = live_server
        query = query_factory()
        query.flags |= dns.flags.AD | dns.flags.CD | s.RESERVED_HEADER_FLAG
        wire = s.udp_query_wire(host, port, query)

        flags = int.from_bytes(wire[2:4], "big")
        assert flags & dns.flags.QR
        assert (flags & dns.flags.RD) == (query.flags & dns.flags.RD)
        assert not (flags & dns.flags.RA)
        assert not (flags & dns.flags.AD)
        assert not (flags & dns.flags.CD)
        assert not (flags & s.RESERVED_HEADER_FLAG)
        if query.opcode() == dns.opcode.STATUS:
            assert dns.message.from_wire(wire).rcode() == dns.rcode.NOTIMP
