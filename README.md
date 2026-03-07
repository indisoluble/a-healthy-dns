# A Healthy DNS

[![Work in Progress](https://img.shields.io/badge/status-work%20in%20progress-yellow.svg)](https://github.com/indisoluble/a-healthy-dns)
[![CI](https://github.com/indisoluble/a-healthy-dns/actions/workflows/validate-tests.yml/badge.svg)](https://github.com/indisoluble/a-healthy-dns/actions/workflows/validate-tests.yml)
[![Codecov](https://codecov.io/gh/indisoluble/a-healthy-dns/branch/master/graph/badge.svg)](https://codecov.io/gh/indisoluble/a-healthy-dns)
[![Docker Hub](https://img.shields.io/docker/v/indisoluble/a-healthy-dns?label=docker%20hub&logo=docker)](https://hub.docker.com/r/indisoluble/a-healthy-dns)

A health-aware authoritative DNS server. It performs TCP connectivity checks against backend IPs and dynamically updates DNS responses so that queries only return healthy endpoints — automatic failover with no external orchestration.

## Quick start

### Docker (recommended)

```bash
docker run -d \
  --name a-healthy-dns \
  -p 53053:53/udp \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100","192.168.1.101"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  indisoluble/a-healthy-dns
```

### From source

```bash
git clone https://github.com/indisoluble/a-healthy-dns.git
cd a-healthy-dns
pip install .

a-healthy-dns \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["192.168.1.100","192.168.1.101"],"health_port":8080}}' \
  --ns '["ns1.example.com"]'
```

### Verify

```bash
dig @localhost -p 53053 www.example.com
```

## Key features

- **Health checking** — continuous TCP connectivity tests; only healthy IPs appear in responses.
- **Multi-domain** — alias zones share records and health state without duplicating checks.
- **DNSSEC** — optional zone signing with automatic re-signing.
- **Docker-ready** — pre-built multi-platform image (`amd64`, `arm64`) on [Docker Hub](https://hub.docker.com/r/indisoluble/a-healthy-dns).

## Documentation

| Document | Content |
|----------|---------|
| [docs/project-brief.md](docs/project-brief.md) | Goals, non-goals, constraints, requirements. |
| [docs/system-patterns.md](docs/system-patterns.md) | Architecture, data flow, design patterns. |
| [docs/project-rules.md](docs/project-rules.md) | Language conventions, QA commands, CI/CD pipeline. |
| [docs/configuration.md](docs/configuration.md) | Full configuration reference: CLI args, env vars, zone resolution schema, DNSSEC. |
| [docs/docker.md](docs/docker.md) | Docker build, run, compose, security hardening, troubleshooting. |
| [docs/table-of-contents.md](docs/table-of-contents.md) | Documentation index and minimum reading set. |