# A Healthy DNS

[![Work in Progress](https://img.shields.io/badge/status-work%20in%20progress-yellow.svg)](https://github.com/indisoluble/a-healthy-dns)
[![CI](https://github.com/indisoluble/a-healthy-dns/actions/workflows/validate-tests.yml/badge.svg)](https://github.com/indisoluble/a-healthy-dns/actions/workflows/validate-tests.yml)
[![Codecov](https://codecov.io/gh/indisoluble/a-healthy-dns/branch/master/graph/badge.svg)](https://codecov.io/gh/indisoluble/a-healthy-dns)
[![Docker Hub](https://img.shields.io/docker/v/indisoluble/a-healthy-dns?label=docker%20hub&logo=docker)](https://hub.docker.com/r/indisoluble/a-healthy-dns)

`a-healthy-dns` is an authoritative DNS server that returns only healthy backend IPs for configured records.

It performs periodic TCP health checks, updates zone data in the background, and answers DNS queries from that health-aware zone state.

## Why Use It

- Health-aware A records with automatic failover behavior.
- Optional alias zones that reuse the same backend checks.
- Optional DNSSEC signing.
- Works as a CLI service or a Docker container.

## Quick Start (Docker)

Run the published image and expose DNS on host port `53053`:

```bash
docker run -d \
  --name a-healthy-dns \
  -p 53053:53/udp \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  indisoluble/a-healthy-dns
```

Verify the first result:

```bash
dig @127.0.0.1 -p 53053 www.example.com A
```

## Quick Start (CLI)

Install and run locally:

```bash
python -m pip install --upgrade pip
pip install .
```

```bash
a-healthy-dns \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["192.168.1.100","192.168.1.101"],"health_port":8080}}' \
  --ns '["ns1.example.com","ns2.example.com"]'
```

Then verify:

```bash
dig @127.0.0.1 -p 53053 www.example.com A
```

## Next Steps

- Full configuration schema and parameter rules: [docs/configuration-reference.md](docs/configuration-reference.md)
- Runtime operations and incident playbooks: [docs/operations-and-troubleshooting.md](docs/operations-and-troubleshooting.md)

## Documentation

- Documentation index and reading order: [docs/table-of-contents.md](docs/table-of-contents.md)
- Project scope and constraints: [docs/project-brief.md](docs/project-brief.md)
- Architecture and extension patterns: [docs/system-patterns.md](docs/system-patterns.md)
- Development and QA workflow: [docs/project-rules.md](docs/project-rules.md)
- Configuration reference: [docs/configuration-reference.md](docs/configuration-reference.md)
- Operations and troubleshooting: [docs/operations-and-troubleshooting.md](docs/operations-and-troubleshooting.md)

## Development

Use the repository QA workflow before pushing changes:

```bash
pytest
pytest --cov=indisoluble.a_healthy_dns --cov-report=term --cov-report=xml
docker build -t a-healthy-dns:test .
```

See [docs/project-rules.md](docs/project-rules.md) for the complete contributor workflow.
