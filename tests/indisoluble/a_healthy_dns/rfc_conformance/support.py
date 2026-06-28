#!/usr/bin/env python3

import socket

import dns.flags
import dns.message
import dns.name
import dns.opcode
import dns.rdataclass
import dns.rdatatype
import dns.rdataset
import dns.update

from unittest.mock import MagicMock

from indisoluble.a_healthy_dns.dns_server_udp_handler import (
    _DNS_TRAFFIC_JUNK,
    _DNS_TRAFFIC_NOISE,
    _DNS_TRAFFIC_SUSPICIOUS,
    _RFC8482_HINFO_CPU,
    _RFC8482_HINFO_OS,
    DnsServerUdpHandler,
)

REAL_FROM_WIRE = dns.message.from_wire

DNS_TRAFFIC_JUNK = _DNS_TRAFFIC_JUNK
DNS_TRAFFIC_NOISE = _DNS_TRAFFIC_NOISE
DNS_TRAFFIC_SUSPICIOUS = _DNS_TRAFFIC_SUSPICIOUS

ZONE = "example.integration.test"
ALIAS_ZONE = "alias.integration.test"
NS = "ns1.integration.test."
SUBDOMAIN = "www"
SUBDOMAIN_IP = "192.0.2.1"
ABSENT_SUBDOMAIN = "missing"
NESTED_SUBDOMAIN = "leaf.parent"
NESTED_SUBDOMAIN_IP = "192.0.2.2"
EMPTY_NON_TERMINAL = "parent"

ZONE_FQDN = f"{ZONE}."
ALIAS_ZONE_FQDN = f"{ALIAS_ZONE}."
SUBDOMAIN_FQDN = f"{SUBDOMAIN}.{ZONE}."
ALIAS_SUBDOMAIN_FQDN = f"{SUBDOMAIN}.{ALIAS_ZONE}."
ABSENT_FQDN = f"{ABSENT_SUBDOMAIN}.{ZONE}."
ALIAS_ABSENT_FQDN = f"{ABSENT_SUBDOMAIN}.{ALIAS_ZONE}."
EMPTY_NON_TERMINAL_FQDN = f"{EMPTY_NON_TERMINAL}.{ZONE}."
ALIAS_EMPTY_NON_TERMINAL_FQDN = f"{EMPTY_NON_TERMINAL}.{ALIAS_ZONE}."
OUT_OF_ZONE_FQDN = "www.unrelated.test."

UNKNOWN_NON_META_RDTYPE = dns.rdatatype.from_text("TYPE65280")

MIXED_CASE_SUBDOMAIN_FQDN = "WwW.ExAmPlE.InTeGrAtIoN.TeSt."
MIXED_CASE_ALIAS_SUBDOMAIN_FQDN = "WwW.AlIaS.InTeGrAtIoN.TeSt."
MIXED_CASE_ABSENT_FQDN = "MiSsInG.ExAmPlE.InTeGrAtIoN.TeSt."
MIXED_CASE_ALIAS_ABSENT_FQDN = "MiSsInG.AlIaS.InTeGrAtIoN.TeSt."
MIXED_CASE_OUT_OF_ZONE_FQDN = "WwW.UnReLaTeD.TeSt."
RESERVED_HEADER_FLAG = 0x0040

MALFORMED_HEADER_ONLY_WIRE = b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
MALFORMED_HEADER_ONLY_ID = 0x1234

SERVER_READY_WAIT = 0.05

TEST_QUERY_ID = 13551
TEST_SOURCE_HOST = "127.0.0.1"
TEST_SOURCE_PORT = 12345
SOA_MNAME = "ns1.example.com."
SOA_RNAME = "hostmaster.example.com."
SOA_SERIAL = 1
SOA_REFRESH = 7200
SOA_RETRY = 3600
SOA_EXPIRE = 1209600


class FakeNode:
    def __init__(self, *rdatasets):
        self._rdatasets = {
            (rdataset.rdclass, rdataset.rdtype): rdataset for rdataset in rdatasets
        }

    def get_rdataset(self, rdclass, rdtype):
        return self._rdatasets.get((rdclass, rdtype))


class FakeReaderContext:
    def __init__(self, transaction):
        self._transaction = transaction

    # Implements context manager protocol.
    def __enter__(self):
        return self._transaction

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class FakeTransaction:
    def __init__(self, *, nodes=None, soa_rdataset=None, names=None):
        self._nodes = nodes or {}
        self._soa_rdataset = soa_rdataset
        self._names = list(self._nodes) if names is None else list(names)

    def get_node(self, name):
        return self._nodes.get(name)

    def get(self, name, rdtype):
        if name == dns.name.empty and rdtype == dns.rdatatype.SOA:
            return self._soa_rdataset

        return None

    def iterate_names(self):
        return iter(self._names)


class FakeZone:
    rdclass = dns.rdataclass.IN

    def __init__(self, origin, transaction):
        self.origin = origin
        self.reader_calls = 0
        self._transaction = transaction

    def reader(self):
        self.reader_calls += 1
        return FakeReaderContext(self._transaction)


def udp_exchange_wire(
    host: str,
    port: int,
    wire: bytes,
    timeout: float = 2.0,
) -> bytes:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        sock.sendto(wire, (host, port))
        data, _ = sock.recvfrom(4096)
        return data


def udp_query(
    host: str,
    port: int,
    query: dns.message.Message,
    timeout: float = 2.0,
) -> dns.message.Message:
    return dns.message.from_wire(
        udp_exchange_wire(host, port, query.to_wire(), timeout)
    )


def udp_raw_query(
    host: str,
    port: int,
    wire: bytes,
    timeout: float = 2.0,
) -> dns.message.Message:
    return dns.message.from_wire(udp_exchange_wire(host, port, wire, timeout))


def udp_query_wire(
    host: str,
    port: int,
    query: dns.message.Message,
    timeout: float = 2.0,
) -> bytes:
    return udp_exchange_wire(host, port, query.to_wire(), timeout)


def make_multi_question_wire(*question_names):
    queries = [
        dns.message.make_query(question_name, dns.rdatatype.A)
        for question_name in question_names
    ]

    wire = bytearray(queries[0].to_wire())
    wire[4:6] = len(queries).to_bytes(2, byteorder="big")

    for query in queries[1:]:
        wire.extend(query.to_wire()[12:])

    return bytes(wire)


def make_status_query() -> dns.message.Message:
    return make_opcode_query(dns.opcode.STATUS)


def make_opcode_query(opcode: int, qname: str = SUBDOMAIN_FQDN) -> dns.message.Message:
    query = dns.message.make_query(qname, dns.rdatatype.A)
    query.set_opcode(opcode)
    return query


def make_query_with_opcode(opcode):
    return make_opcode_query(opcode, "test.example.com.")


def make_update_query():
    query = dns.update.Update("example.com.")
    query.add("www", 300, "A", "192.0.2.1")
    return query


def make_a_rdataset(*ip_addresses, ttl=300):
    return dns.rdataset.from_text(
        dns.rdataclass.IN, dns.rdatatype.A, ttl, *ip_addresses
    )


def make_soa_rdataset(*, ttl=300, minimum=60):
    return dns.rdataset.from_text(
        dns.rdataclass.IN,
        dns.rdatatype.SOA,
        ttl,
        (
            f"{SOA_MNAME} {SOA_RNAME} {SOA_SERIAL} {SOA_REFRESH} "
            f"{SOA_RETRY} {SOA_EXPIRE} {minimum}"
        ),
    )


def soa_authority_ttl(soa_rdataset):
    return min(soa_rdataset.ttl, next(iter(soa_rdataset)).minimum)


def make_hinfo_rdataset(ttl):
    return dns.rdataset.from_text(
        dns.rdataclass.IN,
        dns.rdatatype.HINFO,
        ttl,
        f'"{_RFC8482_HINFO_CPU}" "{_RFC8482_HINFO_OS}"',
    )


def make_zone(zone_origins, transaction):
    return FakeZone(zone_origins.primary, transaction)


def make_server(zone, zone_origins):
    server = MagicMock()
    server.zone = zone
    server.zone_origins = zone_origins
    return server


def make_handler(zone, zone_origins):
    handler = object.__new__(DnsServerUdpHandler)
    handler.server = make_server(zone, zone_origins)
    handler.client_address = (TEST_SOURCE_HOST, TEST_SOURCE_PORT)
    return handler


def make_request(wire_data):
    mock_sock = MagicMock()
    return (wire_data, mock_sock), mock_sock


def handle_wire(wire_data, client_address, server):
    request, mock_sock = make_request(wire_data)
    DnsServerUdpHandler(request, client_address, server)
    return mock_sock


def sent_wire(mock_sock, client_address):
    mock_sock.sendto.assert_called_once()
    sent_data, destination = mock_sock.sendto.call_args[0]
    assert destination == client_address
    return sent_data


def sent_response(mock_sock, client_address, from_wire=dns.message.from_wire):
    return from_wire(sent_wire(mock_sock, client_address))


def update_test_response(response, query_name, query_type, zone, zone_origins):
    question = dns.message.make_query(query_name, query_type).question[0]
    make_handler(zone, zone_origins)._update_response(response, question, TEST_QUERY_ID)


def assert_log_record(caplog, level, message_fragment, traffic_marker=None):
    assert any(
        record.levelno == level
        and message_fragment in record.getMessage()
        and (traffic_marker is None or traffic_marker in record.getMessage())
        for record in caplog.records
    )


def assert_log_context(caplog, *, query_id=TEST_QUERY_ID):
    assert f"source={TEST_SOURCE_HOST}:{TEST_SOURCE_PORT}" in caplog.text
    assert f"id={query_id}" in caplog.text


def assert_section_counts(response, *, additional=0, authority=0, answer=0):
    assert len(response.additional) == additional
    assert len(response.authority) == authority
    assert len(response.answer) == answer


def assert_response_flags(resp: dns.message.Message, *, aa: bool = True):
    assert bool(resp.flags & dns.flags.AA) == aa
    assert bool(resp.flags & dns.flags.QR)
    assert not bool(resp.flags & dns.flags.RA)
    assert not bool(resp.flags & dns.flags.TC)


def assert_response_header(
    response,
    *,
    query_id,
    rcode,
    aa,
    tc=False,
    opcode=None,
    rd=None,
):
    assert response.id == query_id
    assert response.rcode() == rcode
    assert bool(response.flags & dns.flags.QR)
    assert bool(response.flags & dns.flags.AA) == aa
    assert bool(response.flags & dns.flags.TC) == tc
    assert not bool(response.flags & dns.flags.RA)

    if opcode is not None:
        assert response.opcode() == opcode

    if rd is not None:
        assert bool(response.flags & dns.flags.RD) == rd


def assert_answer_rrset(response, *, name, rdtype, rdataset):
    assert_section_counts(response, answer=1)
    assert response.answer[0].name == name
    assert response.answer[0].rdclass == rdataset.rdclass
    assert response.answer[0].rdtype == rdtype
    assert response.answer[0].ttl == rdataset.ttl
    assert set(response.answer[0]) == set(rdataset)


def assert_soa_authority(response, *, name, expected_ttl):
    assert len(response.authority) == 1
    assert response.authority[0].name == name
    assert response.authority[0].rdclass == dns.rdataclass.IN
    assert response.authority[0].rdtype == dns.rdatatype.SOA
    assert response.authority[0].ttl == expected_ttl


def assert_no_authority_or_additional(response):
    assert len(response.additional) == 0
    assert len(response.authority) == 0


def scan_wire_for_compressed_names(wire: bytes) -> bool:
    flags = int.from_bytes(wire[2:4], "big")
    qdcount = int.from_bytes(wire[4:6], "big")
    ancount = int.from_bytes(wire[6:8], "big")
    nscount = int.from_bytes(wire[8:10], "big")
    arcount = int.from_bytes(wire[10:12], "big")

    if len(wire) < 12 or not (flags & dns.flags.QR):
        return False

    def parse_name(offset: int) -> tuple[int, bool]:
        used_pointer = False
        while True:
            length = wire[offset]
            if length == 0:
                return offset + 1, used_pointer
            if length & 0xC0 == 0xC0:
                return offset + 2, True
            offset += 1 + length

    used_pointer_anywhere = False
    offset = 12

    for _ in range(qdcount):
        offset, used_pointer = parse_name(offset)
        used_pointer_anywhere |= used_pointer
        offset += 4

    def parse_rr(offset: int) -> int:
        nonlocal used_pointer_anywhere
        offset, used_pointer = parse_name(offset)
        used_pointer_anywhere |= used_pointer

        rrtype = int.from_bytes(wire[offset : offset + 2], "big")
        offset += 2
        offset += 2
        offset += 4
        rdlength = int.from_bytes(wire[offset : offset + 2], "big")
        offset += 2

        rdata_start = offset
        if rrtype == dns.rdatatype.SOA:
            offset, used_pointer = parse_name(offset)
            used_pointer_anywhere |= used_pointer
            offset, used_pointer = parse_name(offset)
            used_pointer_anywhere |= used_pointer
            offset += 20
        else:
            offset += rdlength

        if offset < rdata_start + rdlength:
            offset = rdata_start + rdlength

        return offset

    for _ in range(ancount + nscount + arcount):
        offset = parse_rr(offset)

    return used_pointer_anywhere
