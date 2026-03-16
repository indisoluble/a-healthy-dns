# A Healthy DNS

[![Work in Progress](https://img.shields.io/badge/status-work%20in%20progress-yellow.svg)](https://github.com/indisoluble/a-healthy-dns)
[![CI](https://github.com/indisoluble/a-healthy-dns/actions/workflows/validate-tests.yml/badge.svg)](https://github.com/indisoluble/a-healthy-dns/actions/workflows/validate-tests.yml)
[![Codecov](https://codecov.io/gh/indisoluble/a-healthy-dns/branch/master/graph/badge.svg)](https://codecov.io/gh/indisoluble/a-healthy-dns)
[![Docker Hub](https://img.shields.io/docker/v/indisoluble/a-healthy-dns?label=docker%20hub&logo=docker)](https://hub.docker.com/r/indisoluble/a-healthy-dns)

An authoritative DNS server that continuously health-checks backend IPs via TCP and automatically removes unhealthy endpoints from DNS responses — no external orchestration required.

## Quick start

### Option A: Docker (recommended)

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
dig @localhost -p 53053 www.example.local
docker logs a-healthy-dns
```

### Option B: Python (from source)

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

## How it works

- Health checks run in the background, testing TCP connectivity to each `(ip, health_port)` pair at a configurable interval.
- When an IP becomes unhealthy it is removed from DNS A record responses immediately on the next zone update.
- When all IPs for a subdomain are unhealthy, the subdomain returns `NXDOMAIN`.
- Multiple domain aliases can share the same health-checked records without duplicated checks (`--alias-zones`).
- DNSSEC zone signing is supported when a private key is provided (`--priv-key-path`).

## Documentation

| Document | Contents |
|---|---|
| [docs/docker.md](docs/docker.md) | Docker deployment: image details, Compose, deployment patterns, container management, security, and orchestration |
| [docs/configuration-reference.md](docs/configuration-reference.md) | All CLI flags and Docker env vars with defaults and examples |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Common issues, debugging, and operational procedures |
| [docs/RFC-conformance.md](docs/RFC-conformance.md) | RFC conformance reference: Level 1 authoritative UDP scope, minimum RFC set, current coverage per RFC, and broader-than-Level-1 scope limits |
| [docs/project-brief.md](docs/project-brief.md) | Goals, non-goals, constraints, requirements |
| [docs/system-patterns.md](docs/system-patterns.md) | Architecture and design patterns |
| [docs/project-rules.md](docs/project-rules.md) | Toolchain, QA commands, CI/CD workflow, naming conventions |
| [docs/table-of-contents.md](docs/table-of-contents.md) | Full documentation index |