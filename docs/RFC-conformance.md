# RFC Conformance

RFC conformance reference for **A Healthy DNS** — Level 1 authoritative UDP subset.

---

## 1. General purpose and scope

### What this server is

A Healthy DNS is an **authoritative DNS server**: it holds the definitive answers for one or more configured DNS zones and answers queries about names within those zones.  It does not perform recursive lookups, does not cache answers from other servers, and does not forward queries.

This document describes RFC conformance for the current implementation scope.  Its intended audience is anyone contributing to or planning work on this project — technical readers who are not necessarily DNS specialists.

### What "RFC conformance" means here

DNS behaviour is standardised in a series of documents called RFCs (Request For Comments), published by the IETF.  A conformant DNS server must produce responses that match the requirements in those RFCs.  Failing to do so can cause resolvers, monitoring tools, or other servers to misinterpret or reject responses.

For this project "RFC conformance" means producing wire-correct responses for every query type within the documented Level 1 scope.

### What Level 1 covers

Level 1 is a deliberately limited scope.  It covers the minimum behaviour required to be a correct authoritative UDP server for the record types this project serves (A, SOA, NS, and optionally RRSIG).

| Behaviour | Level 1 target |
|---|---|
| Query is for a name **outside** all hosted zones | Return **REFUSED** |
| Query is for a name **inside** a hosted zone but the owner name does not exist | Return **NXDOMAIN** (name does not exist) |
| Owner name exists but the queried record type is absent | Return **NOERROR** with an empty answer section (a **NODATA** response) |
| NODATA or NXDOMAIN response | Include the apex **SOA** record in the authority section |
| Query cannot be parsed or has an invalid structure | Return **FORMERR** where appropriate |
| Query uses an unsupported opcode | Return **NOTIMP** |
| Query is not for the **IN** (Internet) class | Treat as unsupported |
| Query has more or fewer than exactly one question | Treat as a format error |

### What Level 1 does not cover

- Recursive or iterative resolution
- Zone transfers (AXFR / IXFR)
- EDNS(0) extension processing
- TCP transport
- IPv6 (AAAA records)
- Any record type beyond A, SOA, NS, and RRSIG

### Key term glossary

| Term | Meaning |
|---|---|
| **Authoritative** | The server holds the definitive records for a zone and sets the AA (Authoritative Answer) flag in its responses |
| **NXDOMAIN** | "Non-Existent Domain" — the queried name does not exist in the zone at all |
| **NODATA / NOERROR empty answer** | The queried name exists but has no records of the requested type; the response code is NOERROR (not an error) and the answer section is empty |
| **SOA in authority** | For negative responses (NXDOMAIN and NODATA) the server includes the zone's Start of Authority record in the authority section so that negative caching behaviour is well-defined |
| **REFUSED** | The server refuses to answer because the query is for a zone it does not serve |
| **FORMERR** | "Format Error" — the server cannot interpret the query because it is malformed |
| **Opcode** | A 4-bit field in the DNS message header indicating the type of operation (e.g. standard query, inverse query, notify) |
| **QCLASS / IN** | The class field in a DNS question; IN (Internet, value 1) is the only class used in modern DNS practice |

---

## 2. Minimum RFCs required to fully meet the described scope

The table below identifies the smallest set of RFCs whose requirements must be met to produce correct Level 1 responses.  RFC 7766 (DNS over TCP) is not listed because Level 1 uses UDP only.

| RFC | Title | Why it matters here | Link |
|---|---|---|---|
| RFC 1034 | Domain Names — Concepts and Facilities | Defines the authoritative server model, zone concept, NXDOMAIN, and NOERROR semantics | https://www.rfc-editor.org/rfc/rfc1034 |
| RFC 1035 | Domain Names — Implementation and Specification | Defines the DNS wire format, QDCOUNT, opcode field, response codes FORMERR and NOTIMP, and the message header | https://www.rfc-editor.org/rfc/rfc1035 |
| RFC 2181 | Clarifications to the DNS Specification | Clarifies that a DNS message must contain exactly one question (QDCOUNT = 1); tightens several ambiguities in RFC 1035 | https://www.rfc-editor.org/rfc/rfc2181 |
| RFC 2308 | Negative Caching of DNS Queries (DNS NCACHE) | Specifies that NXDOMAIN and NODATA responses must include the apex SOA in the authority section so resolvers can cache negative results correctly | https://www.rfc-editor.org/rfc/rfc2308 |

---

## 3. Current coverage of each RFC

The assessments below are based on the source file `indisoluble/a_healthy_dns/dns_server_udp_handler.py` and supporting modules.  Where the repository does not clearly demonstrate a behaviour the assessment is marked **uncertain**.

---

### 3.1 RFC 1034 — Domain Names: Concepts and Facilities

RFC 1034 establishes the conceptual model for authoritative DNS servers: a server is authoritative for one or more zones, answers queries about names in those zones with the AA flag set, and uses defined response codes for names that are absent or that fall outside its zones.

**RFC 1034 §6.2** — https://www.rfc-editor.org/rfc/rfc1034 describes the algorithm an authoritative server uses to process a query.

#### Currently covered

| Behaviour | Status | Notes |
|---|---|---|
| Authoritative Answer (AA) flag set on all responses | **Implemented** | `indisoluble/a_healthy_dns/dns_server_udp_handler.py:79` sets `dns.flags.AA` on every response |
| NXDOMAIN when owner name is absent from an in-zone query | **Implemented** | Handler returns `dns.rcode.NXDOMAIN` when `txn.get_node(relative_name)` returns nothing |
| NOERROR when owner name exists and records are found | **Implemented** | Handler adds matching RRset to the answer section and returns NOERROR implicitly |

#### Current gaps

| Behaviour | Status | Notes |
|---|---|---|
| REFUSED for queries outside all served zones | **Implemented** | `indisoluble/a_healthy_dns/dns_server_udp_handler.py:36` returns `dns.rcode.REFUSED` when `zone_origins.relativize()` returns `None` |
| SOA in authority for NXDOMAIN responses | **Implemented** | `_add_apex_soa_to_authority()` appends the apex SOA to `response.authority` in the NXDOMAIN branch; see also RFC 2308 §3 |
| NODATA response includes SOA in authority | **Implemented** | `_add_apex_soa_to_authority()` appends the apex SOA to `response.authority` in the NOERROR/empty-answer branch; see also RFC 2308 §2.1 |

---

### 3.2 RFC 1035 — Domain Names: Implementation and Specification

RFC 1035 defines the DNS wire format: the message header structure (including the QDCOUNT field and opcode field), all standard record types, and the FORMERR and NOTIMP response codes.

- RFC 1035 §4.1.1 defines the header format, including QDCOUNT and OPCODE — https://www.rfc-editor.org/rfc/rfc1035
- RFC 1035 §4.1.2 defines the question section format
- RFC 1035 §4.1.3 defines answer, authority, and additional section formats

#### Currently covered

| Behaviour | Status | Notes |
|---|---|---|
| Wire parsing of incoming queries | **Implemented** | `dns.message.from_wire()` is used; `DNSException` is caught |
| FORMERR when question section is empty | **Implemented** | Handler checks `if query.question:` and returns `dns.rcode.FORMERR` |
| Wire serialisation of responses | **Implemented** | `response.to_wire()` is called before sending |
| A, SOA, NS record types in responses | **Implemented** | All three record types are populated by the zone updater |

#### Current gaps

| Behaviour | Status | Notes |
|---|---|---|
| FORMERR when parse fails entirely | **Not implemented** | When `dns.message.from_wire()` raises `DNSException` the handler logs a warning and **returns without sending any response** (`indisoluble/a_healthy_dns/dns_server_udp_handler.py:73-75`).  RFC 1035 §4.1.1 expects a FORMERR response to be sent when possible |
| NOTIMP for unsupported opcodes | **Not implemented** | The handler does not inspect `query.opcode()`.  A query with opcode IQUERY, STATUS, NOTIFY, or UPDATE is silently processed as a standard query |
| QDCOUNT validation (must be exactly 1) | **Not implemented** | The handler only checks whether `query.question` is truthy; it does not reject messages where `len(query.question) > 1`.  RFC 1035 §4.1.1, clarified by RFC 2181 §5.1, requires exactly one question |
| QCLASS / IN class validation | **Not implemented** | The handler never checks `question.rdclass`.  Queries for class CHAOS, HESIOD, or ANY are answered as if they were IN-class queries |

#### Uncertainties

- It is **uncertain** whether dnspython's `from_wire()` already rejects some malformed messages that would otherwise require FORMERR.  The project does not have tests that probe specific malformed inputs to verify the boundary.

---

### 3.3 RFC 2181 — Clarifications to the DNS Specification

RFC 2181 corrects and tightens several ambiguities in RFC 1035.  The requirement most relevant to Level 1 is found in §5.1: a DNS query must contain exactly one question; a server receiving a message with QDCOUNT ≠ 1 should return FORMERR — https://www.rfc-editor.org/rfc/rfc2181.

RFC 2181 §4 also clarifies that the AA flag applies to the entire response when the server is authoritative, which this project already satisfies.

#### Currently covered

| Behaviour | Status | Notes |
|---|---|---|
| AA flag set correctly | **Implemented** | Confirmed as noted under RFC 1034 above |

#### Current gaps

| Behaviour | Status | Notes |
|---|---|---|
| FORMERR for QDCOUNT ≠ 1 (RFC 2181 §5.1) | **Not implemented** | Multi-question messages are not rejected; single-question check uses a truthy test only |

#### Uncertainties

- It is **uncertain** whether dnspython silently drops extra questions when parsing.  Verification is needed to understand what `query.question` actually contains for a QDCOUNT > 1 message.

---

### 3.4 RFC 2308 — Negative Caching of DNS Queries

RFC 2308 defines how negative responses (NXDOMAIN and NODATA) must be structured so that resolvers can cache them correctly.  The core requirement is that both response types **must** include the zone's apex SOA record in the authority section — RFC 2308 §3 (NXDOMAIN) and RFC 2308 §2.1 (NODATA/NOERROR) — https://www.rfc-editor.org/rfc/rfc2308.

Without the SOA in the authority section, resolvers either cannot cache the negative result or cache it with an undefined TTL, leading to repeated unnecessary queries.

RFC 2308 §5 defines the SOA minimum TTL field as the negative caching TTL; this project already populates `SOA MINIMUM` via `calculate_soa_min_ttl()` in `records/time.py`.

#### Currently covered

| Behaviour | Status | Notes |
|---|---|---|
| SOA record with correct `MINIMUM` field exists in zone | **Implemented** | `soa_record.py` populates the minimum TTL field from `calculate_soa_min_ttl()` |

#### Current gaps

| Behaviour | Status | Notes |
|---|---|---|
| SOA in authority section for NXDOMAIN (RFC 2308 §3) | **Implemented** | `_add_apex_soa_to_authority()` appends the apex SOA (`txn.get(dns.name.empty, dns.rdatatype.SOA)`) to `response.authority` |
| SOA in authority section for NODATA (RFC 2308 §2.1) | **Implemented** | Same helper populates the authority section for empty-answer NOERROR responses |

---

## 4. For each RFC, required changes to fully cover it

---

### 4.1 RFC 1034

#### Changes required for Level 1 conformance

1. **~~Fix REFUSED for out-of-zone queries.~~** *(implemented)*
   `indisoluble/a_healthy_dns/dns_server_udp_handler.py:36` now sets `dns.rcode.REFUSED` for out-of-zone queries.

2. **~~Include apex SOA in the authority section for NXDOMAIN responses.~~** *(implemented)*
   `_add_apex_soa_to_authority()` retrieves the apex SOA via `txn.get(dns.name.empty, dns.rdatatype.SOA)` and appends it to `response.authority` in the NXDOMAIN branch.  *See also RFC 2308 §3.*

3. **~~Include apex SOA in the authority section for NODATA responses.~~** *(implemented)*
   Same helper populates the authority section for NOERROR with empty answer.  *See also RFC 2308 §2.1.*

#### Broader changes (beyond Level 1)

- Additional out-of-zone handling (e.g. referrals to delegated zones) is not needed for Level 1 and would require redesigning the zone model.

---

### 4.2 RFC 1035

#### Changes required for Level 1 conformance

1. **Send FORMERR when wire parsing fails.**
   When `dns.message.from_wire()` raises `dns.exception.DNSException`, construct a minimal FORMERR response and send it back to the client rather than silently dropping the query.  *Note: constructing a valid response from a fully unparseable message is difficult; this may be limited to cases where the header is readable.  Whether dnspython exposes enough from a partial parse is an uncertainty that requires testing.*

2. **Validate and reject unsupported opcodes with NOTIMP.**
   After parsing, check `query.opcode()`.  If the opcode is not `dns.opcode.QUERY` (value 0), set the response rcode to `dns.rcode.NOTIMP` and return immediately.  *This is a mandatory RFC requirement.*

3. **Validate QDCOUNT = 1 and return FORMERR if not.**
   After parsing, check `len(query.question) != 1`.  If true, return `dns.rcode.FORMERR`.  This subsumes the current truthy check for `query.question`.  *See also RFC 2181 §5.1.*

4. **Validate QCLASS = IN and return FORMERR (or REFUSED, project choice) if not.**
   After parsing, check `question.rdclass != dns.rdataclass.IN`.  Returning `dns.rcode.REFUSED` is an acceptable project choice for non-IN queries since the server only serves IN-class data; FORMERR is also permitted.  *Document whichever is chosen as a project decision.*

#### Verification work for uncertainties

- **Verify dnspython parse behaviour for malformed inputs:** Write tests that send messages with truncated headers, invalid label encodings, and QDCOUNT > 1, and observe what `from_wire()` returns or raises.  This will clarify whether the FORMERR-on-parse-failure path is already partially covered by the library.

#### Broader changes (beyond Level 1)

- Full EDNS(0) handling (OPT pseudo-RR) is beyond Level 1 scope.
- Additional record types (AAAA, MX, TXT, etc.) are outside current scope.

---

### 4.3 RFC 2181

#### Changes required for Level 1 conformance

1. **Enforce QDCOUNT = 1.**
   As described in §4.2 item 3, add a check for `len(query.question) != 1` and return FORMERR.  This directly implements RFC 2181 §5.1.

#### Verification work for uncertainties

- **Check dnspython's QDCOUNT parsing:** Confirm via a targeted test whether `query.question` is a list that can contain more than one entry for a QDCOUNT > 1 wire message, or whether dnspython normalises or rejects it during parsing.

#### Broader changes (beyond Level 1)

- RFC 2181 §8 (class-in-data semantics) and §9 (TTL semantics) are informational for this scope; no implementation change is needed for Level 1.

---

### 4.4 RFC 2308

#### Changes required for Level 1 conformance

1. **~~Add apex SOA to authority section for NXDOMAIN and NODATA responses.~~** *(implemented)*
   `_add_apex_soa_to_authority()` in `dns_server_udp_handler.py` retrieves the apex SOA from the zone transaction and appends it to `response.authority` for both NXDOMAIN and NOERROR/empty-answer responses.  This satisfies both RFC 2308 §2.1 (NODATA) and RFC 2308 §3 (NXDOMAIN).

#### Broader changes (beyond Level 1)

- RFC 2308 §4 describes referral responses; not applicable for Level 1 since this server does not delegate sub-zones.
- RFC 2308 §6 describes server-side negative caching; also not applicable since this server is authoritative and does not cache resolver results.

---

## PR-style summary

### Files changed

| File | Change type |
|---|---|
| `docs/RFC-conformance.md` | New — this document |
| `docs/table-of-contents.md` | Updated — added entry for this document |

### Minimum RFC set selected

- RFC 1034 — Domain Names: Concepts and Facilities
- RFC 1035 — Domain Names: Implementation and Specification
- RFC 2181 — Clarifications to the DNS Specification
- RFC 2308 — Negative Caching of DNS Queries

RFC 7766 (DNS over TCP) was evaluated and excluded because Level 1 scope is UDP only.

### Main current gaps identified

1. ~~**REFUSED for out-of-zone queries**~~ — **fixed**: `dns_server_udp_handler.py:36` now returns REFUSED
2. ~~**SOA in authority section**~~ — **fixed**: `_add_apex_soa_to_authority()` populates `response.authority` for NXDOMAIN and NODATA responses
3. **NOTIMP for unsupported opcodes** — no opcode check at all (non-conformant with RFC 1035 §4.1.1)
4. **QDCOUNT validation** — QDCOUNT ≠ 1 is not rejected (non-conformant with RFC 2181 §5.1)
5. **QCLASS / IN validation** — non-IN class queries are not rejected
6. **FORMERR on parse failure** — currently drops the connection with no response

### Main uncertainties

- Whether dnspython's `from_wire()` internally rejects malformed messages (truncated headers, invalid labels) that would require FORMERR — *not verified; test coverage needed*
- Whether `query.question` can contain more than one entry after `from_wire()` on a QDCOUNT > 1 wire message — *not verified; test coverage needed*

### Ambiguities intentionally left open

- Whether non-IN class queries should be answered with REFUSED or FORMERR is a valid project choice within RFC bounds; this document marks it as such rather than prescribing one answer.
