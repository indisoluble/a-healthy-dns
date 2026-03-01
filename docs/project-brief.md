# Project Brief

## What is A Healthy DNS?

A health-aware DNS server that performs TCP connectivity checks on backend IP
addresses and automatically updates DNS responses so queries only return healthy
endpoints.

## Goals

- Provide automatic failover by removing unhealthy IPs from DNS answers.
- Support multiple subdomains, each with its own set of IPs and health-check port.
- Serve multiple domains (alias zones) that resolve to the same IPs without
  duplicating health checks.
- Optionally sign zones with DNSSEC.

## Non-goals

- Acting as a recursive or forwarding resolver.
- Supporting record types other than A, NS, SOA (and DNSSEC-related).
- GUI or web-based management.
- Persisting state across restarts (zone is rebuilt from config + live checks).

## Constraints

- Python ≥ 3.10.
- Runtime dependencies limited to `dnspython` and `cryptography` (no frameworks).
- Single-process, single UDP listener.
- Configuration via CLI args (or env vars in Docker); no config files.

## High-level requirements

| # | Requirement |
|---|---|
| R1 | Parse zone-resolution config (JSON) and validate at startup. |
| R2 | Perform periodic TCP health checks per IP/port pair. |
| R3 | Rebuild DNS zone transactionally when health status changes. |
| R4 | Respond to A / NS / SOA queries with only healthy data. |
| R5 | Support alias zones (multi-domain → same records). |
| R6 | Optionally DNSSEC-sign the zone (RSA, key loaded from PEM). |
| R7 | Graceful shutdown on SIGINT / SIGTERM. |
| R8 | Deployable as Docker container with env-var configuration. |
