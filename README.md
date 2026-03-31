# A Healthy DNS

[![Work in Progress](https://img.shields.io/badge/status-work%20in%20progress-yellow.svg)](https://github.com/indisoluble/a-healthy-dns)
[![CI](https://github.com/indisoluble/a-healthy-dns/actions/workflows/validate-tests.yml/badge.svg)](https://github.com/indisoluble/a-healthy-dns/actions/workflows/validate-tests.yml)
[![Codecov](https://codecov.io/gh/indisoluble/a-healthy-dns/branch/master/graph/badge.svg)](https://codecov.io/gh/indisoluble/a-healthy-dns)
[![Docker Hub](https://img.shields.io/docker/v/indisoluble/a-healthy-dns?label=docker%20hub&logo=docker)](https://hub.docker.com/r/indisoluble/a-healthy-dns)

An authoritative UDP DNS server that continuously health-checks backend IPs via TCP and serves only healthy A records.

When every backend for a subdomain is unhealthy, that name fails closed with `NXDOMAIN` until at least one backend recovers.

## Quick start

### Option A: Docker (recommended)

This quick start keeps the container on a high port so local testing does not require binding host port `53`.

```bash
docker run -d \
  --name a-healthy-dns \
  -p 53053:53053/udp \
  -e DNS_HOSTED_ZONE="example.local" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100","192.168.1.101"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.local"]' \
  -e DNS_PORT="53053" \
  indisoluble/a-healthy-dns
```

Verify it is running:

```bash
dig @localhost -p 53053 example.local SOA
dig @localhost -p 53053 www.example.local A
docker logs --tail 50 a-healthy-dns
```

For Compose usage, port-53 deployment, DNSSEC key mounts, and hardening, use [docs/docker.md](docs/docker.md).

### Option B: Python CLI (from source)

```bash
git clone https://github.com/indisoluble/a-healthy-dns.git
cd a-healthy-dns
pip install .

a-healthy-dns \
  --hosted-zone example.local \
  --zone-resolutions '{"www":{"ips":["192.168.1.100","192.168.1.101"],"health_port":8080}}' \
  --ns '["ns1.example.local"]'
```

Requires Python 3.10+.

## Behavior at a glance

- Health checks run in the background, testing TCP connectivity to each `(ip, health_port)` pair at a configurable interval.
- When an IP becomes unhealthy it is removed from DNS A record responses immediately on the next zone update.
- When all IPs for a subdomain are unhealthy, the subdomain returns `NXDOMAIN`.
- Multiple domain aliases can share the same health-checked records without duplicated checks (`--alias-zones`).
- DNSSEC zone signing is supported when a private key is provided (`--priv-key-path`).

## Documentation

Start with [docs/table-of-contents.md](docs/table-of-contents.md) for the minimum reading set and the canonical owner of each documentation topic.

| Document | Contents |
|---|---|
| [docs/table-of-contents.md](docs/table-of-contents.md) | Full documentation index, minimum reading set, and canonical topic ownership |
| [docs/project-brief.md](docs/project-brief.md) | Goals, non-goals, constraints, requirements |
| [docs/system-patterns.md](docs/system-patterns.md) | Architecture patterns, structural conventions, and folder hierarchy / codebase layout rules |
| [docs/project-rules.md](docs/project-rules.md) | Toolchain, QA workflow, CI/release rules, and repository-specific code conventions |
| [docs/RFC-conformance.md](docs/RFC-conformance.md) | Wire-level authoritative UDP behavior, response semantics, and RFC scope boundaries |
| [docs/configuration-reference.md](docs/configuration-reference.md) | CLI flags and Docker environment variables with defaults and examples |
| [docs/docker.md](docs/docker.md) | Docker deployment guide: quick start, Compose, DNSSEC mounts, hardening, and upgrades |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Runtime diagnosis, log interpretation, live debugging, monitoring, and incident handoff |
