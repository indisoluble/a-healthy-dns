# A Healthy DNS

[![Work in Progress](https://img.shields.io/badge/status-work%20in%20progress-yellow.svg)](https://github.com/indisoluble/a-healthy-dns)
[![CI](https://github.com/indisoluble/a-healthy-dns/actions/workflows/validate-tests.yml/badge.svg)](https://github.com/indisoluble/a-healthy-dns/actions/workflows/validate-tests.yml)
[![Codecov](https://codecov.io/gh/indisoluble/a-healthy-dns/branch/master/graph/badge.svg)](https://codecov.io/gh/indisoluble/a-healthy-dns)
[![Docker Hub](https://img.shields.io/docker/v/indisoluble/a-healthy-dns?label=docker%20hub&logo=docker)](https://hub.docker.com/r/indisoluble/a-healthy-dns)

A Healthy DNS is an authoritative UDP DNS server for one hosted zone and optional
alias zones. It probes configured backend `ip:port` pairs with TCP health checks
and publishes only healthy A records, with optional DNSSEC signing.

For local source runs, use Python `3.10+`.

## Quick Start

From the repository root, start a temporary healthy backend in one terminal:

```bash
python -m http.server 8080 --bind 127.0.0.1
```

Install and run the DNS server in another terminal:

```bash
python -m pip install .
a-healthy-dns \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["127.0.0.1"],"health_port":8080}}' \
  --ns '["ns1.example.com"]' \
  --port 53053
```

Query it from a third terminal:

```bash
dig @127.0.0.1 -p 53053 +short www.example.com A
```

Expected result:

```text
127.0.0.1
```

## Highlights

- authoritative UDP DNS for a primary hosted zone plus optional alias zones
- health-aware A answers based on TCP connectivity checks
- startup-time validation for JSON config, IPs, ports, and DNSSEC inputs
- optional DNSSEC signing
- direct CLI and Docker deployment modes

## Docker

The container image defaults to internal port `53`. For a container launch
example on a high port:

```bash
docker build -t a-healthy-dns .
docker run --rm \
  -p 53053:53053/udp \
  -e DNS_PORT="53053" \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  a-healthy-dns
```

Use backend IPs that are reachable from inside the container. For DNSSEC,
Compose, smoke tests, and troubleshooting, use
[`docs/deployment-and-operations.md`](./docs/deployment-and-operations.md).

## Documentation

- [`docs/table-of-contents.md`](./docs/table-of-contents.md)
- [`docs/project-brief.md`](./docs/project-brief.md)
- [`docs/system-patterns.md`](./docs/system-patterns.md)
- [`docs/project-rules.md`](./docs/project-rules.md)
- [`docs/configuration-reference.md`](./docs/configuration-reference.md)
- [`docs/deployment-and-operations.md`](./docs/deployment-and-operations.md)
