# Project Brief

## Purpose

`a-healthy-dns` is an authoritative DNS server that updates answers according to backend health, so clients receive only currently healthy endpoints for configured subdomains and zones.

## Problem Statement

Static DNS records keep returning endpoints even when upstream services are down. This project addresses that gap by continuously testing backend reachability and rebuilding DNS zone data as health changes.

## Goals

1. Serve authoritative DNS answers for a configured hosted zone, with optional alias zones that share the same record data.
2. Expose only healthy `A` records per subdomain based on ongoing TCP connectivity checks.
3. Keep zone data current through a background update loop, including TTL/refresh behavior tied to check timing.
4. Support optional DNSSEC zone signing when a private key is configured.
5. Support both direct CLI execution and containerized deployment.

## Non-goals

1. Recursive or forwarding DNS resolution.
2. Advanced traffic policies (weighted, geo, latency routing).
3. Health checks beyond TCP connection tests.
4. Automatic backend discovery from service registries.
5. Full DNS record-type management beyond the implemented authoritative records.

## Primary Users and Use Cases

1. Platform or SRE teams running internal/external authoritative DNS for services with multiple backend IPs.
2. Teams that need simple failover behavior without introducing a larger service-mesh or load-balancer dependency.
3. Container-first deployments where runtime configuration is provided through environment variables.

## Functional Requirements

1. CLI must accept hosted zone, zone resolutions, and name server data as required inputs.
2. Configuration parsing must reject malformed JSON or invalid domain/IP/port values and fail fast.
3. Zone updater must periodically test backend connectivity and rebuild DNS zone records when health state changes.
4. Query handler must answer authoritatively for configured zones, return `NXDOMAIN` for unknown/out-of-zone names, and return `NOERROR` with empty answer when name exists but queried type does not.
5. DNSSEC signing must be optional and enabled only when valid key path and algorithm are configured.

## Non-functional Constraints

1. Runtime target is Python 3.10+ with `dnspython` and `cryptography` dependencies.
2. Network serving model is UDP DNS with a threaded health-update loop.
3. Default CLI DNS port is non-privileged (`53053`), while Docker runtime supports privileged DNS port binding (`53/udp`) via capability assignment.
4. Shutdown behavior must support graceful stop for both DNS server and updater thread.

## Delivery and Quality Constraints

1. Python unit/integration tests run through `pytest` with coverage reporting.
2. Docker workflow validates image build and live DNS behavior (including alias zone handling and expected response codes).
3. CI enforces version increment checks on `setup.py` for changes on `master`.

## Documentation Map

1. [`docs/system-patterns.md`](./system-patterns.md) captures architecture and execution flow.
2. [`docs/project-rules.md`](./project-rules.md) defines local QA commands and contribution workflow.
3. [`docs/configuration-reference.md`](./configuration-reference.md) defines CLI and Docker configuration schemas in detail.
4. [`docs/operations-and-troubleshooting.md`](./operations-and-troubleshooting.md) provides runtime diagnostics and incident playbooks.
