# A Healthy DNS

[![Work in Progress](https://img.shields.io/badge/status-work%20in%20progress-yellow.svg)](https://github.com/indisoluble/a-healthy-dns)
[![CI](https://github.com/indisoluble/a-healthy-dns/actions/workflows/validate-tests.yml/badge.svg)](https://github.com/indisoluble/a-healthy-dns/actions/workflows/validate-tests.yml)
[![Codecov](https://codecov.io/gh/indisoluble/a-healthy-dns/branch/master/graph/badge.svg)](https://codecov.io/gh/indisoluble/a-healthy-dns)
[![Docker Hub](https://img.shields.io/docker/v/indisoluble/a-healthy-dns?label=docker%20hub&logo=docker)](https://hub.docker.com/r/indisoluble/a-healthy-dns)

A health-aware authoritative DNS server that automatically removes unhealthy backends from DNS responses through continuous TCP health checks. Only healthy endpoints are returned to clients, providing automatic failover at the DNS layer.

**Why use this?** Traditional DNS serves static IP lists regardless of backend health. A Healthy DNS continuously monitors your backends and dynamically updates DNS responses based on health status, ensuring clients only reach working services.

## What It Does

- **Continuous health monitoring** — TCP connectivity tests every 30 seconds (configurable)
- **Dynamic DNS updates** — Removes unhealthy IPs from responses automatically
- **Multi-domain support** — Serve multiple domains from the same backend IPs
- **DNSSEC signing** — Optional zone signing for secure DNS
- **Zero configuration changes needed** — Backends come and go without manual DNS updates

## Quick Start (Docker)

The fastest way to get started:

```bash
docker run -d \
  --name a-healthy-dns \
  -p 53053:53053/udp \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100","192.168.1.101"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  indisoluble/a-healthy-dns
```

Test it:

```bash
# Query the DNS server
dig @localhost -p 53053 www.example.com

# Watch logs to see health checks
docker logs -f a-healthy-dns
```

**What this does:**
- Creates DNS records for `www.example.com` pointing to two IPs
- Checks port 8080 on each IP every 30 seconds
- Only returns healthy IPs in DNS responses
- If all IPs fail, returns NXDOMAIN (fail-closed behavior)

## Installation Options

### Docker (Recommended)

Pre-built image on [Docker Hub](https://hub.docker.com/r/indisoluble/a-healthy-dns):

```bash
docker pull indisoluble/a-healthy-dns
```

See [docs/docker.md](docs/docker.md) for Docker Compose, security hardening, and production deployment.

### From Source

```bash
# Requires Python 3.10+
git clone https://github.com/indisoluble/a-healthy-dns.git
cd a-healthy-dns
pip install .

# Run directly
a-healthy-dns \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  --ns '["ns1.example.com"]'
```

## Basic Usage

### Minimal CLI Configuration

```bash
a-healthy-dns \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["192.168.1.100","192.168.1.101"],"health_port":80}}' \
  --ns '["ns1.example.com","ns2.example.com"]'
```

**Required parameters:**
- `--hosted-zone` — Your domain name
- `--zone-resolutions` — Subdomain → IPs + health check port mapping (JSON)
- `--ns` — Name servers for your zone (JSON array)

### Common Options

```bash
a-healthy-dns \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["10.0.1.100","10.0.1.101"],"health_port":80}}' \
  --ns '["ns1.example.com"]' \
  --port 53 \                      # Standard DNS port (requires root/capabilities)
  --test-min-interval 15 \          # Health check every 15 seconds
  --test-timeout 2 \                # 2-second health check timeout
  --log-level info                  # Logging verbosity
```

See [docs/configuration.md](docs/configuration.md) for all parameters, examples, and tuning guidance.

## Testing Your Deployment

```bash
# Query A records
dig @localhost -p 53053 www.example.com

# Query with verbose output
dig @localhost -p 53053 www.example.com +noall +answer

# Check SOA and NS records
dig @localhost -p 53053 example.com SOA
dig @localhost -p 53053 example.com NS

# Test DNSSEC (if enabled)
dig @localhost -p 53053 www.example.com +dnssec
```

## How Health Checks Work

1. **Health checker** runs in background thread
2. **TCP connection test** to each IP on configured health port
3. **Success** → IP marked healthy and included in DNS responses
4. **Failure** → IP marked unhealthy and excluded from DNS responses
5. **All unhealthy** → Subdomain returns NXDOMAIN (fail-closed)

Health checks repeat every `test-min-interval` seconds (default 30s).

## Documentation

- **[docs/table-of-contents.md](docs/table-of-contents.md)** — Documentation index
- **[docs/project-brief.md](docs/project-brief.md)** — Goals, requirements, constraints
- **[docs/system-patterns.md](docs/system-patterns.md)** — Architecture and design patterns
- **[docs/project-rules.md](docs/project-rules.md)** — Python conventions, testing, QA commands
- **[docs/configuration.md](docs/configuration.md)** — Complete configuration reference
- **[docs/docker.md](docs/docker.md)** — Docker deployment guide
- **[docs/troubleshooting.md](docs/troubleshooting.md)** — Common issues and debugging
- **[AGENTS.md](AGENTS.md)** — Coding agent contract and standards

## Contributing

Contributions welcome! See [docs/project-rules.md](docs/project-rules.md) for development setup, testing, and coding conventions.

## License

Apache License 2.0. See [LICENSE](LICENSE) for details.