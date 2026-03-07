# Project Brief

## Summary

A Healthy DNS is an authoritative DNS server for a primary hosted zone and
optional alias zones. It keeps DNS answers aligned with backend availability by
testing TCP connectivity to configured IP and port pairs, rebuilding its
in-memory zone, and serving only healthy A records. The runtime can optionally
sign the zone with DNSSEC.

## Problem Statement

Operators often need a small DNS layer that stops returning dead backend
addresses without introducing a full traffic-management platform. This project
addresses that problem by combining:

- Static zone intent supplied at startup
- Continuous health checks against backend endpoints
- Automatic authoritative DNS updates when health status changes

## Goals

- Provide a simple way to serve health-aware A records for one hosted zone and
  optional alias zones.
- Keep runtime state in memory and derive DNS answers directly from the latest
  health-check results.
- Fail closed for unhealthy endpoints by omitting unhealthy A records from DNS
  answers.
- Support optional DNSSEC signing for operators that need signed authoritative
  responses.
- Support both direct CLI execution and containerized deployment.

## Primary Use Cases

- Publish service endpoints for a domain where each subdomain maps to one or
  more backend IP addresses and a health-check port.
- Reuse the same backend set across alias zones without duplicating health
  checks.
- Run a lightweight authoritative DNS service inside a container while still
  binding to the standard DNS port when needed.
- Keep zone freshness tied to health-check cadence instead of manual record
  updates.

## Functional Scope

### In Scope

- CLI configuration for hosted zone, alias zones, zone resolutions, health-check
  timing, logging, name servers, and optional DNSSEC key material.
- Validation of domain names, JSON payload structure, IP addresses, and health
  ports before the server starts serving traffic.
- Background health checking using TCP connectivity tests.
- Automatic regeneration of NS, SOA, A, and optional DNSSEC records in an
  in-memory zone.
- Authoritative UDP answers for configured names under the primary zone and its
  aliases.

### Out of Scope

- Recursive DNS resolution or forwarding to upstream resolvers.
- TCP DNS serving, zone transfer protocols, or multi-node replication.
- Health checks richer than TCP connect success or failure.
- Runtime configuration APIs, dynamic service discovery, or persistent control
  plane storage.
- Per-alias custom record sets; alias zones reuse the same relative names and
  backend targets as the primary zone.

## Constraints

- The server requires Python 3.10+ and depends on `dnspython` plus
  `cryptography`.
- Startup configuration is required and must be valid; invalid zone, backend, or
  DNSSEC inputs abort startup instead of serving partial configuration.
- DNS answers are derived from a single process-local in-memory zone, so current
  state is not persisted across restarts.
- Query handling is authoritative-only and UDP-only.
- TTL and DNSSEC timing are derived from the configured health-check interval so
  cache behavior stays aligned with update cadence.

## Operational Requirements

- A hosted zone, at least one name server, and at least one subdomain
  resolution are mandatory inputs.
- Each subdomain resolution must declare a non-empty IP list and one health
  port shared by those IPs.
- DNSSEC is optional, but when enabled it requires readable private-key
  material and a supported signing algorithm.
- Graceful shutdown must stop the UDP server and background updater without
  leaving the process hanging.

## Quality Priorities

- Correctness of authoritative answers is more important than maximizing record
  availability for unhealthy backends.
- Configuration validation should fail early and clearly.
- Runtime behavior should stay understandable: one CLI entrypoint, one config
  builder, one background updater, one UDP request handler.
- Operational simplicity is preferred over feature breadth.

## Intended Readers

- Operators deploying the DNS server for a small set of services or domains.
- Maintainers changing configuration semantics, runtime behavior, or deployment
  workflow.
- Contributors who need the product scope and constraints before working on
  architecture or code-level details.
