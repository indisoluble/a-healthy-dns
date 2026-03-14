#!/usr/bin/env python3

"""Component integration tests for the authoritative UDP serving layer.

Scope
-----
These tests validate the **authoritative UDP server component** end-to-end:

  dns.message.from_wire()  →  DnsServerUdpHandler  →  DnsServerZoneUpdater zone

A real UDP server is started on localhost with a real in-memory zone whose
state is pre-populated via ``DnsServerZoneUpdater.update(check_ips=False)``.
All queries are sent as actual UDP datagrams; all assertions operate on the
parsed wire-level response.

**What this suite covers:**
- RFC-conformant response shapes for all Level 1 response categories
  (NOERROR, NXDOMAIN, NODATA, REFUSED, NOTIMP, FORMERR) as documented in
  docs/RFC-conformance.md
- Response header fields (QR, ID, AA, RA, TC)
- Answer / authority / additional section shapes
- Rejection of malformed wire input (silent drop)
- Real wire-level QDCOUNT != 1 (zero-question and multi-question FORMERR)

**What this suite does NOT cover:**
- The health-check lifecycle (periodic TCP probes, dynamic A-record
  addition/removal when backends go up or down).  That behaviour is
  exercised by the Docker end-to-end tests in
  ``.github/workflows/test-integration.yml``.
- Container startup, Docker networking, or alias zone routing.

These tests complement the mocked unit tests in
``tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py``.
"""

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
_NS = "ns1.example.integration.test."
_SUBDOMAIN = "www"
_SUBDOMAIN_IP = "192.0.2.1"   # RFC 5737 TEST-NET-1
_ABSENT_SUBDOMAIN = "missing"

_ZONE_FQDN = f"{_ZONE}."
_SUBDOMAIN_FQDN = f"{_SUBDOMAIN}.{_ZONE}."
_ABSENT_FQDN = f"{_ABSENT_SUBDOMAIN}.{_ZONE}."
_OUT_OF_ZONE_FQDN = "www.unrelated.test."

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


# ---------------------------------------------------------------------------
# Module-scoped server fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def live_server():
    """Start a real UDP server on 127.0.0.1:<OS-assigned port>.

    Zone layout
    -----------
    Zone:  example.integration.test.
      NS   @ → ns1.example.integration.test.
      SOA  @ (auto-generated via DnsServerZoneUpdater)
      A    www → 192.0.2.1  (RFC 5737 TEST-NET-1)

    IPs are pre-marked healthy so check_ips=False populates the zone
    immediately without making real TCP connections.
    """
    zone_origins = ZoneOrigins(_ZONE, [])

    a_record = AHealthyRecord(
        subdomain=dns.name.from_text(_SUBDOMAIN, origin=zone_origins.primary),
        healthy_ips=[AHealthyIp(ip=_SUBDOMAIN_IP, health_port=8080, is_healthy=True)],
    )

    config = DnsServerConfig(
        zone_origins=zone_origins,
        name_servers=frozenset([_NS]),
        a_records=frozenset([a_record]),
        ext_private_key=None,
    )

    # min_interval drives TTL calculations for NS/SOA/A records; 30 s is a
    # reasonable value for tests — it has no effect on timing because
    # update() is called exactly once with check_ips=False.
    updater = DnsServerZoneUpdater(
        min_interval=30, connection_timeout=2, config=config
    )
    # Populate zone without health checks — IPs already marked healthy above
    updater.update(check_ips=False)

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
# ---------------------------------------------------------------------------

class TestPositiveResponses:
    """NOERROR responses for in-zone owner names and record types."""

    def test_a_query_returns_noerror(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_SUBDOMAIN_FQDN, dns.rdatatype.A)
        resp = _udp_query(host, port, query)

        assert resp.rcode() == dns.rcode.NOERROR

    def test_a_query_answer_contains_expected_ip(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_SUBDOMAIN_FQDN, dns.rdatatype.A)
        resp = _udp_query(host, port, query)

        assert len(resp.answer) == 1
        assert resp.answer[0].rdtype == dns.rdatatype.A
        assert any(str(rdata) == _SUBDOMAIN_IP for rdata in resp.answer[0])

    def test_a_query_authority_and_additional_empty(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_SUBDOMAIN_FQDN, dns.rdatatype.A)
        resp = _udp_query(host, port, query)

        assert len(resp.authority) == 0
        assert len(resp.additional) == 0

    def test_soa_query_at_apex_returns_noerror(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_ZONE_FQDN, dns.rdatatype.SOA)
        resp = _udp_query(host, port, query)

        assert resp.rcode() == dns.rcode.NOERROR

    def test_soa_query_answer_contains_soa_at_apex(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_ZONE_FQDN, dns.rdatatype.SOA)
        resp = _udp_query(host, port, query)

        assert len(resp.answer) == 1
        assert resp.answer[0].rdtype == dns.rdatatype.SOA
        assert resp.answer[0].name == dns.name.from_text(_ZONE_FQDN)

    def test_ns_query_at_apex_returns_noerror(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_ZONE_FQDN, dns.rdatatype.NS)
        resp = _udp_query(host, port, query)

        assert resp.rcode() == dns.rcode.NOERROR

    def test_ns_query_answer_contains_expected_ns(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_ZONE_FQDN, dns.rdatatype.NS)
        resp = _udp_query(host, port, query)

        assert len(resp.answer) == 1
        assert resp.answer[0].rdtype == dns.rdatatype.NS
        ns_targets = {str(rdata.target) for rdata in resp.answer[0]}
        assert _NS in ns_targets


# ---------------------------------------------------------------------------
# Response header fields — RFC 1035 §4.1.1
# ---------------------------------------------------------------------------

class TestResponseHeaderFields:
    """QR, ID, AA, RA, TC fields on all Level 1 response categories."""

    def test_positive_a_response_header(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_SUBDOMAIN_FQDN, dns.rdatatype.A)
        resp = _udp_query(host, port, query)

        assert bool(resp.flags & dns.flags.QR)
        assert resp.id == query.id
        assert bool(resp.flags & dns.flags.AA)
        assert not bool(resp.flags & dns.flags.RA)
        assert not bool(resp.flags & dns.flags.TC)

    def test_nxdomain_response_header(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_ABSENT_FQDN, dns.rdatatype.A)
        resp = _udp_query(host, port, query)

        assert bool(resp.flags & dns.flags.QR)
        assert resp.id == query.id
        assert bool(resp.flags & dns.flags.AA)
        assert not bool(resp.flags & dns.flags.RA)
        assert not bool(resp.flags & dns.flags.TC)

    def test_refused_response_header(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_OUT_OF_ZONE_FQDN, dns.rdatatype.A)
        resp = _udp_query(host, port, query)

        assert bool(resp.flags & dns.flags.QR)
        assert resp.id == query.id
        assert bool(resp.flags & dns.flags.AA)
        assert not bool(resp.flags & dns.flags.RA)
        assert not bool(resp.flags & dns.flags.TC)


# ---------------------------------------------------------------------------
# Negative responses — RFC 2308 §2.1 (NODATA) and §3 (NXDOMAIN)
# ---------------------------------------------------------------------------

class TestNegativeResponses:
    """NXDOMAIN and NODATA responses must carry the apex SOA in authority."""

    def test_nxdomain_rcode_for_absent_owner(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_ABSENT_FQDN, dns.rdatatype.A)
        resp = _udp_query(host, port, query)

        assert resp.rcode() == dns.rcode.NXDOMAIN

    def test_nxdomain_authority_contains_apex_soa(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_ABSENT_FQDN, dns.rdatatype.A)
        resp = _udp_query(host, port, query)

        assert len(resp.authority) == 1
        assert resp.authority[0].rdtype == dns.rdatatype.SOA
        assert resp.authority[0].name == dns.name.from_text(_ZONE_FQDN)

    def test_nxdomain_answer_and_additional_empty(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_ABSENT_FQDN, dns.rdatatype.A)
        resp = _udp_query(host, port, query)

        assert len(resp.answer) == 0
        assert len(resp.additional) == 0

    def test_nodata_rcode_for_absent_type(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_SUBDOMAIN_FQDN, dns.rdatatype.AAAA)
        resp = _udp_query(host, port, query)

        assert resp.rcode() == dns.rcode.NOERROR

    def test_nodata_authority_contains_apex_soa(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_SUBDOMAIN_FQDN, dns.rdatatype.AAAA)
        resp = _udp_query(host, port, query)

        assert len(resp.authority) == 1
        assert resp.authority[0].rdtype == dns.rdatatype.SOA
        assert resp.authority[0].name == dns.name.from_text(_ZONE_FQDN)

    def test_nodata_answer_and_additional_empty(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_SUBDOMAIN_FQDN, dns.rdatatype.AAAA)
        resp = _udp_query(host, port, query)

        assert len(resp.answer) == 0
        assert len(resp.additional) == 0


# ---------------------------------------------------------------------------
# Rejected queries — RFC 1034 §6.2, RFC 1035 §4.1.1, RFC 2181 §5.1
# ---------------------------------------------------------------------------

class TestRejectedQueries:
    """Queries that must be rejected per the documented Level 1 policy."""

    def test_out_of_zone_returns_refused(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_OUT_OF_ZONE_FQDN, dns.rdatatype.A)
        resp = _udp_query(host, port, query)

        assert resp.rcode() == dns.rcode.REFUSED

    def test_out_of_zone_refused_sections_empty(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_OUT_OF_ZONE_FQDN, dns.rdatatype.A)
        resp = _udp_query(host, port, query)

        assert len(resp.answer) == 0
        assert len(resp.authority) == 0
        assert len(resp.additional) == 0

    def test_non_in_class_returns_refused(self, live_server):
        host, port = live_server
        query = dns.message.make_query(
            _SUBDOMAIN_FQDN, dns.rdatatype.A, rdclass=dns.rdataclass.CH
        )
        resp = _udp_query(host, port, query)

        assert resp.rcode() == dns.rcode.REFUSED

    def test_non_in_class_refused_sections_empty(self, live_server):
        host, port = live_server
        query = dns.message.make_query(
            _SUBDOMAIN_FQDN, dns.rdatatype.A, rdclass=dns.rdataclass.CH
        )
        resp = _udp_query(host, port, query)

        assert len(resp.answer) == 0
        assert len(resp.authority) == 0
        assert len(resp.additional) == 0

    def test_status_opcode_returns_notimp(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_SUBDOMAIN_FQDN, dns.rdatatype.A)
        query.set_opcode(dns.opcode.STATUS)
        resp = _udp_query(host, port, query)

        assert resp.rcode() == dns.rcode.NOTIMP

    def test_notimp_sections_empty(self, live_server):
        host, port = live_server
        query = dns.message.make_query(_SUBDOMAIN_FQDN, dns.rdatatype.A)
        query.set_opcode(dns.opcode.STATUS)
        resp = _udp_query(host, port, query)

        assert len(resp.answer) == 0
        assert len(resp.authority) == 0
        assert len(resp.additional) == 0

    def test_zero_question_query_returns_formerr(self, live_server):
        host, port = live_server
        # dns.message.Message() with no questions produces a valid wire message
        # with QDCOUNT=0; the handler must return FORMERR (RFC 2181 §5.1)
        query = dns.message.Message()
        resp = _udp_query(host, port, query)

        assert resp.rcode() == dns.rcode.FORMERR

    def test_multi_question_query_returns_formerr(self, live_server):
        host, port = live_server
        # Build a structurally well-formed but RFC-noncompliant DNS wire message
        # with QDCOUNT=2.  RFC 2181 §5.1 requires exactly one question per query.
        # dnspython preserves both questions when parsing; the handler must return
        # FORMERR because len(query.question) != 1.
        wire = _make_two_question_wire(_SUBDOMAIN_FQDN, _ABSENT_FQDN)
        resp = _udp_raw_query(host, port, wire)

        assert resp.rcode() == dns.rcode.FORMERR
