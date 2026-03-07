# Project Brief

## What it is

**A Healthy DNS** is a health-aware authoritative DNS server.  
It continuously tests the TCP reachability of backend IP addresses and automatically removes unhealthy IPs from DNS A-record responses, so clients only ever receive live endpoints.

## Why it exists

Standard authoritative DNS servers serve static records.  
When a backend goes down, DNS continues advertising the dead IP until an operator manually edits the zone.  
A Healthy DNS closes this gap: it couples the DNS response directly to a real-time health signal, providing automatic failover with no external orchestration layer.

## Goals

1. **Automatic failover** — unhealthy IPs are removed from responses without manual intervention.
2. **Authoritative DNS** — the server is the authoritative source for one or more zones; no forwarding or caching mode.
3. **Multi-domain support** — a single set of health-checked records can be served under multiple domain names (primary + alias zones) without duplicating health check logic.
4. **DNSSEC support** — optional zone signing with automatic signature rotation.
5. **Minimal footprint** — a single Python process, deployable as a CLI tool or Docker container.
6. **Configurable health checking** — tunable TCP test interval and timeout to fit different SLA requirements.

## Non-goals

- **Not a recursive/caching resolver** — it does not forward or cache queries for external domains.
- **Not a load balancer** — it does not distribute traffic; it only includes healthy IPs in responses.
- **Not a service discovery system** — there is no dynamic registration API; backends are declared at startup via configuration.
- **No HTTP health checks** — health probes are TCP connectivity tests only; no HTTP/HTTPS probe logic.
- **No persistence** — zone state is in-memory; there is no on-disk zone file or database.
- **No cluster mode** — single-instance only; no replication or consensus protocol.

## Constraints

| Constraint | Value |
|---|---|
| Python version | ≥ 3.10 |
| DNS transport | UDP only (no TCP DNS) |
| Health probe protocol | TCP connectivity test |
| Default listening port | 53053 (non-privileged); port 53 requires `NET_BIND_SERVICE` capability |
| Zone state | In-memory; lost on restart |
| DNSSEC | Optional; requires an externally generated private key file |
| Configuration surface | CLI arguments and Docker environment variables (no config file) |

## Requirements

### Functional

- Serve authoritative DNS responses for a configured hosted zone and optional alias zones.
- Track one or more IP addresses per subdomain, each with an associated health-check TCP port.
- Exclude IPs that fail TCP connectivity tests from A-record responses.
- Return `NXDOMAIN` when all IPs for a subdomain are unhealthy.
- Serve NS and SOA records for the zone.
- Optionally sign the zone with DNSSEC (RRSIG, DNSKEY) and rotate signatures automatically before expiry.
- Support multiple alias zones that resolve to the same set of health-checked records.

### Operational

- Accept configuration via CLI arguments (`a-healthy-dns`) or Docker environment variables.
- Emit structured log output at configurable verbosity (debug / info / warning / error / critical).
- Run as a non-root user in Docker; bind to privileged port 53 only when `NET_BIND_SERVICE` capability is granted.
- Shut down cleanly on `SIGINT` / `SIGTERM`.

## Out of scope

- Zone transfer (AXFR/IXFR).
- Dynamic DNS update protocol (RFC 2136).
- IPv6 / AAAA record health checking.
- HTTP/HTTPS health probes.
- Configuration hot-reload (restart required to change configuration).
- Multi-instance deployment or leader election.
