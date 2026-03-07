# Project Brief

## What it is

A Healthy DNS is a health-aware authoritative DNS server. It performs active TCP connectivity checks against backend IP addresses and dynamically updates DNS responses so that queries only return healthy endpoints.

## Why it exists

Standard DNS servers return static records regardless of backend health. When a backend goes down, clients continue receiving its IP until a human intervenes or an external failover system reacts. A Healthy DNS eliminates that gap by embedding health checking directly into the DNS server, providing automatic failover without external orchestration.

## Goals

- Serve authoritative DNS with automatic failover based on real-time health checks.
- Require zero external dependencies beyond Python and its packages — no sidecar health checkers, no service mesh, no orchestrator integration.
- Support multiple domains (alias zones) sharing the same health-checked records without duplicating checks.
- Optionally sign zones with DNSSEC.
- Run as a single process with a simple CLI interface — no configuration files.
- Be deployable as a Docker container with environment-variable-only configuration.

## Non-goals

- **Recursive resolution.** This is an authoritative-only server; it does not resolve queries for zones it does not host.
- **HTTP/HTTPS health checks.** Health is determined by TCP connectivity (3-way handshake), not application-layer probes.
- **Load balancing algorithms.** All healthy IPs are returned; the client or its resolver decides which to use (typically round-robin by the stub resolver).
- **Persistent state.** Zone data is entirely in-memory and rebuilt from health checks each cycle. There is no database or on-disk zone file.
- **DNS-over-HTTPS / DNS-over-TLS.** Only UDP transport is supported.
- **Dynamic record management API.** Records are defined at startup via CLI arguments; runtime changes require a restart.

## Constraints

- **Python 3.10+** — minimum language version.
- **Dependencies:** `dnspython >=2.8.0, <3.0.0` for DNS protocol handling; `cryptography >=46.0.5, <47.0.0` for DNSSEC operations.
- **UDP only** — DNS queries are served over UDP; TCP DNS transport is not implemented.
- **Single-threaded DNS serving** — the UDP server handles queries on the main thread; health checks run on a single background thread.

## Requirements

### Functional

1. Accept zone configuration (hosted zone, subdomains, IPs, health ports, name servers) via CLI arguments or Docker environment variables.
2. Perform periodic TCP connectivity tests against each configured IP on its health port.
3. Build and serve a DNS zone containing only healthy A records.
4. Recalculate TTLs based on the health-check interval so clients re-query before the next cycle completes.
5. Support multiple zone origins (primary + aliases) served from the same underlying records and health state.
6. Optionally sign the zone with DNSSEC, automatically re-signing before signature expiration.

### Operational

1. Start with a single command and no configuration files.
2. Shut down gracefully on SIGINT/SIGTERM, completing in-flight health checks.
3. Log health transitions and zone updates at configurable verbosity levels.
4. Run as a non-root user inside Docker with minimal capabilities (`NET_BIND_SERVICE` only).
