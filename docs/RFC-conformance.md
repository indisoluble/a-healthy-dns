# RFC Conformance: Level 1 Authoritative UDP Subset

This document defines the DNS protocol conformance scope for **A Healthy DNS**.
It maps each implemented behavior to the relevant RFC sections, explicitly
distinguishes the current implementation from known gaps, and identifies
intentional project-scope boundaries.

---

## 1. Purpose and Scope

A Healthy DNS is an authoritative DNS server for a statically configured set of
zones.  It is not a general-purpose resolver, caching server, or forwarding
server.  The scope covered here is the **Level 1 authoritative UDP subset**:
the minimal set of protocol behaviors required to act as a primary authoritative
server for its configured zones over UDP.

This document is accurate for the codebase at the time of writing and serves as
the baseline for assessing future protocol extensions.

---

## 2. Conformance Scope and Non-Goals

### 2.1 In scope

| Dimension | Scope |
|---|---|
| Transport | UDP only |
| Role | Authoritative only; no recursion, no caching, no forwarding |
| Zones | Configured primary zone + alias zones |
| DNS class | IN (Internet) only |
| Opcodes | QUERY (0) — meaningful responses; other opcodes not enforced |
| Record types served | A (configured subdomains), NS (zone apex), SOA (zone apex), RRSIG (if DNSSEC enabled) |

### 2.2 Non-goals (intentional scope limits)

The following are **not implemented** and are outside the current project scope
(see `docs/project-brief.md` for the authoritative non-goals list):

- TCP transport (RFC 7766 §5 recommends TCP support; this is a known limitation)
- Recursive resolution or referral (no CNAME, DNAME, delegation)
- AAAA / IPv6 records
- Zone transfer (AXFR / IXFR)
- Dynamic update (RFC 2136)
- EDNS0 (RFC 6891)
- DNSSEC validation of upstream data
- Multi-server replication or zone synchronisation

---

## 3. Level 1 Authoritative UDP Subset

### 3.1 Transport

The server binds a single UDP socket via Python's `socketserver.UDPServer`.
Each datagram is processed synchronously in the main serving thread.
No TCP listener is started.

**Source:** `indisoluble/a_healthy_dns/main.py` (server creation) and
`indisoluble/a_healthy_dns/dns_server_udp_handler.py` (handler class).

### 3.2 Zone scope

Queries are matched against a **primary zone** and zero or more **alias zones**
configured at startup.  A name is "in scope" if `ZoneOrigins.relativize()`
returns a non-`None` result, i.e., the name is a subdomain of one of the
configured origins.

**Source:** `indisoluble/a_healthy_dns/records/zone_origins.py:38-46`.

### 3.3 Answer header flags

Every response produced by the server carries:

| Flag | Value | Note |
|---|---|---|
| QR | 1 | Set by `dns.message.make_response()` |
| AA | 1 | Set explicitly: `response.flags \|= dns.flags.AA` |
| RD | copied from query | Not modified; server never sets RA=1 |
| RA | 0 | Recursion not available |
| TC | 0 | No truncation logic; oversized datagrams sent as-is (see §6.1) |

**Source:** `indisoluble/a_healthy_dns/dns_server_udp_handler.py:78-79`.

### 3.4 Health-driven record availability

A background thread continuously runs TCP health checks against every configured
IP.  After each health check cycle, the zone is atomically rewritten:

- Subdomains whose IPs are **all unhealthy** are omitted from the new zone
  entirely — no A record node is created for them.
- A subsequent query for that subdomain therefore finds no node in the zone and
  returns **NXDOMAIN**.

This is the primary project-specific semantic layered on top of standard DNS
authoritative behavior.

**Source:** `indisoluble/a_healthy_dns/dns_server_zone_updater.py:124-132` and
`indisoluble/a_healthy_dns/records/a_record.py`.

---

## 4. Behavior Matrix

The table below covers every query scenario handled by the current
implementation.  The **Implemented behavior** column describes what the code
actually does today; the **Notes** column calls out gaps relative to the stated
Level 1 policy or relevant RFC guidance.

| Area | Query / scenario | Implemented behavior | RCODE | Authority section | Driving RFC(s) and section(s) | Notes |
|---|---|---|---|---|---|---|
| **Wire parsing** | Datagram that cannot be decoded as DNS message | No response sent; warning logged | — | — | RFC 1035 §4.1 | RFC 1035 §4.1 expects servers to return FORMERR where possible; since message ID cannot be extracted, silent drop is the only viable option.  Project choice. |
| **Question section** | Parseable query with empty question section (QDCOUNT = 0) | FORMERR | FORMERR (2) | None | RFC 1035 §4.1.1, §4.1.2 | Correct: a response cannot be meaningful without a question. |
| **Multi-question** | QDCOUNT > 1 | First question answered; extra questions silently ignored | Determined by first question | Per first question | RFC 1035 §4.1.2 | RFC 1035 §4.1.2 allows QDCOUNT > 1 in theory but practice converged to exactly 1.  Current code does not return FORMERR for excess questions.  Known gap; see §6.2. |
| **Opcode** | Opcode other than QUERY (e.g., NOTIFY, UPDATE, STATUS) | Response generated as if QUERY; no opcode check performed | Determined by zone lookup | None | RFC 1035 §4.1.1 | Non-QUERY opcodes should yield NOTIMP.  Known gap; see §6.3. |
| **DNS class** | Non-IN class query (CH, HS, ANY) | Zone node found; `get_rdataset(IN, qtype)` returns `None`; NOERROR with empty answer | NOERROR | None | RFC 1034 §3.7, RFC 1035 §3.2.1 | Non-IN queries are not explicitly rejected.  If the zone node exists, the response is NOERROR / empty answer because no IN records match the requested class.  Known gap; see §6.4. |
| **Outside served zones** | Query for a name not under any configured zone origin | NXDOMAIN; warning logged | NXDOMAIN (3) | None | RFC 1035 §4.3.1 | RFC 1035 §4.3.1 states that if a server is not authoritative for the queried domain it should not return NXDOMAIN; REFUSED is the appropriate response.  Current code returns NXDOMAIN.  Known gap; see §6.5. |
| **In-zone: name not found** | Query for a name within a served zone that has no zone node (including a name whose IPs are all unhealthy) | NXDOMAIN; warning logged | NXDOMAIN (3) | None (SOA absent) | RFC 1035 §4.3.2, RFC 2308 §2, §3 | RFC 2308 §3 states that an authoritative NXDOMAIN response SHOULD include the zone SOA in the authority section.  SOA is currently omitted.  Known gap; see §6.6. |
| **In-zone: owner exists, QTYPE absent** | Query for a name that has a zone node but no rdataset of the requested type (e.g., MX query for a name that has only an A record) | NOERROR, empty answer section | NOERROR (0) | None (SOA absent) | RFC 2308 §2.1, §3 | RFC 2308 §2.1 defines this as a NODATA response and §3 states the SOA SHOULD appear in the authority section.  SOA is currently omitted.  Known gap; see §6.6. |
| **Positive A answer** | Query QTYPE=A for a name in zone with healthy IPs | NOERROR; A RRset in answer section; AA=1 | NOERROR (0) | — | RFC 1035 §3.2.2, §4.3.2, RFC 2181 §5 | Correct authoritative positive answer. |
| **Positive SOA answer** | Query QTYPE=SOA for zone apex | NOERROR; SOA RRset in answer section; AA=1 | NOERROR (0) | — | RFC 1035 §3.3.13, §4.3.2 | Correct. |
| **Positive NS answer** | Query QTYPE=NS for zone apex | NOERROR; NS RRset in answer section; AA=1 | NOERROR (0) | — | RFC 1035 §3.3.11, §4.3.2 | Correct. |
| **Health-driven removal** | All configured IPs for a subdomain fail TCP health checks → subdomain removed from zone | Subsequent queries for that name return NXDOMAIN (node absent from zone) | NXDOMAIN (3) | None | RFC 1035 §4.3.2 | Project-specific behavior layered on top of standard DNS.  Not an RFC requirement; intentional project design (see `docs/project-brief.md` §R1–R4). |

---

## 5. RFC Mapping by Behavior

This section maps each relevant RFC section to the behaviors documented above.
It is intended as a quick cross-reference when evaluating future changes.

### RFC 1034 — Domain Names: Concepts and Facilities

| Section | Behavior area |
|---|---|
| §3.7 Classes | Only IN class records are stored in the zone; non-IN queries receive NOERROR empty answer |
| §4.3.1 Process of query | Authoritative-only server; no referrals or recursive service |

### RFC 1035 — Domain Names: Implementation and Specification

| Section | Behavior area |
|---|---|
| §3.2.1 TYPE and CLASS values | IN class only; A, NS, SOA served; RRSIG optionally |
| §3.2.2 A record | A record format and creation (`records/a_record.py`) |
| §3.3.11 NS record | NS record at zone apex (`records/ns_record.py`) |
| §3.3.13 SOA record | SOA record at zone apex (`records/soa_record.py`) |
| §4.1 Messages | Wire format parsed via `dns.message.from_wire()`; unparseable datagrams silently dropped |
| §4.1.1 Header section format | QR=1, AA=1 set on all responses; OPCODE copied from query; not validated |
| §4.1.2 Question section | QDCOUNT=0 → FORMERR; QDCOUNT>1 → first question answered (gap) |
| §4.3.1 Resolver algorithms | Authoritative responses only; outside-zone queries return NXDOMAIN (should be REFUSED — gap) |
| §4.3.2 Processing queries | Node lookup → NXDOMAIN / NODATA / positive answer path; AA set |

### RFC 2181 — Clarifications to the DNS Specification

| Section | Behavior area |
|---|---|
| §5 Authoritative data | AA bit set unconditionally on all authoritative responses |

### RFC 2308 — Negative Caching of DNS Queries

| Section | Behavior area |
|---|---|
| §2 NAME ERROR | NXDOMAIN issued for absent in-zone names; SOA authority absent (gap) |
| §2.1 NODATA | NOERROR / empty answer for existing owner with absent QTYPE; SOA authority absent (gap) |
| §3 Negative answers from auth. servers | SOA SHOULD appear in authority section for all negative responses — not yet implemented |

### RFC 7766 — DNS Transport over TCP

| Section | Behavior area |
|---|---|
| §5 Transport protocol selection | TCP not supported — intentional project scope limit; UDP only |

---

## 6. Known Limitations and Future Extensions

Each entry below identifies a gap between the current implementation and either
the stated Level 1 policy or RFC guidance, along with the relevant code
location.

### 6.1 No TC (truncation) handling

The server does not set the TC bit and does not truncate oversized UDP responses.
Responses that exceed the path MTU may be silently dropped by the network.
For the current record set (A, NS, SOA for modest zone sizes) this is unlikely
to be a problem in practice.

**Future extension:** Enforce a 512-byte or EDNS0-negotiated message size limit
and set TC=1 when a response would exceed it.

### 6.2 QDCOUNT > 1 not rejected

Queries with more than one question are not rejected with FORMERR; only the
first question is processed.  RFC 1035 §4.1.2 technically permits multiple
questions, but virtually all real DNS software treats QDCOUNT=1 as mandatory.

**Future extension:** Return FORMERR when QDCOUNT > 1.  
**Code location:** `indisoluble/a_healthy_dns/dns_server_udp_handler.py:81-84`.

### 6.3 Non-QUERY opcodes not rejected

Queries with opcodes other than QUERY (e.g., NOTIFY=4, UPDATE=5, STATUS=2) are
processed through the same zone-lookup path instead of being rejected with
NOTIMP.  This can produce unexpected responses for operations that were never
meant to be answered as a QUERY.

**Future extension:** Check the query opcode before zone lookup and return
NOTIMP for all opcodes other than QUERY.  
**Code location:** `indisoluble/a_healthy_dns/dns_server_udp_handler.py:81`.

### 6.4 Non-IN class queries not explicitly rejected

A query in class CH (Chaosnet) or HS (Hesiod) for a name that happens to exist
in the zone will receive a NOERROR / empty answer rather than an explicit
rejection.  This can be misleading; RFC 1034 §3.7 makes classes independent
namespaces.

**Future extension:** Return REFUSED (or FORMERR) when QCLASS is not IN.  
**Code location:** `indisoluble/a_healthy_dns/dns_server_udp_handler.py:46`.

### 6.5 Outside-zone queries return NXDOMAIN instead of REFUSED

When a query arrives for a name that is not under any configured zone origin,
the server returns NXDOMAIN.  Per RFC 1035 §4.3.1, an authoritative server
that is not authoritative for the queried domain should return REFUSED (RCODE=5)
or provide a referral — not NXDOMAIN, which implies authority and knowledge of
non-existence.

**Future extension:** Return REFUSED for queries outside all served zones.  
**Code location:** `indisoluble/a_healthy_dns/dns_server_udp_handler.py:32-37`.

### 6.6 SOA absent from authority section in negative responses

RFC 2308 §3 states that authoritative negative responses (both NXDOMAIN and
NODATA) SHOULD include the zone apex SOA record in the authority section.
The current implementation returns neither SOA nor any other authority RR in
negative responses.

Omitting the SOA prevents resolvers from caching negative responses for their
correct TTL (they must use a default negative TTL instead), which is a
correctness issue for deployments behind resolvers.

**Future extension:** Append the zone apex SOA RRset to the authority section
of all NXDOMAIN and NODATA responses.  
**Code location:** `indisoluble/a_healthy_dns/dns_server_udp_handler.py:32-54`.

### 6.7 TCP transport not supported

RFC 7766 §5 recommends that all DNS servers support TCP transport.  A Healthy
DNS is UDP-only.  For the intended use case (authoritative server returning
small A, NS, and SOA responses) TCP is not required, but it is a limitation for
responses that approach the DNS message size limit.

This is an **intentional project scope limit**, not an oversight.

---

## 7. Summary

**Implemented and RFC-aligned:**
- Authoritative UDP server for configured primary + alias zones
- QR=1, AA=1 on all responses
- FORMERR for QDCOUNT=0 (no question section)
- NXDOMAIN for absent in-zone names (including health-removed names)
- NOERROR / empty answer (NODATA) for existing names with absent QTYPE
- Positive answers for A, NS, SOA record types

**Implemented but deviating from RFC guidance:**
- Outside-zone queries return NXDOMAIN instead of REFUSED (§6.5)
- Negative responses omit SOA in authority section (§6.6)
- QDCOUNT > 1 silently uses first question instead of FORMERR (§6.2)
- Non-QUERY opcodes not rejected with NOTIMP (§6.3)
- Non-IN class queries not explicitly rejected (§6.4)

**Intentional project scope limits (non-goals):**
- UDP only; no TCP (§6.7)
- No recursion, no caching, no forwarding, no zone transfer
- No AAAA / IPv6, no CNAME / DNAME, no EDNS0
