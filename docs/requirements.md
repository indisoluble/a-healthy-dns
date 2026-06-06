# Requirements

This document defines what **A Healthy DNS** must satisfy.

It is the canonical home for functional, operational, quality, compatibility, security, performance, reliability, and constraint requirements. Product scope lives in [`docs/project-brief.md`](project-brief.md); major decision rationale lives in [`docs/decisions.md`](decisions.md); architecture lives in [`docs/architecture.md`](architecture.md); configuration syntax lives in [`docs/configuration-reference.md`](configuration-reference.md); protocol conformance lives in [`docs/RFC-conformance.md`](RFC-conformance.md).

## Constraints

| Constraint | Requirement |
|---|---|
| Runtime target | Python 3.11+ |
| Network role | Authoritative DNS server for one hosted zone plus optional alias zones |
| Transport | UDP only |
| Record modes | Standard static IP entries and health-checked IP entries, both configurable within the same zone |
| Health check protocol | TCP connectivity checks against configured health-checked backend IPs and ports; standard static entries skip probing |
| Record scope | Base records: A, SOA, and NS; synthesized HINFO is returned for RFC 8482 `QTYPE=ANY` minimization using the matched apex SOA negative-response TTL but is not configured zone data; when DNSSEC is enabled, generated DNSKEY, NSEC, and RRSIG artifact data are also published without implying full DNSSEC authoritative-server behavior |
| Deployment modes | Direct CLI process and Docker container |
| Configuration model | Startup-time configuration only; live reload is not currently supported |

## Functional Requirements

- **R1** For each configured subdomain, maintain a list of backend IP addresses together with the publication mode that applies to them.
- **R2** Periodically test TCP connectivity to each configured `(ip, health_port)` pair for health-checked entries; standard static entries must not be probed and must remain publishable without a health check.
- **R3** Update the in-memory DNS zone when the publishable A-record set changes.
- **R4** Return only currently healthy health-checked IPs plus any configured standard static IPs in DNS A-record responses.
- **R5** When a configured subdomain has no currently publishable A records, follow the authoritative UDP name-existence semantics in [`docs/RFC-conformance.md`](RFC-conformance.md): return `NXDOMAIN` only when the owner name and its subtree are absent, and return `NODATA` for existing empty non-terminals.
- **R6** Support alias zones that resolve identically to the primary zone without separate record or health-check state.
- **R7** Derive DNS timing values from health-check parameters so DNS timing stays aligned with refresh behavior; [`docs/architecture.md`](architecture.md) owns the detailed formulas.
- **R8** When a DNSSEC private key is provided, sign the zone and publish generated DNSSEC artifact data alongside the base A, NS, and SOA data without requiring full DNSSEC authoritative-server behavior outside the protocol scope documented in [`docs/RFC-conformance.md`](RFC-conformance.md).

## Operational Requirements

- **R9** Accept startup configuration through CLI arguments. Docker deployments pass the same arguments as the container command.
- **R10** Validate startup configuration before serving traffic; invalid configuration must fail fast and exit non-zero.
- **R11** Provide log output at configurable verbosity levels.
- **R12** Start serving DNS queries without an external database or coordination service.
- **R13** Shut down cleanly on `SIGINT` and `SIGTERM`, including the background zone updater.

## Protocol Requirements

- **R14** Implement the authoritative UDP response semantics documented in [`docs/RFC-conformance.md`](RFC-conformance.md).
- **R15** Set the authoritative-answer flag on responses produced for supported authoritative queries.
- **R16** Return `REFUSED` for queries outside all configured zones and for unsupported DNS classes.
- **R17** Return `FORMERR` for malformed DNS messages when a response can be formed, and drop packets that are too short to recover a DNS transaction ID without a DNS response while logging the rejection for operator visibility.
- **R18** Return RFC 8482 minimized synthesized HINFO responses for `QTYPE=ANY` queries at existing in-zone owner names and empty non-terminals, while preserving standard NXDOMAIN behavior for absent owner names.

## Quality And Reliability Requirements

- **R19** Keep zone writes atomic by rebuilding the zone inside one `dns.versioned.Zone` writer transaction.
- **R20** Keep query handling read-only with respect to zone state.
- **R21** Cover behavior changes with the relevant automated tests described in [`docs/testing.md`](testing.md).
- **R22** Preserve deterministic behavior in tests by mocking real network and time dependencies outside component or Docker end-to-end scopes.

## Security And Deployment Requirements

- **R23** Keep DNSSEC private keys optional and loaded only when explicitly configured.
- **R24** The Docker image must run the application as the Chainguard default non-root uid `65532`. Standard DNS exposure on host port `53` must be achievable without running the application as root or modifying the image. Bridge-mode deployment guidance must publish host port `53` to a non-privileged listener port when the process does not need to bind container port `53`. When the DNS process itself must bind port `53`, the approved strategy is `net.ipv4.ip_unprivileged_port_start=53` in the network namespace where the DNS process binds. `NET_BIND_SERVICE` is supported only as a runtime-specific fallback when the sysctl cannot be set and the runtime grants the capability effectively to the non-root process.
- **R25** `/app/keys` remains the Docker mount point for DNSSEC private keys and should be mounted read-only by operators.
