#!/usr/bin/env python3

import socket
import socketserver
import threading
import time

import dns.flags
import dns.message
import dns.name
import dns.opcode
import dns.rcode
import dns.rdataclass
import dns.rdatatype
import pytest

from indisoluble.a_healthy_dns.dns_server_config_factory import DnsServerConfig
from indisoluble.a_healthy_dns.dns_server_udp_handler import DnsServerUdpHandler
from indisoluble.a_healthy_dns.dns_server_zone_updater import DnsServerZoneUpdater
from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp
from indisoluble.a_healthy_dns.records.a_healthy_record import AHealthyRecord
from indisoluble.a_healthy_dns.records.zone_origins import ZoneOrigins


# ---------------------------------------------------------------------------
# Zone constants used throughout all test classes
# ---------------------------------------------------------------------------

_ZONE = "example.integration.test"
_ALIAS_ZONE = "alias.integration.test"
_NS = "ns1.integration.test."
_SUBDOMAIN = "www"
_SUBDOMAIN_IP = "192.0.2.1"  # RFC 5737 TEST-NET-1
_ABSENT_SUBDOMAIN = "missing"

_ZONE_FQDN = f"{_ZONE}."
_ALIAS_ZONE_FQDN = f"{_ALIAS_ZONE}."
_SUBDOMAIN_FQDN = f"{_SUBDOMAIN}.{_ZONE}."
_ALIAS_SUBDOMAIN_FQDN = f"{_SUBDOMAIN}.{_ALIAS_ZONE}."
_ABSENT_FQDN = f"{_ABSENT_SUBDOMAIN}.{_ZONE}."
_ALIAS_ABSENT_FQDN = f"{_ABSENT_SUBDOMAIN}.{_ALIAS_ZONE}."
_OUT_OF_ZONE_FQDN = "www.unrelated.test."

# RFC 3597: use a private-use RR type code to ensure dnspython parses it as an
# unknown numeric data type and the server treats it as a non-meta lookup type.
_UNKNOWN_NON_META_RDTYPE = dns.rdatatype.from_text("TYPE65280")

_MIXED_CASE_SUBDOMAIN_FQDN = "WwW.ExAmPlE.InTeGrAtIoN.TeSt."
_MIXED_CASE_ALIAS_SUBDOMAIN_FQDN = "WwW.AlIaS.InTeGrAtIoN.TeSt."
_MIXED_CASE_ABSENT_FQDN = "MiSsInG.ExAmPlE.InTeGrAtIoN.TeSt."
_MIXED_CASE_ALIAS_ABSENT_FQDN = "MiSsInG.AlIaS.InTeGrAtIoN.TeSt."
_MIXED_CASE_OUT_OF_ZONE_FQDN = "WwW.UnReLaTeD.TeSt."

# A wire payload that is ≥ 12 bytes (DNS header is readable) but not a valid
# DNS message.  The handler must recover the transaction ID and return FORMERR
# (RFC 1035 §4.1.1).  Exactly 12 bytes: valid DNS header with QDCOUNT=1 but
# the question section is absent.
_MALFORMED_HEADER_ONLY_WIRE = b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
_MALFORMED_HEADER_ONLY_ID = 0x1234

# Pause after server.serve_forever() starts before sending queries.
# 50 ms is well above any observable startup latency on CI runners.
_SERVER_READY_WAIT = 0.05


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------


def _udp_query(
    host: str,
    port: int,
    query: dns.message.Message,
    timeout: float = 2.0,
) -> dns.message.Message:
    """Send *query* over UDP and return the parsed response."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(query.to_wire(), (host, port))
        data, _ = sock.recvfrom(4096)
        return dns.message.from_wire(data)
    finally:
        sock.close()


def _udp_raw_query(
    host: str,
    port: int,
    wire: bytes,
    timeout: float = 2.0,
) -> dns.message.Message:
    """Send raw *wire* bytes over UDP and return the parsed response."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(wire, (host, port))
        data, _ = sock.recvfrom(4096)
        return dns.message.from_wire(data)
    finally:
        sock.close()


def _udp_query_wire(
    host: str,
    port: int,
    query: dns.message.Message,
    timeout: float = 2.0,
) -> bytes:
    """Send *query* over UDP and return raw response wire bytes."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(query.to_wire(), (host, port))
        data, _ = sock.recvfrom(4096)
        return data
    finally:
        sock.close()


def _make_two_question_wire(name1: str, name2: str) -> bytes:
    """Build a valid DNS wire message with QDCOUNT=2.

    Constructs the first query normally, then patches QDCOUNT to 2 and
    appends the question section from a second query.  dnspython does not
    natively produce multi-question messages; this reproduces the exact
    wire format used by the handler unit tests.
    """
    q1 = dns.message.make_query(name1, dns.rdatatype.A)
    q2 = dns.message.make_query(name2, dns.rdatatype.A)
    wire = bytearray(q1.to_wire())
    wire[4:6] = (2).to_bytes(2, byteorder="big")
    wire.extend(q2.to_wire()[12:])
    return bytes(wire)


def _make_status_query() -> dns.message.Message:
    query = dns.message.make_query(_SUBDOMAIN_FQDN, dns.rdatatype.A)
    query.set_opcode(dns.opcode.STATUS)
    return query


def _scan_wire_for_compressed_names(wire: bytes) -> bool:
    """Return True when *wire* uses DNS name compression pointers.

    This is a minimal wire parser for RFC 1035 name encoding, sufficient for
    asserting that at least one parsed name uses the compression pointer form.
    """
    flags = int.from_bytes(wire[2:4], "big")
    qdcount = int.from_bytes(wire[4:6], "big")
    ancount = int.from_bytes(wire[6:8], "big")
    nscount = int.from_bytes(wire[8:10], "big")
    arcount = int.from_bytes(wire[10:12], "big")

    # If this isn't a DNS message, bail out quickly.
    if len(wire) < 12 or not (flags & dns.flags.QR):
        return False

    def parse_name(offset: int) -> tuple[int, bool]:
        used_pointer = False
        while True:
            length = wire[offset]
            if length == 0:
                return offset + 1, used_pointer
            if length & 0xC0 == 0xC0:
                # Compression pointer, ends the current name.
                return offset + 2, True
            offset += 1 + length

    used_pointer_anywhere = False
    offset = 12

    for _ in range(qdcount):
        offset, used_pointer = parse_name(offset)
        used_pointer_anywhere |= used_pointer
        offset += 4  # QTYPE + QCLASS

    def parse_rr(offset: int) -> int:
        nonlocal used_pointer_anywhere
        offset, used_pointer = parse_name(offset)
        used_pointer_anywhere |= used_pointer

        rrtype = int.from_bytes(wire[offset : offset + 2], "big")
        offset += 2  # TYPE
        offset += 2  # CLASS
        offset += 4  # TTL
        rdlength = int.from_bytes(wire[offset : offset + 2], "big")
        offset += 2  # RDLENGTH

        rdata_start = offset
        if rrtype == dns.rdatatype.SOA:
            offset, used_pointer = parse_name(offset)  # MNAME
            used_pointer_anywhere |= used_pointer
            offset, used_pointer = parse_name(offset)  # RNAME
            used_pointer_anywhere |= used_pointer
            offset += 20  # SERIAL, REFRESH, RETRY, EXPIRE, MINIMUM
        else:
            offset += rdlength

        # Defensive: ensure we always advance at least the declared rdata length.
        if offset < rdata_start + rdlength:
            offset = rdata_start + rdlength

        return offset

    for _ in range(ancount + nscount + arcount):
        offset = parse_rr(offset)

    return used_pointer_anywhere


def _assert_response_flags(resp: dns.message.Message, *, aa: bool = True):
    assert bool(resp.flags & dns.flags.AA) == aa
    assert bool(resp.flags & dns.flags.QR)
    assert not bool(resp.flags & dns.flags.RA)
    assert not bool(resp.flags & dns.flags.TC)


def _assert_section_counts(
    resp: dns.message.Message,
    *,
    additional: int = 0,
    authority: int = 0,
    answer: int = 0,
):
    assert len(resp.additional) == additional
    assert len(resp.authority) == authority
    assert len(resp.answer) == answer


# ---------------------------------------------------------------------------
# Module-scoped server fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def live_server():
    """Start a real UDP server on 127.0.0.1:<OS-assigned port>.

    Zone layout
    -----------
    Zone:  example.integration.test.
      NS   @ → ns1.integration.test.
      SOA  @ (auto-generated via DnsServerZoneUpdater)
      A    www → 192.0.2.1  (RFC 5737 TEST-NET-1)

    IPs are pre-marked healthy so initialize_zone() populates the zone
    immediately without making real TCP connections.
    """
    zone_origins = ZoneOrigins(_ZONE, [_ALIAS_ZONE])

    a_record = AHealthyRecord(
        subdomain=dns.name.from_text(_SUBDOMAIN, origin=zone_origins.primary),
        healthy_ips=[AHealthyIp(ip=_SUBDOMAIN_IP, health_port=8080, is_healthy=True)],
    )

    config = DnsServerConfig(
        zone_origins=zone_origins,
        primary_name_server=_NS,
        name_servers=frozenset([_NS]),
        a_records=frozenset([a_record]),
        ext_private_key=None,
    )

    # min_interval drives TTL calculations for NS/SOA/A records; 30 s is a
    # reasonable value for tests — it has no effect on timing because
    # initialize_zone() is called exactly once.
    updater = DnsServerZoneUpdater(min_interval=30, connection_timeout=2, config=config)
    # Populate zone without health checks — IPs already marked healthy above
    updater.initialize_zone()

    server = socketserver.UDPServer(("127.0.0.1", 0), DnsServerUdpHandler)
    server.zone = updater.zone
    server.zone_origins = zone_origins

    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    # Pause long enough for serve_forever() to enter its select loop.
    time.sleep(_SERVER_READY_WAIT)

    host, port = server.server_address
    yield host, port

    server.shutdown()
    thread.join(timeout=5)


# ---------------------------------------------------------------------------
# Positive responses — RFC 1034 §6.2
# Response header fields — RFC 1035 §4.1.1
# ---------------------------------------------------------------------------


class TestPositiveResponses:
    """NOERROR responses for in-zone owner names and record types."""

    def test_a_query_returns_noerror_expected_ip_and_empty_authority(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_SUBDOMAIN_FQDN, dns.rdatatype.A)
        resp = _udp_query(host, port, query)

        assert resp.rcode() == dns.rcode.NOERROR
        assert resp.id == query.id

        _assert_section_counts(resp, answer=1)
        assert resp.answer[0].rdtype == dns.rdatatype.A
        assert any(str(rdata) == _SUBDOMAIN_IP for rdata in resp.answer[0])

        _assert_response_flags(resp)

    @pytest.mark.parametrize(
        "qname",
        [
            _MIXED_CASE_SUBDOMAIN_FQDN,
            _MIXED_CASE_ALIAS_SUBDOMAIN_FQDN,
        ],
        ids=["mixed-case-primary", "mixed-case-alias"],
    )
    def test_mixed_case_a_query_returns_noerror_expected_ip(self, live_server, qname):
        host, port = live_server
        query = dns.message.make_query(qname, dns.rdatatype.A)
        resp = _udp_query(host, port, query)

        assert resp.rcode() == dns.rcode.NOERROR
        assert resp.id == query.id

        _assert_section_counts(resp, answer=1)
        assert resp.answer[0].rdtype == dns.rdatatype.A
        assert any(str(rdata) == _SUBDOMAIN_IP for rdata in resp.answer[0])

        _assert_response_flags(resp)

    def test_soa_query_answer_contains_soa_at_apex(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_ZONE_FQDN, dns.rdatatype.SOA)
        resp = _udp_query(host, port, query)

        assert resp.rcode() == dns.rcode.NOERROR
        assert resp.id == query.id

        _assert_section_counts(resp, answer=1)
        assert resp.answer[0].rdtype == dns.rdatatype.SOA
        assert resp.answer[0].name == dns.name.from_text(_ZONE_FQDN)

        _assert_response_flags(resp)

    def test_ns_query_answer_contains_expected_ns(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_ZONE_FQDN, dns.rdatatype.NS)
        resp = _udp_query(host, port, query)

        assert resp.rcode() == dns.rcode.NOERROR
        assert resp.id == query.id

        _assert_section_counts(resp, answer=1)
        assert resp.answer[0].rdtype == dns.rdatatype.NS
        ns_targets = {str(rdata.target) for rdata in resp.answer[0]}
        assert _NS in ns_targets

        _assert_response_flags(resp)

    def test_alias_a_query_returns_noerror_expected_ip_and_empty_authority(
        self, live_server
    ):
        host, port = live_server
        query = dns.message.make_query(_ALIAS_SUBDOMAIN_FQDN, dns.rdatatype.A)
        resp = _udp_query(host, port, query)

        assert resp.rcode() == dns.rcode.NOERROR
        assert resp.id == query.id

        _assert_section_counts(resp, answer=1)
        assert resp.answer[0].rdtype == dns.rdatatype.A
        assert resp.answer[0].name == dns.name.from_text(_ALIAS_SUBDOMAIN_FQDN)
        assert any(str(rdata) == _SUBDOMAIN_IP for rdata in resp.answer[0])

        _assert_response_flags(resp)


# ---------------------------------------------------------------------------
# Negative responses — RFC 2308 §2.1 (NODATA) and §3 (NXDOMAIN)
# Response header fields — RFC 1035 §4.1.1
# ---------------------------------------------------------------------------


class TestNegativeResponses:
    """NXDOMAIN and NODATA responses must carry the apex SOA in authority."""

    @pytest.mark.parametrize(
        "qname,rdtype,expected_rcode,expected_soa_name",
        [
            (
                _ABSENT_FQDN,
                dns.rdatatype.A,
                dns.rcode.NXDOMAIN,
                _ZONE_FQDN,
            ),
            (
                _SUBDOMAIN_FQDN,
                dns.rdatatype.AAAA,
                dns.rcode.NOERROR,
                _ZONE_FQDN,
            ),
            (
                _SUBDOMAIN_FQDN,
                _UNKNOWN_NON_META_RDTYPE,
                dns.rcode.NOERROR,
                _ZONE_FQDN,
            ),
            (
                _ABSENT_FQDN,
                _UNKNOWN_NON_META_RDTYPE,
                dns.rcode.NXDOMAIN,
                _ZONE_FQDN,
            ),
            (
                _ALIAS_ABSENT_FQDN,
                dns.rdatatype.A,
                dns.rcode.NXDOMAIN,
                _ALIAS_ZONE_FQDN,
            ),
            (
                _ALIAS_SUBDOMAIN_FQDN,
                dns.rdatatype.AAAA,
                dns.rcode.NOERROR,
                _ALIAS_ZONE_FQDN,
            ),
            (
                _ALIAS_SUBDOMAIN_FQDN,
                _UNKNOWN_NON_META_RDTYPE,
                dns.rcode.NOERROR,
                _ALIAS_ZONE_FQDN,
            ),
            (
                _ALIAS_ABSENT_FQDN,
                _UNKNOWN_NON_META_RDTYPE,
                dns.rcode.NXDOMAIN,
                _ALIAS_ZONE_FQDN,
            ),
        ],
        ids=[
            "nxdomain-absent-owner",
            "nodata-absent-type",
            "nodata-unknown-type",
            "nxdomain-absent-owner-unknown-type",
            "alias-nxdomain-absent-owner",
            "alias-nodata-absent-type",
            "alias-nodata-unknown-type",
            "alias-nxdomain-absent-owner-unknown-type",
        ],
    )
    def test_negative_response_has_soa_authority(
        self, live_server, qname, rdtype, expected_rcode, expected_soa_name
    ):
        host, port = live_server
        query = dns.message.make_query(qname, rdtype)
        resp = _udp_query(host, port, query)

        assert resp.rcode() == expected_rcode
        assert resp.id == query.id

        _assert_section_counts(resp, authority=1)
        assert resp.authority[0].rdtype == dns.rdatatype.SOA
        assert resp.authority[0].name == dns.name.from_text(expected_soa_name)
        soa_rdata = next(iter(resp.authority[0]))
        assert resp.authority[0].ttl == soa_rdata.minimum

        _assert_response_flags(resp)

    @pytest.mark.parametrize(
        "qname,rdtype,expected_rcode,expected_soa_name",
        [
            (
                _MIXED_CASE_ABSENT_FQDN,
                dns.rdatatype.A,
                dns.rcode.NXDOMAIN,
                _ZONE_FQDN,
            ),
            (
                _MIXED_CASE_SUBDOMAIN_FQDN,
                dns.rdatatype.AAAA,
                dns.rcode.NOERROR,
                _ZONE_FQDN,
            ),
            (
                _MIXED_CASE_ALIAS_ABSENT_FQDN,
                dns.rdatatype.A,
                dns.rcode.NXDOMAIN,
                _ALIAS_ZONE_FQDN,
            ),
            (
                _MIXED_CASE_ALIAS_SUBDOMAIN_FQDN,
                dns.rdatatype.AAAA,
                dns.rcode.NOERROR,
                _ALIAS_ZONE_FQDN,
            ),
        ],
        ids=[
            "mixed-case-nxdomain-absent-owner",
            "mixed-case-nodata-absent-type",
            "mixed-case-alias-nxdomain-absent-owner",
            "mixed-case-alias-nodata-absent-type",
        ],
    )
    def test_mixed_case_negative_response_has_soa_authority(
        self, live_server, qname, rdtype, expected_rcode, expected_soa_name
    ):
        host, port = live_server
        query = dns.message.make_query(qname, rdtype)
        resp = _udp_query(host, port, query)

        assert resp.rcode() == expected_rcode
        assert resp.id == query.id

        _assert_section_counts(resp, authority=1)
        assert resp.authority[0].rdtype == dns.rdatatype.SOA
        assert resp.authority[0].name.to_text().lower() == expected_soa_name.lower()
        soa_rdata = next(iter(resp.authority[0]))
        assert resp.authority[0].ttl == soa_rdata.minimum

        _assert_response_flags(resp)


# ---------------------------------------------------------------------------
# Rejected queries — RFC 1034 §6.2, RFC 1035 §4.1.1, RFC 9619
# Response header fields — RFC 1035 §4.1.1
# ---------------------------------------------------------------------------


class TestRejectedQueries:
    """Queries that must be rejected per the documented Level 1 policy."""

    @pytest.mark.parametrize(
        "query,expected_rcode",
        [
            (
                dns.message.make_query(_OUT_OF_ZONE_FQDN, dns.rdatatype.A),
                dns.rcode.REFUSED,
            ),
            (
                dns.message.make_query(_MIXED_CASE_OUT_OF_ZONE_FQDN, dns.rdatatype.A),
                dns.rcode.REFUSED,
            ),
            (
                dns.message.make_query(
                    _SUBDOMAIN_FQDN, dns.rdatatype.A, rdclass=dns.rdataclass.CH
                ),
                dns.rcode.REFUSED,
            ),
            # dns.message.Message() with no questions produces QDCOUNT=0; handler returns FORMERR per Level 1 policy.
            (dns.message.Message(), dns.rcode.FORMERR),
        ],
        ids=["out-of-zone", "mixed-case-out-of-zone", "non-in-class", "zero-question"],
    )
    def test_rejected_query_returns_expected_rcode(
        self, live_server, query, expected_rcode
    ):
        host, port = live_server
        resp = _udp_query(host, port, query)

        assert resp.rcode() == expected_rcode
        assert resp.id == query.id

        _assert_section_counts(resp)
        _assert_response_flags(resp, aa=False)

    def test_multi_question_query_returns_formerr(self, live_server):
        host, port = live_server
        # Build a structurally well-formed but RFC-noncompliant DNS wire message
        # with QDCOUNT=2.  RFC 9619 requires FORMERR for QUERY messages
        # with more than one question.
        # dnspython preserves both questions when parsing; the handler must return
        # FORMERR because len(query.question) != 1.
        wire = _make_two_question_wire(_SUBDOMAIN_FQDN, _ABSENT_FQDN)
        resp = _udp_raw_query(host, port, wire)

        assert resp.rcode() == dns.rcode.FORMERR
        assert resp.id == dns.message.from_wire(wire).id

        _assert_section_counts(resp)
        _assert_response_flags(resp, aa=False)

    def test_status_opcode_returns_notimp(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_SUBDOMAIN_FQDN, dns.rdatatype.A)
        query.set_opcode(dns.opcode.STATUS)
        resp = _udp_query(host, port, query)

        assert resp.rcode() == dns.rcode.NOTIMP
        assert resp.id == query.id

        _assert_section_counts(resp)
        _assert_response_flags(resp, aa=False)


# ---------------------------------------------------------------------------
# Malformed wire input — RFC 1035 §4.1.1
# Response header fields — RFC 1035 §4.1.1
# ---------------------------------------------------------------------------


class TestMalformedWireInput:
    """Malformed UDP payloads with a recoverable DNS header return FORMERR."""

    def test_malformed_wire_with_header_returns_formerr(self, live_server):
        host, port = live_server
        resp = _udp_raw_query(host, port, _MALFORMED_HEADER_ONLY_WIRE)

        assert resp.rcode() == dns.rcode.FORMERR
        assert resp.id == _MALFORMED_HEADER_ONLY_ID

        _assert_section_counts(resp)
        _assert_response_flags(resp, aa=False)


# ---------------------------------------------------------------------------
# Response wire encoding — RFC 1123
# ---------------------------------------------------------------------------


class TestResponseWireEncoding:
    def test_response_wire_uses_name_compression(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_ZONE_FQDN, dns.rdatatype.SOA)
        wire = _udp_query_wire(host, port, query)

        resp = dns.message.from_wire(wire)
        assert resp.rcode() == dns.rcode.NOERROR
        assert resp.id == query.id

        assert _scan_wire_for_compressed_names(wire)

    @pytest.mark.parametrize(
        "query_factory",
        [
            lambda: dns.message.make_query(_ZONE_FQDN, dns.rdatatype.SOA),
            _make_status_query,
        ],
        ids=["noerror-soa", "notimp-status"],
    )
    def test_response_wire_header_bits_are_clear(self, live_server, query_factory):
        host, port = live_server
        query = query_factory()
        wire = _udp_query_wire(host, port, query)

        flags = int.from_bytes(wire[2:4], "big")
        assert flags & dns.flags.QR
        assert (flags & dns.flags.RD) == (query.flags & dns.flags.RD)
        assert not (flags & dns.flags.RA)
        assert not (flags & dns.flags.AD)
        assert not (flags & dns.flags.CD)
        assert not (flags & 0x0040)  # Reserved Z bit (RFC 1035 §4.1.1)
