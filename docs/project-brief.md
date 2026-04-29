# Project Brief

This document defines the product scope and acceptance boundaries for **A Healthy DNS**.

It is the canonical home for purpose, scope, goals, non-goals, target operators, and high-level capabilities. Requirements live in [`docs/requirements.md`](requirements.md); major decision rationale lives in [`docs/decisions.md`](decisions.md); architecture and folder layout live in [`docs/architecture.md`](architecture.md); engineering rules live in [`docs/engineering-rules.md`](engineering-rules.md); configuration syntax lives in [`docs/configuration-reference.md`](configuration-reference.md); protocol-level DNS behavior lives in [`docs/RFC-conformance.md`](RFC-conformance.md).

## What it is

**A Healthy DNS** is an authoritative DNS server that can publish standard static IP addresses, health-checked IP addresses, or both within the same hosted zone. Health-checked entries use continuous TCP probes and DNS answers update automatically to reflect backend health. Standard static entries are published without a health probe. Both modes can be mixed across subdomains within one deployment.

## Why it exists

Traditional authoritative DNS returns static records. When a backend becomes unavailable, DNS continues advertising it until an operator changes the zone. A Healthy DNS preserves that standard authoritative behavior for static records while adding health-aware answers where operators want automatic failover, so one zone can combine both patterns without an external control plane.

## Goals

1. **Automatic failover** — remove unhealthy IP addresses from DNS responses without manual intervention.
2. **Authoritative DNS** — serve one hosted zone plus any configured alias zones as an authoritative UDP DNS server.
3. **Dual record modes** — support standard static records, health-checked records, and mixed configurations as first-class product behavior.
4. **Multi-domain support** — let multiple domain aliases reuse the same records without duplicating record or health-check state.
5. **Optional DNSSEC** — sign the zone when a private key is provided and publish the generated DNSSEC artifacts alongside the base records.
6. **Configurable health checking** — allow operators to tune check interval, TCP timeout, and health port per health-checked subdomain.
7. **Operational simplicity** — run as a single Python process or Docker container with startup-time configuration only.

## Non-goals

- **Recursive resolution** — the server does not perform recursive lookups or act as a caching resolver.
- **Non-TCP health checks** — health is determined exclusively by TCP connectivity; ICMP, HTTP, and other protocols are out of scope.
- **Live configuration reload** — adding or removing subdomains or zones requires a restart.
- **Zone replication and transfers** — AXFR, IXFR, and multi-instance state replication are out of scope.
- **IPv6 answer support** — current implementation serves A records (IPv4) only.
- **Traffic-shaping policy** — weighted, geographic, or policy-based routing is out of scope.

## High-level capabilities

- Serve authoritative UDP DNS answers for one hosted zone and optional alias zones.
- Publish A, SOA, and NS records, with optional DNSSEC-generated DNSKEY, NSEC, and RRSIG data.
- Mix standard static A records and TCP health-checked A records in the same zone.
- Update the in-memory zone automatically as backend health changes.
- Run directly from the Python CLI or as a Docker container.
