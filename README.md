# A Healthy DNS

[![Work in Progress](https://img.shields.io/badge/status-work%20in%20progress-yellow.svg)](https://github.com/indisoluble/a-healthy-dns)
[![CI](https://github.com/indisoluble/a-healthy-dns/actions/workflows/validate-tests.yml/badge.svg)](https://github.com/indisoluble/a-healthy-dns/actions/workflows/validate-tests.yml)
[![Codecov](https://codecov.io/gh/indisoluble/a-healthy-dns/branch/master/graph/badge.svg)](https://codecov.io/gh/indisoluble/a-healthy-dns)
[![Docker Hub](https://img.shields.io/docker/v/indisoluble/a-healthy-dns?label=docker%20hub&logo=docker)](https://hub.docker.com/r/indisoluble/a-healthy-dns)

An authoritative UDP DNS server for one hosted zone that can serve standard static A records, health-checked A records, or a mix of both.

Health-checked entries are published only while their TCP check passes. Standard static entries are published without a health probe. When an owner name and its subtree are absent from the active zone view, queries return `NXDOMAIN`; existing empty non-terminals return `NODATA`.

## Quick start

### Option A: Docker (recommended)

This quick start keeps the container on a high port so local testing does not require binding host port `53`. It intentionally mixes a standard static `www` record with a health-checked `checked` record; the verification query uses `www` so the first run does not depend on a reachable sample backend.

```bash
docker run -d \
  --name a-healthy-dns \
  -p 53053:53053/udp \
  indisoluble/a-healthy-dns \
  --port 53053 \
  --hosted-zone example.local \
  --zone-resolutions '{"www":["192.168.1.200"],"checked":{"ips":["192.168.1.100","192.168.1.101"],"health_port":8080}}' \
  --ns '["ns1.dns.example.net"]'
```

Verify it is running:

```bash
dig @localhost -p 53053 example.local SOA
dig @localhost -p 53053 www.example.local A
docker logs --tail 50 a-healthy-dns
```

For Compose usage, port-53 deployment, DNSSEC key mounts, hardening, and production image pinning, use [docs/docker.md](docs/docker.md). The untagged image above is for a local quick start; production deployments should pin a specific image tag.

### Option B: Python CLI (from source)

```bash
git clone https://github.com/indisoluble/a-healthy-dns.git
cd a-healthy-dns
pip install .

a-healthy-dns \
  --hosted-zone example.local \
  --zone-resolutions '{"www":["192.168.1.200"],"checked":{"ips":["192.168.1.100","192.168.1.101"],"health_port":8080}}' \
  --ns '["ns1.dns.example.net"]'
```

Requires Python 3.11+.

## Behavior at a glance

- Each subdomain can be configured in one of two supported record modes: health-checked (`{"ips":[...],"health_port":...}`) or standard static (`["ip1","ip2"]`).
- Health checks run in the background, testing TCP connectivity only for entries configured with a `health_port`.
- Standard static entries are returned without a health probe and can be mixed freely with health-checked entries in the same zone.
- When a health-checked IP becomes unhealthy it is removed from DNS A record responses on the next zone update.
- When an owner name and its subtree are absent from the active zone view, queries return `NXDOMAIN`; existing empty non-terminals return `NODATA`.
- Multiple domain aliases can share the same records without duplicated checks (`--alias-zones`).
- Optional DNSSEC artifact publication is supported when a private key is provided (`--priv-key-path`); full DNSSEC authoritative-server behavior is out of scope.

## Documentation

Start with [docs/table-of-contents.md](docs/table-of-contents.md) for the full documentation index, minimum reading set, and canonical owner of each documentation topic.

Common next stops:

| Need | Document |
|---|---|
| Full documentation navigation | [docs/table-of-contents.md](docs/table-of-contents.md) |
| CLI flags and examples | [docs/configuration-reference.md](docs/configuration-reference.md) |
| Docker deployment | [docs/docker.md](docs/docker.md) |
| Runtime diagnosis | [docs/troubleshooting.md](docs/troubleshooting.md) |
| DNS wire behavior and RFC scope | [docs/RFC-conformance.md](docs/RFC-conformance.md) |
