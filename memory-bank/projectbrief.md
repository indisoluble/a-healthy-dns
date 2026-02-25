# Project Brief

## Project Name
**a-healthy-dns** — Health-aware authoritative DNS server

## Vision
A lightweight, self-contained authoritative DNS server that dynamically resolves domain names to only those IP addresses that pass periodic TCP health checks. Unhealthy backends are automatically removed from DNS responses, providing client-side load balancing with health awareness without requiring external load balancers.

## Core Goals
1. **Health-aware DNS resolution**: Serve DNS A records that contain only IP addresses whose associated health-check port is reachable via TCP.
2. **Automatic zone management**: Continuously refresh the DNS zone in the background, adding/removing IPs based on health status changes.
3. **DNSSEC support**: Optionally sign the zone with RRSIG records, automatically managing signature inception, expiration, and re-signing schedules.
4. **Multi-domain support**: Serve identical records for a primary hosted zone and zero or more alias zones.
5. **Container-ready deployment**: Ship as a minimal Docker image with non-root execution, capability restrictions, and environment-variable–driven configuration.

## Scope
- **In scope**: UDP-only authoritative DNS server, A/NS/SOA/DNSKEY/RRSIG record types, TCP health checking, DNSSEC zone signing, Docker packaging, CLI with argparse.
- **Out of scope**: Recursive resolution, TCP DNS transport, AAAA records, dynamic API for zone changes, persistent storage, clustering/replication.

## Key Metrics
- 236 passing tests (pytest), 100 % green.
- Version: `0.1.26`
- Python ≥ 3.10, dependencies: `dnspython >=2.8,<3` + `cryptography >=46.0.5,<47`.

## Repository
- **Owner**: indisoluble
- **Default branch**: master
- **Package namespace**: `indisoluble.a_healthy_dns`
- **CLI entry point**: `a-healthy-dns` → `indisoluble.a_healthy_dns.main:main`
