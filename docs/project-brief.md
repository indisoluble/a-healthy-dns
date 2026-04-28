# Project Brief

This document defines the product scope and acceptance boundaries for **A Healthy DNS**.

It is the canonical home for goals, non-goals, constraints, and high-level requirements. Architecture and folder layout live in [`docs/system-patterns.md`](system-patterns.md); toolchain, dependency pins, QA workflow, and code conventions live in [`docs/project-rules.md`](project-rules.md); configuration syntax lives in [`docs/configuration-reference.md`](configuration-reference.md); protocol-level DNS behavior lives in [`docs/RFC-conformance.md`](RFC-conformance.md).

## What it is

**A Healthy DNS** is an authoritative DNS server that performs continuous TCP health checks on configured backend IP addresses and automatically updates DNS answers to reflect current backend health. It can also publish IPs that skip the health check (configured as a bare list). Healthy endpoints and bare-list entries are advertised after the updater refreshes the in-memory zone; unhealthy endpoints are withheld until they recover.

## Why it exists

Traditional authoritative DNS returns static records. When a backend becomes unavailable, DNS continues advertising it until an operator changes the zone. A Healthy DNS closes that gap by making the authoritative layer health-aware, providing automatic failover without an external control plane.

## Goals

1. **Automatic failover** — remove unhealthy IP addresses from DNS responses without manual intervention.
2. **Authoritative DNS** — serve one hosted zone plus any configured alias zones as an authoritative UDP DNS server.
3. **Multi-domain support** — let multiple domain aliases reuse the same records without duplicating health-check state.
4. **Optional DNSSEC** — sign the zone when a private key is provided and publish the generated DNSSEC artifacts alongside the base records.
5. **Configurable health checking** — allow operators to tune check interval, TCP timeout, and health port per health-checked subdomain.
6. **Operational simplicity** — run as a single Python process or Docker container with startup-time configuration only.

## Non-goals

- **Recursive resolution** — the server does not perform recursive lookups or act as a caching resolver.
- **Non-TCP health checks** — health is determined exclusively by TCP connectivity; ICMP, HTTP, and other protocols are out of scope.
- **Live configuration reload** — adding or removing subdomains or zones requires a restart.
- **Zone replication and transfers** — AXFR, IXFR, and multi-instance state replication are out of scope.
- **IPv6 answer support** — current implementation serves A records (IPv4) only.
- **Traffic-shaping policy** — weighted, geographic, or policy-based routing is out of scope.

## Constraints

| Constraint | Detail |
|---|---|
| Runtime target | Python 3.10+ |
| Network role | Authoritative DNS server for one hosted zone plus optional alias zones |
| Transport | UDP only |
| Health check protocol | TCP connectivity checks against configured backend IPs and ports; bare-list IP entries skip the health check |
| Record scope | Base records: A, SOA, and NS; when DNSSEC is enabled, generated DNSKEY, NSEC, and RRSIG data are also published |
| Deployment modes | Direct CLI process and Docker container |

## Key requirements

### Functional

- **R1** For each configured subdomain, maintain a list of backend IP addresses and their current health state.
- **R2** Periodically test TCP connectivity to each configured `(ip, health_port)` pair; entries without a health port are not probed and are treated as healthy by updater refreshes.
- **R3** Update the in-memory DNS zone when backend health state changes.
- **R4** Return only currently healthy or bare-list IP addresses in DNS A-record responses.
- **R5** Return `NXDOMAIN` when a configured subdomain has no currently healthy or bare-list IPs.
- **R6** Support alias zones that resolve identically to the primary zone without separate health-check state.
- **R7** Compute SOA timing values from health-check parameters so DNS timing stays aligned with refresh behavior.
- **R8** When a DNSSEC private key is provided, sign the zone and publish the generated DNSSEC artifacts alongside the base A, NS, and SOA data.

### Operational

- **R9** Accept startup configuration through CLI arguments and Docker environment variables.
- **R10** Validate startup configuration before serving traffic; invalid configuration must fail fast and exit non-zero.
- **R11** Provide structured log output at configurable verbosity levels.
- **R12** Start serving DNS queries within seconds and require no external database or coordination service.
