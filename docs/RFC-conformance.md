# RFC Conformance

RFC conformance contract for **A Healthy DNS** — Level 1 authoritative UDP response scope.

This document is the canonical home for:
- the DNS protocol behavior this server intentionally covers,
- the RFCs that define correctness for that behavior,
- adjacent RFC references only where they clarify explicit scope boundaries,
- and the current implementation and test coverage status for those applicable RFC requirements.

It does not own product scope, configuration syntax, deployment procedures, or troubleshooting guidance. Those topics live in [`docs/project-brief.md`](project-brief.md), [`docs/configuration-reference.md`](configuration-reference.md), [`docs/docker.md`](docker.md), and [`docs/troubleshooting.md`](troubleshooting.md).

---

## 1. Purpose and use

This document exists to make the DNS protocol contract reviewable. Use it to answer three questions:

1. What DNS behavior does this server intentionally cover?
2. Which RFCs define correctness for that behavior, and which adjacent RFCs are explicitly not conformance dependencies?
3. Which applicable RFC requirements are currently implemented and tested?

Do not use this document as an unqualified claim that A Healthy DNS implements every DNS feature in every referenced RFC. The product deliberately serves a narrow authoritative UDP role. Product scope and non-goals live in [`docs/project-brief.md`](project-brief.md); protocol requirements live in [`docs/requirements.md`](requirements.md).

## 2. Current conformance claim

Current claim: **every necessary Level 1 RFC is fully covered under this document's definition**. The RFC applicability table below contains the complete RFC set needed to judge the declared Level 1 target, and the Level 1 behaviours documented here are implemented and covered by automated tests.

That claim is scoped. For broad DNS RFCs such as RFC 1034 and RFC 1035, "covered" means the implementation satisfies the RFC requirements that apply to the declared Level 1 authoritative UDP target. It does not mean full-document compliance for unrelated resolver behavior, zone transfers, TCP transport, unsupported record types, EDNS(0), or DNSSEC proof semantics.

A listed RFC is a Level 1 conformance dependency only when it appears in the RFC applicability table. RFCs mentioned in glossary notes, scope-boundary rows, or out-of-scope sections are supporting references, not conformance claims.

When this document says an RFC is fully covered for Level 1, it means:

- the RFC applies to at least one behavior in the Level 1 target,
- every applicable requirement from that RFC is implemented for that behavior,
- the behavior is covered by automated tests listed in the test coverage mapping,
- and any broader RFC material outside the target is listed as out of scope rather than treated as a hidden gap.

When an RFC is necessary for the product but not fully covered under that definition, this document must say so explicitly. Current known gaps: none.

## 3. Level 1 protocol target

### What this server is

A Healthy DNS is an **authoritative DNS server**: it holds the definitive answers for one or more configured DNS zones and answers queries about names within those zones. It does not perform recursive lookups, does not cache answers from other servers, and does not forward queries.

### Why this scope exists

The project needs DNS responses that recursive resolvers, monitoring tools, and operators can interpret correctly while keeping the product focused on health-aware authoritative answers. Level 1 therefore covers the minimum wire behavior needed for the supported product role: authoritative UDP answers for configured zones, correct negative responses, and predictable rejection of malformed or unsupported queries.

### What Level 1 covers

Level 1 covers the minimum behaviour required to be a correct authoritative UDP server for the core authoritative responses this project is built around: A, SOA, and NS, plus the negative-response semantics that make those answers wire-correct.

| Behaviour | Level 1 target |
|---|---|
| Query is for a name **outside** all hosted or alias zones | Return **REFUSED** without the **AA** flag |
| Query is for a name **inside** a hosted or alias zone but the owner name does not exist | Return **NXDOMAIN** (name does not exist) with the **AA** flag |
| Owner name exists but the queried record type is absent | Return **NOERROR** with an empty answer section (a **NODATA** response) and the **AA** flag |
| Owner name is an empty non-terminal inside a hosted or alias zone | Return **NOERROR** with an empty answer section (a **NODATA** response) and the **AA** flag |
| NODATA or NXDOMAIN response | Include the matched zone apex **SOA** record in the authority section, with the negative-response TTL set to the minimum of the SOA RR TTL and `SOA.MINIMUM` |
| Query has malformed wire format with a recoverable DNS header (>= 12 bytes) | Return **FORMERR** without the **AA** flag |
| Query payload is shorter than the DNS header (< 12 bytes) | Drop without a DNS response and log the rejection |
| Incoming packet is a DNS response rather than a query (`QR=1`) | Drop the packet and log the rejection |
| Query uses an unsupported opcode, including obsolete **IQUERY** | Return **NOTIMP** without the **AA** flag |
| Query is not for the **IN** (Internet) class | Return **REFUSED** without the **AA** flag |
| Query is for an unsupported or unknown non-meta RR type at an existing owner name | Treat the type as absent data and return **NOERROR** with an empty answer section and the **AA** flag |
| Query is for `QTYPE=ANY` at an existing owner name or empty non-terminal | Return **NOERROR** with the **AA** flag and one synthesized **HINFO** RRset whose CPU field is `RFC8482` and whose OS field is empty; the HINFO TTL is the same value this server would use for the matched apex SOA in a negative response: `min(SOA TTL, SOA.MINIMUM)` |
| Query has more or fewer than exactly one question | Return **FORMERR** without the **AA** flag |
| Query contains supported, reserved, or unknown DNS request flags | Do not drop the query solely because those flags are present; apply the Level 1 response flag policy |
| UDP response would exceed the classic DNS UDP payload limit | Return a response no larger than **512 bytes** with the **TC** (truncated) flag set |
| DNS response wire encoding | Use DNS message serialization that applies standard name compression and leaves unused or unsupported DNS response header bits clear |
| DNS owner-name matching for hosted zones, alias zones, and zone nodes | Treat ASCII case differences as equivalent for lookup and authority decisions |
| SOA response | Publish an unsigned 32-bit SOA serial value |
| TTL-bearing responses | Publish TTL values consistently with the modern DNS TTL field definition for A, NS, SOA, and negative-response SOA authority RRsets |

### What Level 1 does not cover

- Recursive or iterative resolution
- Zone transfers (AXFR / IXFR), including RFC 5936 AXFR behavior
- EDNS(0) extension processing, including RFC 6891 OPT processing
- TCP transport, including RFC 7766 DNS-over-TCP requirements
- IPv6 (AAAA records)
- CNAME, DNAME, or other xNAME redirection-chain processing
- DNS Stateful Operations (DSO), including RFC 8490 session semantics
- Delegation referral and glue response construction, including RFC 9471 referral-glue behavior
- Full DNSSEC authoritative-server behavior, including EDNS(0)/DO processing, automatic inclusion of RRSIG RRsets with signed answers, DNSSEC negative-denial proofs, DNSSEC algorithm policy enforcement, and complete DNSKEY / NSEC / RRSIG query semantics, even though the current signing path publishes DNSKEY, NSEC, and RRSIG RRsets when DNSSEC is enabled

### Key term glossary

| Term | Meaning |
|---|---|
| **Authoritative** | The server holds the definitive records for a zone and sets the AA (Authoritative Answer) flag only on responses evaluated against a hosted or alias zone |
| **NXDOMAIN** | "Non-Existent Domain" — the queried name does not exist in the zone at all |
| **NODATA / NOERROR empty answer** | The queried name exists but has no records of the requested type; the response code is NOERROR (not an error) and the answer section is empty |
| **SOA in authority** | For negative responses (NXDOMAIN and NODATA) the server includes the matched hosted or alias zone's Start of Authority record in the authority section so that negative caching behaviour is well-defined. The authority SOA RRset TTL is the negative-cache TTL, not necessarily the stored apex SOA TTL |
| **Non-meta RR type** | An ordinary resource-record type query handled as data lookup when unsupported, such as `AAAA` or an unknown `TYPE####` data type under RFC 3597 and current DNS registry terminology. This excludes special operation or extension query types such as `ANY`, which has its own RFC 8482 policy in Level 1, and out-of-scope query types such as `AXFR`, `IXFR`, and `OPT`/EDNS(0). |
| **Level 1 response flag policy** | Responses set `QR`; preserve request `RD`; set `AA` only for authoritative in-zone responses; set `TC` only when UDP truncation occurs; and leave `RA`, `AD`, `CD`, and still-reserved header bits clear because recursion, DNSSEC signalling, and EDNS(0) are outside Level 1. |
| **REFUSED** | The server refuses to answer because the query is for a zone it does not serve |
| **FORMERR** | "Format Error" — the server cannot interpret the query because it is malformed |

---

## 4. RFC applicability and compliance summary

The table below identifies the smallest complete RFC set needed to judge the Level 1 protocol target. The project does not claim unqualified full-document compliance with these broad RFCs; it claims full coverage only when the status column says so.

Completeness is based on the declared behaviour in [Level 1 protocol target](#3-level-1-protocol-target) and the current RFC Editor update chains for the DNS base specifications and Level 1-dependent updates, especially RFC 1034, RFC 1035, RFC 2181, and RFC 2308. If an RFC defines behavior inside the Level 1 target, it must appear in this table with an implemented or gap status. RFCs that update the core DNS specifications only for lower-layer UDP/IP transport, TCP transport, EDNS(0), DNSSEC, zone transfer/update/notify, TSIG/TKEY/SIG(0), DSO/sessionful DNS, xNAME redirection, referral glue, resolver/cache behavior, terminology, IANA registry allocation procedures, experimental record types, or record families outside A/SOA/NS are not listed in the main table because those behaviours are outside Level 1.

| RFC | Applies to Level 1 because it defines | Current Level 1 status | Broader material not claimed |
|---|---|---|---|
| [RFC 1034](https://www.rfc-editor.org/rfc/rfc1034) | Authoritative server model, zone concept, NXDOMAIN, and NOERROR/NODATA semantics | **Fully covered for Level 1** | Recursive resolution, resolver algorithms, referrals, and delegation behavior outside this server's scope |
| [RFC 1035](https://www.rfc-editor.org/rfc/rfc1035) | DNS message wire format, header flags, QDCOUNT, opcode field, response codes, UDP payload limit, TC flag, and response serialization | **Fully covered for Level 1** | TCP transport, zone transfers, EDNS(0) payload negotiation, unsupported classes, and record families beyond the declared response scope |
| [RFC 1123](https://www.rfc-editor.org/rfc/rfc1123) | DNS host requirements for UDP query service, response compression, and DNS response header correctness | **Fully covered for Level 1** | TCP service, resolver behavior, arbitrary zone-file loading, broadcast/multicast DNS queries, and broad Internet host requirements |
| [RFC 1982](https://www.rfc-editor.org/rfc/rfc1982) | DNS SOA serial number space for the SOA responses this server publishes | **Fully covered for Level 1 publication semantics** | Secondary-server comparison arithmetic, serial-increment policy for zone transfers, and replication behavior |
| [RFC 2181](https://www.rfc-editor.org/rfc/rfc2181) | Clarifications for UDP reply routing, RRset handling, zone authority, AA flag behavior, SOA placement/MNAME, and TC flag behavior | **Fully covered for Level 1** | Clarifications for DNS behavior outside the supported authoritative UDP response set |
| [RFC 2308](https://www.rfc-editor.org/rfc/rfc2308) | NXDOMAIN and NODATA authority-section SOA requirements and negative-response TTL handling | **Fully covered for Level 1** | Referral response details and server-side negative caching |
| [RFC 3425](https://www.rfc-editor.org/rfc/rfc3425) | IQUERY obsolescence and NOTIMP handling for IQUERY requests | **Fully covered for Level 1** | Historical inverse-query semantics, which are obsolete and not implemented |
| [RFC 3597](https://www.rfc-editor.org/rfc/rfc3597) | Unknown DNS RR type handling for ordinary non-meta `TYPE####` queries | **Fully covered for Level 1** | Loading, storing, transferring, and serving arbitrary unknown RR data; unknown-RR RDATA preservation; master-file generic RDATA syntax; and DNSSEC canonical-form details |
| [RFC 4343](https://www.rfc-editor.org/rfc/rfc4343) | Case-insensitive DNS name matching for authoritative lookup and zone matching | **Fully covered for Level 1** | Internationalized Domain Name handling and output-case preservation choices outside the lookup-result correctness requirement |
| [RFC 4592](https://www.rfc-editor.org/rfc/rfc4592) | DNS owner-name existence rules, including empty non-terminals | **Fully covered for Level 1** | Wildcard synthesis and wildcard-specific RRset behavior |
| [RFC 8482](https://www.rfc-editor.org/rfc/rfc8482) | Minimal-sized responses for `QTYPE=ANY` queries at existing IN-class names | **Fully covered for Level 1** | DNSSEC-specific RRSIG inclusion for signed synthesized or selected answers; EDNS(0)/DO signaling remains outside Level 1 |
| [RFC 8020](https://www.rfc-editor.org/rfc/rfc8020) | NXDOMAIN semantics and the required NODATA response for empty non-terminals | **Fully covered for Level 1** | Recursive resolver NXDOMAIN-cut caching behavior and DNSSEC proof reuse |
| [RFC 8767](https://www.rfc-editor.org/rfc/rfc8767) | Updated DNS TTL definition for TTL-bearing authoritative responses | **Fully covered for Level 1** | Recursive resolver serve-stale behavior, stale-answer timers, and cache-refresh semantics |
| [RFC 8906](https://www.rfc-editor.org/rfc/rfc8906) | Best Current Practice for responding to basic DNS queries, unknown or unsupported RR types, DNS request flags, and unknown opcodes | **Fully covered for Level 1** | TCP, EDNS, firewalls, packet scrubbers, whole-answer caches, remediation procedures, and operator testing guidance |
| [RFC 9619](https://www.rfc-editor.org/rfc/rfc9619) | Standard-query `QDCOUNT > 1` validation and required FORMERR response | **Fully covered for Level 1** | Non-standard operation modes outside this server's query-handling target |

### Level 1 RFC selection audit

The current main table covers every RFC that defines behavior in the Level 1 target:

- core DNS authority and wire behavior: RFC 1034, RFC 1035, RFC 1123, RFC 2181, RFC 2308, and RFC 9619
- Level 1-specific updates for serials, opcodes, unknown types, case, name existence, `QTYPE=ANY` minimization, TTLs, and robustness: RFC 1982, RFC 3425, RFC 3597, RFC 4343, RFC 4592, RFC 8020, RFC 8482, RFC 8767, and RFC 8906

The following commonly adjacent RFC areas were reviewed but are not Level 1 conformance dependencies under the current target:

| RFC area | Examples | Why not Level 1 |
|---|---|---|
| TCP transport | RFC 7766, RFC 5966 | Level 1 is explicitly UDP-only. Oversized UDP answers set `TC`, but TCP retry/service is outside the target. |
| EDNS(0) and OPT processing | RFC 6891 | Level 1 uses the classic 512-byte UDP payload limit and does not negotiate EDNS payload size, extended RCODEs, or EDNS options. |
| Zone transfers, update, and notify | RFC 1995, RFC 1996, RFC 2136, RFC 5936 | The server does not implement AXFR, IXFR, dynamic update, notify, secondary replication, or transfer-specific compression behavior. |
| DNS registry taxonomy | RFC 6895 | Useful vocabulary for distinguishing data TYPEs, QTYPEs, and Meta-TYPEs, but it does not add an independent Level 1 response-correctness requirement. |
| DNS Stateful Operations | RFC 8490 | Level 1 is UDP-only and does not establish stateful DNS sessions. The DSO opcode is outside the Level 1 product target; generic unsupported-opcode response robustness is assessed under RFC 8906. |
| xNAME redirection and redirection-chain status | RFC 6604, RFC 6672 | Level 1 does not publish CNAME or DNAME data, synthesize CNAMEs, or follow redirection chains. RCODE and AA rules specific to xNAME chains therefore do not add a Level 1 requirement. |
| Referral glue | RFC 9471 | Level 1 does not serve delegation referrals or referral glue. It serves authoritative answers for hosted and alias zones only. |
| Resolver/cache-only behavior | RFC 5452, RFC 9520 | The server is authoritative-only and does not send resolver queries, cache upstream answers, or cache resolution failures. |
| DNS terminology-only updates | RFC 9499 | Terminology helps describe DNS concepts but does not add an independent Level 1 implementation requirement. |
| DNSSEC protocol behavior | RFC 4033, RFC 4034, RFC 4035, RFC 6840, RFC 9364, RFC 9904 | Optional signing can publish DNSSEC artifacts, but full DNSSEC authoritative-server behavior is outside Level 1. See [Out-of-scope but related RFCs](#7-out-of-scope-but-related-rfcs). |

---

## 5. Detailed RFC coverage

The assessments below map each applicable RFC to the implementation behavior that satisfies it or to the gap that prevents a full-coverage claim.

---

### 5.1 RFC 1034 — Domain Names: Concepts and Facilities

RFC 1034 — https://www.rfc-editor.org/rfc/rfc1034 defines zones, authoritative name-server behavior, standard-query processing, authoritative name errors, and example NOERROR/NODATA and NXDOMAIN responses.

| Behaviour | Status | Notes |
|---|---|---|
| Authoritative Answer (AA) flag set only for hosted-zone responses | **Implemented** | `_update_response()` in `indisoluble/a_healthy_dns/dns_server_udp_handler.py` sets `dns.flags.AA` only after `ZoneOrigins.relativize()` confirms the query name belongs to a hosted or alias zone. `DnsServerUdpHandler.handle()` rejects malformed packets, inbound response packets, unsupported opcodes, invalid question counts, and unsupported classes before `_update_response()` can set AA. |
| REFUSED for queries outside all served zones | **Implemented** | `_update_response()` returns `dns.rcode.REFUSED` without AA when `ZoneOrigins.relativize()` returns `None` for a query name outside every hosted or alias zone. |
| NXDOMAIN when owner name is absent from an in-zone query | **Implemented** | `_update_response()` sets AA after the zone match, reads `txn.get_node(relative_name)`, and sets `dns.rcode.NXDOMAIN` when that owner node is absent. |
| NOERROR when owner name exists and matching records are found | **Implemented** | `_update_response()` keeps the default NOERROR for in-zone queries, reads the owner node and requested rdataset, then uses `_build_answer()` to populate the answer section. |
| SOA in authority for NXDOMAIN responses (RFC 2308 §3) | **Implemented** | The NXDOMAIN branch in `_update_response()` builds authority with `_build_authority_with_apex_soa()` using the matched hosted or alias zone apex and appends the returned RRsets to `response.authority`. |
| SOA in authority for NODATA responses (RFC 2308 §2.1) | **Implemented** | The NODATA branch in `_update_response()` builds authority with `_build_authority_with_apex_soa()` using the matched hosted or alias zone apex and appends the returned RRsets to `response.authority`. |

---

### 5.2 RFC 1035 — Domain Names: Implementation and Specification

RFC 1035 — https://www.rfc-editor.org/rfc/rfc1035: wire format (header §4.1.1 including QDCOUNT and OPCODE, question §4.1.2, answer/authority §4.1.3) and response codes (FORMERR, NOTIMP).

| Behaviour | Status | Notes |
|---|---|---|
| Wire parsing of incoming queries | **Implemented** | `dns.message.from_wire()` is used; `dns.exception.DNSException` is caught |
| FORMERR when wire parsing fails | **Implemented** | When `dns.message.from_wire()` raises a `DNSException` other than `ShortHeader` (DNS header readable), the handler extracts the transaction ID from bytes 0-1 and responds with FORMERR. That minimal parse-failure response sets QR, preserves the ID, preserves the request opcode and RD bit from the header, and does not set AA because no authoritative question is available. When `ShortHeader` is raised (payload < 12 bytes), the packet is dropped without a DNS response. See the note below for details. |
| DNS response packet rejection | **Implemented** | Packets with a readable DNS header and the `QR` response flag set are not queries; the handler logs the rejection and drops the packet before parsing, so both well-formed and malformed response packets are ignored. |
| Opcode validation — NOTIMP for non-QUERY opcodes | **Implemented** | `DnsServerUdpHandler.handle()` checks `query.opcode() != dns.opcode.QUERY` and returns `dns.rcode.NOTIMP` without AA. Tested with STATUS (opcode 2), NOTIFY (opcode 4), and valid UPDATE messages (opcode 5). Standard-query-shaped packets with opcode UPDATE are malformed and are rejected by dnspython's wire parser before this check is reached. |
| QDCOUNT validation — FORMERR for ≠ 1 question | **Implemented** | `DnsServerUdpHandler.handle()` checks `len(query.question) != 1`; zero or more-than-one questions return `dns.rcode.FORMERR` without AA. Confirmed: dnspython preserves all questions for QDCOUNT > 1 wire messages. See also RFC 9619 below. |
| QCLASS / IN class validation | **Implemented** | `DnsServerUdpHandler.handle()` checks `question.rdclass != dns.rdataclass.IN`; non-IN queries return `dns.rcode.REFUSED` without AA. Project decision: REFUSED because the server exclusively serves IN-class data. |
| Wire serialisation of responses | **Implemented** | `response.to_wire()` is called before every `sendto()` |
| UDP response truncation | **Implemented** | `_response_to_udp_wire()` serializes every UDP response with a 512-byte classic DNS payload limit and `prefer_truncation=True`, so oversized responses set TC and stay within RFC 1035 UDP size constraints. EDNS(0) payload negotiation remains outside Level 1. |
| A, SOA, NS record types in responses | **Implemented** | All three record types are populated by the zone updater |

Note on malformed-wire inputs: replying requires the DNS transaction ID (bytes 0-1, RFC 1035 §4.1.1). Payloads shorter than 12 bytes raise `dns.message.ShortHeader` and are dropped without a DNS response, with an `info`-level `dns_traffic=junk` log for operator visibility. Packets with a readable header and `QR=1` are dropped as inbound response packets. Any other `dns.exception.DNSException` subclass (`FormError`, `BadPointer`, etc.) means the header was readable; the server replies with FORMERR using the extracted transaction ID and header opcode/RD bits. These paths are confirmed by unit tests in `test_dns_server_udp_handler.py` and by `TestMalformedWireInput` in the component integration tests.

---

### 5.3 RFC 1123 — Requirements for Internet Hosts — Application and Support

RFC 1123 — https://www.rfc-editor.org/rfc/rfc1123: supplements the DNS base specifications with host requirements. For Level 1, only the DNS name-server requirements that affect the declared authoritative UDP response path apply.

| Behaviour | Status | Notes |
|---|---|---|
| DNS server services UDP queries | **Implemented** | The runtime uses `socketserver.UDPServer`, and component integration tests exercise positive, negative, malformed, and rejected DNS queries over real UDP sockets. |
| DNS responses use standard name compression | **Implemented** | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` inspects response wire bytes and confirms DNS name compression pointers are used when repeated names are present. |
| Unused or unsupported DNS response header bits remain clear | **Implemented** | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` inspects response wire header flags and asserts Level 1-unused bits remain clear (`RA`, `AD`, `CD`, and reserved bits). |
| TCP query service and TCP retry after truncation | **Out of Level 1 scope** | RFC 1123 recommends TCP service for DNS servers, and later DNS transport RFCs strengthen TCP requirements. Level 1 deliberately remains UDP-only and signals oversized UDP answers with `TC`. |
| Zero-TTL record handling | **Out of Level 1 scope** | Level 1 generated records use TTLs derived from positive health-check timing configuration; the server does not load arbitrary zone data containing zero-TTL records. |
| DNS software extensibility and arbitrary RR type loading | **Out of Level 1 scope** | Level 1 is restricted to generated A, SOA, and NS responses. The server does not implement arbitrary master-file loading or transparent support for every RR type. |
| Resolver behavior, root hints, and broadcast/multicast DNS queries | **Out of Level 1 scope** | The server is authoritative-only, does not implement recursive resolution or cache management, and does not issue resolver queries. |

No remaining Level 1 gaps in RFC 1123 coverage.

---

### 5.4 RFC 3425 — Obsoleting IQUERY

RFC 3425 — https://www.rfc-editor.org/rfc/rfc3425: updates RFC 1035 by making opcode 1 obsolete and saying name servers should return NOTIMP when an IQUERY request is received. For Level 1, the applicable behavior is rejection of IQUERY as an unsupported opcode.

| Behaviour | Status | Notes |
|---|---|---|
| IQUERY requests return NOTIMP | **Implemented** | `DnsServerUdpHandler.handle()` returns `dns.rcode.NOTIMP` without AA for every parsed non-QUERY opcode. Unit tests exercise opcode 1 (IQUERY) directly, as well as other unsupported opcodes. |
| Historical inverse-query lookup semantics | **Out of Level 1 scope** | IQUERY is obsolete and is intentionally not implemented. |

No remaining Level 1 gaps in RFC 3425 coverage.

---

### 5.5 RFC 3597 — Handling of Unknown DNS Resource Record (RR) Types

RFC 3597 — https://www.rfc-editor.org/rfc/rfc3597: defines how DNS implementations handle RR types whose RDATA format they do not understand. For Level 1, the applicable behavior is limited to query-response robustness for ordinary unknown non-meta data types. The project does not load arbitrary master files, receive zone transfers, or serve unknown RR data.

| Behaviour | Status | Notes |
|---|---|---|
| Unknown numeric non-meta RR type query at an existing owner name receives a normal NODATA response | **Implemented** | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` sends an unknown numeric `TYPE####` query for an existing owner name and asserts a normal NOERROR/empty-answer response with SOA authority. |
| Unknown numeric non-meta RR type query at an absent in-zone owner name receives NXDOMAIN | **Implemented** | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` sends an unknown numeric `TYPE####` query for an absent in-zone owner name and asserts NXDOMAIN with SOA authority. |
| Transparent loading, storage, transfer, and serving of unknown RR data | **Out of Level 1 scope** | Level 1 generates A, NS, and SOA records only, plus optional DNSSEC artifacts when signing is enabled. The server does not load arbitrary zone files, accept zone transfers, or publish unknown-RR RDATA. |
| Generic master-file representation and DNSSEC canonical form for unknown RR data | **Out of Level 1 scope** | These requirements apply to arbitrary unknown RR data handling, which is not a Level 1 product capability. |

No remaining Level 1 gaps in RFC 3597 coverage.

---

### 5.6 RFC 2181 — Clarifications to the DNS Specification

RFC 2181 — https://www.rfc-editor.org/rfc/rfc2181: §6.1 clarifies zone authority and says a server for one zone should not return authoritative answers for names in another zone.

| Behaviour | Status | Notes |
|---|---|---|
| UDP replies are routed back to the query source | **Implemented** | `DnsServerUdpHandler.handle()` sends every response with `sock.sendto(..., self.client_address)`, preserving the client source address and source port as the response destination. Runtime integration tests exercise the response path over real UDP sockets. |
| UDP replies are sent from the listening DNS socket | **Implemented** | The handler uses the `socketserver.UDPServer` socket that received the query, so replies are sent from the bound server address and port. |
| Complete RRset response construction | **Implemented** | `_build_answer()` emits one response RRset for the requested owner/class/type and adds every RDATA item from the zone rdataset with one TTL. Oversized RRsets are serialized through `_response_to_udp_wire()` with `prefer_truncation=True`, so `TC` is set when a full required answer cannot fit. |
| AA flag set correctly | **Implemented** | Responses that are evaluated against a hosted or alias zone set AA. Rejections where no authoritative zone answer is evaluated, including malformed queries, unsupported opcodes, invalid question counts, unsupported classes, and out-of-zone names, do not set AA. |
| SOA placement in authoritative negative responses | **Implemented** | Negative responses place the matched apex SOA in the authority section, not the additional section. |
| SOA `MNAME` identifies the configured primary name server | **Implemented** | `iter_soa_record()` receives `config.primary_name_server`, derived from the first configured nameserver, and emits it as the SOA primary nameserver. |
| TC flag behavior for oversized UDP answers | **Implemented** | `_response_to_udp_wire()` serializes with the classic 512-byte UDP limit and `prefer_truncation=True`; oversized-answer tests assert the wire response is no larger than 512 bytes and has `TC` set. |
| Cache ranking and received-RRset merging rules | **Out of Level 1 scope** | The server is authoritative-only, does not cache upstream answers, and does not merge received DNS data into served zone data. |
| CNAME, DNSSEC-specific RRset special cases, and arbitrary-label policy | **Out of Level 1 scope** | Level 1 serves generated A, SOA, and NS responses only. DNSSEC artifact publication is treated separately and is not a Level 1 conformance target. |
| NS target canonicality and addressability | **Out of Level 1 scope** | RFC 2181 says NS targets must not be aliases and must have address records. This server publishes configured NS owner data but does not resolve or validate whether external nameserver hostnames are aliases; that is operator-owned zone-delegation correctness, not Level 1 UDP response behavior. |

No remaining Level 1 gaps in RFC 2181 coverage.

---

### 5.7 RFC 1982 — Serial Number Arithmetic

RFC 1982 — https://www.rfc-editor.org/rfc/rfc1982: updates RFC 1034 and RFC 1035 by defining serial number arithmetic for DNS SOA serial numbers. For Level 1, the applicable behavior is publication of an SOA serial in the 32-bit unsigned DNS SOA serial number space.

| Behaviour | Status | Notes |
|---|---|---|
| SOA serial is an unsigned 32-bit value | **Implemented** | `uint32_current_time()` returns the current Unix timestamp as an integer and raises `OverflowError` if it exceeds `2^32 - 1`; `iter_soa_record()` uses that value as the SOA serial. |
| Consecutive generated SOA serials do not repeat within the same process | **Implemented** | `_iter_soa_serial()` waits for the timestamp to change when a duplicate timestamp would be emitted. |
| Serial-number comparison and secondary-transfer arithmetic | **Out of Level 1 scope** | The server does not implement secondary-server behavior, AXFR/IXFR, or SOA serial comparison against another zone copy. |

No remaining Level 1 gaps in RFC 1982 coverage.

---

### 5.8 RFC 4343 — DNS Case Insensitivity Clarification

RFC 4343 — https://www.rfc-editor.org/rfc/rfc4343: updates RFC 1034, RFC 1035, and RFC 2181 by clarifying that ASCII DNS label matching is case-insensitive while output case may be preserved or normalized without changing RRset completeness.

| Behaviour | Status | Notes |
|---|---|---|
| Case-insensitive hosted-zone and alias-zone matching | **Implemented** | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` exercises mixed-case queries for primary-zone and alias-zone names and asserts they are treated as in-zone (AA set, expected response code). |
| Case-insensitive owner-node lookup | **Implemented** | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` exercises mixed-case queries for existing owner names and asserts they retrieve the same A answers and NODATA semantics as lowercase queries. |
| Output case preservation | **Out of Level 1 scope** | Level 1 requires lookup-result correctness and RRset completeness, not a specific output capitalization policy. RFC 4343 permits multiple output-case choices as long as retrieval is case-insensitive. |

No remaining Level 1 gaps in RFC 4343 coverage.

---

### 5.9 RFC 4592 — The Role of Wildcards in the Domain Name System

RFC 4592 — https://www.rfc-editor.org/rfc/rfc4592: updates RFC 1034 by refining DNS name-existence rules. For Level 1, the applicable material is not wildcard synthesis; it is the definition that a node exists when it owns at least one RRset or has descendants that own RRsets. That makes empty non-terminals existing names.

| Behaviour | Status | Notes |
|---|---|---|
| Exact owner names with RRsets exist | **Implemented** | `_update_response()` treats a zone node returned by `txn.get_node(relative_name)` as an existing owner name and returns either an answer or NODATA depending on whether the requested rdataset exists. |
| Empty non-terminal owner names exist and return NODATA | **Implemented** | `_update_response()` treats a missing node as an empty non-terminal when `txn.iterate_names()` contains a descendant name, and returns NOERROR/empty-answer with SOA authority. Coverage: `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` and `tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py`. |
| Wildcard synthesis | **Out of Level 1 scope** | The configuration validator does not support wildcard labels, and Level 1 does not claim wildcard behavior. |

No remaining Level 1 gaps in RFC 4592 empty non-terminal coverage.

---

### 5.10 RFC 8020 — NXDOMAIN: There Really Is Nothing Underneath

RFC 8020 — https://www.rfc-editor.org/rfc/rfc8020: updates RFC 1034 and RFC 2308 by clarifying that NXDOMAIN means the queried name and its descendants do not exist, and that empty non-terminals must receive NODATA.

| Behaviour | Status | Notes |
|---|---|---|
| NXDOMAIN only when the queried owner name and its subtree do not exist | **Implemented** | `_update_response()` checks for an empty non-terminal (a missing owner node with existing descendants) before returning NXDOMAIN, so NXDOMAIN is reserved for names with no node and no descendant nodes in the served zone view. |
| Empty non-terminal receives NODATA | **Implemented** | Missing owner nodes with descendants receive NOERROR/empty-answer with the matched zone apex SOA in authority (RFC 2308). Coverage: `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` and `tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py`. |
| Resolver NXDOMAIN-cut caching behavior | **Out of Level 1 scope** | The server is authoritative-only and does not implement recursive resolver caching. |

No remaining Level 1 gaps in RFC 8020 empty non-terminal coverage.

---

### 5.11 RFC 8767 — Serving Stale Data to Improve DNS Resiliency

RFC 8767 — https://www.rfc-editor.org/rfc/rfc8767: defines recursive resolver serve-stale behavior and updates the DNS TTL definition used by RFC 1035 and RFC 2181. For Level 1, only the updated TTL definition for TTL-bearing authoritative responses applies.

| Behaviour | Status | Notes |
|---|---|---|
| A, NS, SOA, and negative-response SOA authority RRsets carry TTL values | **Implemented** | All generated TTLs are clamped to the RFC 8767 updated TTL definition range: `0 <= TTL <= 2^31-1`. TTL calculator helpers in `records/time.py` are decorated to clamp their outputs, and negative-response SOA authority TTL is computed as `min(SOA TTL, SOA.MINIMUM)` from those clamped values. |
| Recursive resolver serve-stale behavior and stale-cache timers | **Out of Level 1 scope** | The server is authoritative-only and does not cache resolver data or serve stale resolver answers. |

No remaining Level 1 gaps in RFC 8767 TTL definition coverage.

---

### 5.12 RFC 8906 — A Common Operational Problem in DNS Servers: Failure to Communicate

RFC 8906 — https://www.rfc-editor.org/rfc/rfc8906: documents Best Current Practice for avoiding DNS server non-response or incorrect response structure. For Level 1, the applicable material is the Basic DNS guidance for zone-existence queries, unknown or unsupported RR types, DNS request flags, recursive queries sent to non-recursive servers, and unknown opcodes.

| Behaviour | Status | Notes |
|---|---|---|
| SOA query for a served zone receives an SOA answer | **Implemented** | Positive SOA queries for the hosted apex return NOERROR with the apex SOA in the answer section. |
| Unsupported known RR type at an existing owner name receives NODATA | **Implemented** | Existing tests query AAAA at an owner name that exists with A data and assert NOERROR with an empty answer and SOA authority. |
| Unknown numeric RR type receives a normal DNS response instead of being dropped | **Implemented** | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` sends an unknown numeric `TYPE####` query and asserts the response is NODATA (existing owner) or NXDOMAIN (absent owner), with SOA authority. |
| DNS queries with request flags set receive a response and unsupported response header bits are not copied | **Implemented** | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` asserts RD is preserved and RA/AD/CD/Z are clear in NOERROR and NOTIMP responses; `tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py` asserts FORMERR header recovery preserves only opcode and RD. |
| Unknown or unimplemented opcodes return NOTIMP | **Implemented** | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py` and `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` cover IQUERY, STATUS, NOTIFY, UPDATE, and an unassigned opcode value, all returning NOTIMP without AA. |
| TCP and EDNS response robustness | **Out of Level 1 scope** | Level 1 is UDP-only and deliberately does not implement EDNS(0). |
| Firewall, packet scrubber, whole-answer cache, remediation, and operator testing guidance | **Out of Level 1 scope** | These are operational deployment and ecosystem testing topics, not in-process authoritative UDP response semantics. |

No remaining Level 1 gaps in RFC 8906 basic DNS response robustness coverage.

---

### 5.13 RFC 8482 — Providing Minimal-Sized Responses to DNS Queries that have QTYPE=ANY

RFC 8482 — https://www.rfc-editor.org/rfc/rfc8482: allows authoritative responders to avoid returning all RRsets for `QTYPE=ANY` queries and instead return a minimal response. For Level 1, the implemented policy is a synthesized HINFO answer for existing IN-class QNAMEs. DNSSEC-specific handling for signed responses is deliberately outside Level 1.

| Behaviour | Status | Notes |
|---|---|---|
| Existing owner name queried with `QTYPE=ANY` receives synthesized HINFO | **Implemented** | `_update_response()` detects `dns.rdatatype.ANY` after zone matching and returns one HINFO RRset whose CPU field is `RFC8482` and whose OS field is empty. The answer owner name is the queried hosted-zone or alias-zone name, and no SOA authority is added because this is a positive RFC 8482 minimization response. |
| Empty non-terminal queried with `QTYPE=ANY` receives synthesized HINFO | **Implemented** | Empty non-terminals are existing QNAMEs under RFC 4592. The `ANY` path therefore returns synthesized HINFO for them, while non-ANY queries at empty non-terminals continue to return NODATA with SOA authority under RFC 8020 and RFC 2308. |
| Absent owner name queried with `QTYPE=ANY` remains NXDOMAIN | **Implemented** | RFC 8482 handling is limited to existing QNAMEs. Absent in-zone owner names continue through the normal NXDOMAIN branch with SOA authority. |
| HINFO TTL reuses the apex SOA TTL calculation | **Implemented** | `_build_rfc8482_hinfo_answer()` reads the same apex SOA data and uses the shared `_build_apex_soa()` helper, so synthesized HINFO uses `min(SOA TTL, SOA.MINIMUM)` without building an authority RRset or adding a second TTL source of truth. Operators influence this value through the existing SOA timing inputs described in [`docs/architecture.md`](architecture.md#6-interval-calculation-pattern). |
| DNSSEC-specific `ANY` response behavior | **Out of Level 1 scope** | Signed-zone RRSIG inclusion, EDNS(0), and DO-bit processing remain part of the broader DNSSEC scope that this document does not claim. |

Future scope note: if CNAME publication is added later, RFC 8482 synthesized HINFO handling must be revisited because Section 4.2 only applies when there is no CNAME present at the owner name matching the QNAME.

No remaining Level 1 gaps in RFC 8482 minimized-response coverage.

---

### 5.14 RFC 9619 — In the DNS, QDCOUNT Is (Usually) One

RFC 9619 — https://www.rfc-editor.org/rfc/rfc9619: updates RFC 1035 by forbidding standard-query (`OPCODE=0`) messages with `QDCOUNT > 1` and requiring `FORMERR` for those messages.

| Behaviour | Status | Notes |
|---|---|---|
| FORMERR for QDCOUNT > 1 | **Implemented** | `DnsServerUdpHandler.handle()` returns `dns.rcode.FORMERR` without AA for multi-question standard queries. |
| FORMERR for QDCOUNT = 0 | **Project Level 1 policy** | A standard query with no question cannot be evaluated against a hosted zone, so the handler returns `dns.rcode.FORMERR` without AA. |

No remaining Level 1 gaps in RFC 9619 coverage.

---

### 5.15 RFC 2308 — Negative Caching of DNS Queries

RFC 2308 — https://www.rfc-editor.org/rfc/rfc2308: NXDOMAIN (§3) and NODATA/NOERROR (§2.1) responses must include the matched zone apex SOA in the authority section for correct negative caching. §5 defines the negative-response TTL as the minimum of the SOA RR TTL and `SOA.MINIMUM`; `SOA.MINIMUM` is populated here via `calculate_soa_min_ttl()` in `records/time.py`, and the emitted authority SOA RRset TTL is trimmed in the UDP handler.

| Behaviour | Status | Notes |
|---|---|---|
| SOA record with correct `MINIMUM` field exists in zone | **Implemented** | `soa_record.py` populates the minimum TTL from `calculate_soa_min_ttl()` |
| SOA in authority section for NXDOMAIN (RFC 2308 §3) | **Implemented** | `_build_authority_with_apex_soa()` in `indisoluble/a_healthy_dns/dns_server_udp_handler.py` retrieves the apex SOA data and returns an authority RRset named at the matched hosted or alias zone apex; `_update_response()` appends that list to `response.authority`. |
| Negative-response SOA RRset TTL uses `min(SOA TTL, SOA.MINIMUM)` (RFC 2308 §5) | **Implemented** | `_build_authority_with_apex_soa()` sets the emitted authority SOA RRset TTL to the lower of the stored SOA rdataset TTL and the SOA RDATA `minimum` value |
| SOA in authority section for NODATA (RFC 2308 §2.1) | **Implemented** | Same helper populates the authority section for NOERROR/empty-answer responses using the matched hosted or alias zone apex |

No remaining Level 1 gaps in RFC 2308 coverage.

---

## 6. Test coverage mapping

| Behaviour | Test location |
|---|---|
| Positive A/SOA/NS responses (NOERROR) | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` (component integration) |
| NXDOMAIN with SOA in authority, including alias-zone authority owner | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` (component integration) |
| NODATA with SOA in authority, including alias-zone authority owner | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` (component integration) |
| Empty non-terminal NODATA for nested configured names | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` (component integration) |
| Out-of-zone REFUSED | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` (component integration) |
| Non-IN-class REFUSED | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` (component integration) |
| Unsupported known RR type NODATA at existing owner names | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` (component integration) |
| Unknown numeric non-meta RR type response robustness | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` (component integration) |
| RFC 8482 `QTYPE=ANY` synthesized HINFO responses for existing owner names and empty non-terminals | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` (component integration) + `tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py` (unit) |
| SOA serial generation uses an unsigned 32-bit value and avoids duplicate consecutive values | `tests/indisoluble/a_healthy_dns/records/test_soa_record.py` (unit) + `tests/indisoluble/a_healthy_dns/tools/test_uint32_current_time.py` (unit) |
| NOTIMP for unsupported opcodes | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` (component integration) + `tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py` (unit) |
| NOTIMP for obsolete IQUERY opcode | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py` (unit) |
| NOTIMP for unassigned opcode values | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` (component integration) + `tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py` (unit) |
| FORMERR for QDCOUNT ≠ 1 (wire-level) | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` (component integration) |
| FORMERR for malformed wire with recoverable header (≥ 12 bytes) | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` (component integration) + `tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py` (unit) |
| Drop and log inbound DNS response packets (`QR=1`) | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py` (unit) |
| Drop without response for malformed wire shorter than 12 bytes | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py` (unit — no transaction ID to reply to) |
| Negative-response SOA TTL is trimmed for RFC 2308 negative caching | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py` (unit) + `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` (component integration) |
| RFC 8767 TTL cap/range policy for generated TTL-bearing responses | `tests/indisoluble/a_healthy_dns/records/test_a_record.py` (unit) + `tests/indisoluble/a_healthy_dns/records/test_ns_record.py` (unit) + `tests/indisoluble/a_healthy_dns/records/test_soa_record.py` (unit) |
| UDP response send path uses the query source address and port | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` (component integration over real UDP sockets) + `tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py` (unit handler send path) |
| RRset construction from zone rdatasets and oversized RRset truncation | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py` (unit) + `tests/indisoluble/a_healthy_dns/records/test_a_record.py` (unit) |
| Oversized UDP responses are truncated to the classic 512-byte limit and set TC | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py` (unit) |
| Parsed response header fields (QR, ID, AA, RA, TC), including non-AA rejected responses | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` (component integration) |
| DNS request-flag robustness for `AD`, `CD`, and still-reserved flags | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` (component integration; wire-byte assertions) |
| Raw response name compression and unsupported response header bits | `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py` (component integration; wire-byte assertions) |
| Health-check-driven A-record addition/removal | `.github/workflows/test-integration.yml` (Docker end-to-end) |
| Container startup, Docker networking, alias zone routing | `.github/workflows/test-integration.yml` (Docker end-to-end) |

## 7. Out-of-scope but related RFCs

The RFCs below are not necessary to prove Level 1 conformance. They are listed because the product has optional DNSSEC artifact publication and the project intends to keep future DNSSEC compatibility work aligned with the relevant standards.

When DNSSEC is enabled, `DnsServerZoneUpdater._sign_zone()` delegates to `dns.dnssec.sign_zone()`, and unit tests in `tests/indisoluble/a_healthy_dns/test_dns_server_zone_updater.py` confirm that generated DNSKEY, NSEC, and RRSIG rdatasets exist for signed zones. That is artifact-presence coverage only; it is not a claim of full DNSSEC authoritative-server conformance.

| RFC | Related because it defines | Current repository status |
|---|---|---|
| [RFC 9364](https://www.rfc-editor.org/rfc/rfc9364) | DNSSEC core-document overview and current DNSSEC terminology context | Related background only; not part of Level 1 |
| [RFC 4033](https://www.rfc-editor.org/rfc/rfc4033) | DNSSEC services and requirements for signed DNS data | Related background only; full DNSSEC services are not implemented |
| [RFC 4034](https://www.rfc-editor.org/rfc/rfc4034) | DNSKEY, RRSIG, NSEC, and DS resource-record definitions | Partially touched by generated artifacts; RR format and signature correctness are delegated to `dnspython` and not independently covered |
| [RFC 4035](https://www.rfc-editor.org/rfc/rfc4035) | DNSSEC protocol behavior for serving signed zones, including RRSIG inclusion and authenticated denial | Not a Level 1 target; EDNS(0)/DO handling, signed-answer augmentation, and NSEC/RRSIG negative-denial responses are not implemented as conformance behavior |
| [RFC 6840](https://www.rfc-editor.org/rfc/rfc6840) | DNSSEC clarifications that update RFC 4033, RFC 4034, and RFC 4035 | Related background only; not part of Level 1 |
| [RFC 6891](https://www.rfc-editor.org/rfc/rfc6891) | EDNS(0), including larger UDP payloads and DNSSEC signalling support | Out of Level 1 and not implemented as a conformance target |
| [RFC 9904](https://www.rfc-editor.org/rfc/rfc9904) | Current DNSSEC cryptographic algorithm recommendation process and IANA-registry-based algorithm guidance | Out of Level 1; repository-owned DNSSEC algorithm policy is not enforced |

## 8. Coverage gaps

No remaining Level 1 gaps for the current protocol target.
