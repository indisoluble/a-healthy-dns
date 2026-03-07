# A Healthy DNS

[![Work in Progress](https://img.shields.io/badge/status-work%20in%20progress-yellow.svg)](https://github.com/indisoluble/a-healthy-dns)
[![CI](https://github.com/indisoluble/a-healthy-dns/actions/workflows/validate-tests.yml/badge.svg)](https://github.com/indisoluble/a-healthy-dns/actions/workflows/validate-tests.yml)
[![Codecov](https://codecov.io/gh/indisoluble/a-healthy-dns/branch/master/graph/badge.svg)](https://codecov.io/gh/indisoluble/a-healthy-dns)
[![Docker Hub](https://img.shields.io/docker/v/indisoluble/a-healthy-dns?label=docker%20hub&logo=docker)](https://hub.docker.com/r/indisoluble/a-healthy-dns)

A health-aware authoritative DNS server. It continuously probes backend IPs via TCP and automatically removes unhealthy endpoints from DNS responses — no operator intervention required.

## Quick start

### Docker (recommended)

```bash
docker run -d \
  --name a-healthy-dns \
  -p 53053:53053/udp \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100","192.168.1.101"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  indisoluble/a-healthy-dns
```

Verify it responds:

```bash
dig @localhost -p 53053 www.example.com
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

Requires Python ≥ 3.10.

## Documentation

| Document | Description |
|---|---|
| [docs/project-brief.md](docs/project-brief.md) | Goals, non-goals, constraints, requirements |
| [docs/configuration.md](docs/configuration.md) | All CLI arguments and Docker environment variables |
| [docs/system-patterns.md](docs/system-patterns.md) | Architecture and design patterns |
| [docs/project-rules.md](docs/project-rules.md) | Dev setup, QA commands, CI pipeline |
| [docs/table-of-contents.md](docs/table-of-contents.md) | Full documentation index |