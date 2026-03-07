# Configuration Reference

Full parameter reference for **A Healthy DNS**, covering both the CLI (`a-healthy-dns`) and Docker environment variables.

> **Quick-start:** see [`README.md`](../README.md).  
> **Parameter behaviour details** (TTL derivation, DNSSEC timing): see [`docs/system-patterns.md`](system-patterns.md).

---

## Two configuration surfaces

| Surface | When to use |
|---|---|
| **CLI flags** | Direct invocation (`a-healthy-dns --flag value ...`) |
| **Docker env vars** | Container deployment (`-e DNS_VAR=value`) |

The Docker entrypoint maps each `DNS_*` variable to its corresponding CLI flag. They are equivalent in function.

---

## Required parameters

These three must always be provided. The server will not start without them.

### Hosted zone

| Surface | Name |
|---|---|
| CLI | `--hosted-zone` |
| Docker | `DNS_HOSTED_ZONE` |

The domain name for which this server is authoritative.

```
--hosted-zone example.com
```

### Zone resolutions

| Surface | Name |
|---|---|
| CLI | `--zone-resolutions` |
| Docker | `DNS_ZONE_RESOLUTIONS` |

JSON object mapping subdomain names to their IP list and health check port.

**Schema:**
```json
{
  "<subdomain>": {
    "ips": ["<ip1>", "<ip2>"],
    "health_port": <port>
  }
}
```

**Example:**
```json
{
  "www": {
    "ips": ["192.168.1.100", "192.168.1.101"],
    "health_port": 8080
  },
  "api": {
    "ips": ["192.168.1.102"],
    "health_port": 8000
  }
}
```

- Each `<subdomain>` is relative to the hosted zone (e.g. `www` → `www.example.com`).
- `ips` must be valid IPv4 addresses (IPv6/AAAA is not supported).
- `health_port` is the TCP port used for health checks.
- All IPs for a subdomain share the same health port.

### Name servers

| Surface | Name |
|---|---|
| CLI | `--ns` |
| Docker | `DNS_NAME_SERVERS` |

JSON array of fully-qualified name server hostnames for the zone's NS record.

```json
["ns1.example.com", "ns2.example.com"]
```

---

## Optional parameters

### Port

| Surface | Name | Default |
|---|---|---|
| CLI | `--port` | `53053` |
| Docker | `DNS_PORT` | `53` |

UDP port the DNS server listens on.

> **Note:** the Docker image default (`53`) differs from the CLI default (`53053`). The image uses `setcap cap_net_bind_service` on the Python binary to allow binding to privileged port 53 without root.

### Log level

| Surface | Name | Default |
|---|---|---|
| CLI | `--log-level` | `info` |
| Docker | `DNS_LOG_LEVEL` | _(not set — falls back to CLI default)_ |

Log verbosity. Accepted values (case-insensitive): `debug`, `info`, `warning`, `error`, `critical`.

### Minimum health-check interval

| Surface | Name | Default |
|---|---|---|
| CLI | `--test-min-interval` | `30` |
| Docker | `DNS_TEST_MIN_INTERVAL` | _(not set — falls back to CLI default)_ |

Minimum seconds between consecutive TCP health checks for a given IP address.

The effective interval is `max(test-min-interval, sum of per-IP timeout × count + per-record overhead)`. See [docs/system-patterns.md § 6](system-patterns.md#6-interval-calculation-pattern) for the full formula.

### Health-check timeout

| Surface | Name | Default |
|---|---|---|
| CLI | `--test-timeout` | `2` |
| Docker | `DNS_TEST_TIMEOUT` | _(not set — falls back to CLI default)_ |

Maximum seconds to wait for a TCP connection during a health check. If the connection does not succeed within this time the IP is considered unhealthy.

### Alias zones

| Surface | Name | Default |
|---|---|---|
| CLI | `--alias-zones` | `[]` |
| Docker | `DNS_ALIAS_ZONES` | _(not set — falls back to CLI default)_ |

JSON array of additional domain names that resolve to the same records as the hosted zone. Health checks are shared; no duplication occurs.

```json
["alias1.com", "alias2.com"]
```

See [docs/system-patterns.md § 7](system-patterns.md#7-multi-domain-support-via-zoneorigins) for the implementation pattern.

---

## DNSSEC parameters (optional)

Both parameters are optional. If `--priv-key-path` / `DNS_PRIV_KEY_PATH` is omitted, DNSSEC signing is disabled entirely and no RRSIG records are produced.

### Private key path

| Surface | Name | Default |
|---|---|---|
| CLI | `--priv-key-path` | _(none)_ |
| Docker | `DNS_PRIV_KEY_PATH` | _(none)_ |

Path to a PEM-encoded DNSSEC private key file. In Docker, mount the key directory into `/app/keys` (read-only) and point this to the mounted path.

```bash
# Docker example
-v "$(pwd)/keys:/app/keys:ro"
-e DNS_PRIV_KEY_PATH="/app/keys/private.pem"
```

### Private key algorithm

| Surface | Name | Default |
|---|---|---|
| CLI | `--priv-key-alg` | `RSASHA256` |
| Docker | `DNS_PRIV_KEY_ALG` | _(not set — falls back to CLI default)_ |

Algorithm used to sign the zone. Accepted values are the DNSSEC algorithm names supported by `dnspython` (e.g. `RSASHA256`, `RSASHA512`, `ECDSAP256SHA256`, `ECDSAP384SHA384`, `ED25519`, `ED448`). The full list is validated at startup against the installed `dnspython` version.

---

## Parameter summary table

| Parameter | CLI flag | Docker env var | Required | Default |
|---|---|---|---|---|
| Hosted zone | `--hosted-zone` | `DNS_HOSTED_ZONE` | **yes** | — |
| Zone resolutions | `--zone-resolutions` | `DNS_ZONE_RESOLUTIONS` | **yes** | — |
| Name servers | `--ns` | `DNS_NAME_SERVERS` | **yes** | — |
| Port | `--port` | `DNS_PORT` | no | `53053` (CLI) / `53` (Docker) |
| Log level | `--log-level` | `DNS_LOG_LEVEL` | no | `info` |
| Min check interval | `--test-min-interval` | `DNS_TEST_MIN_INTERVAL` | no | `30` s |
| Check timeout | `--test-timeout` | `DNS_TEST_TIMEOUT` | no | `2` s |
| Alias zones | `--alias-zones` | `DNS_ALIAS_ZONES` | no | `[]` |
| DNSSEC key path | `--priv-key-path` | `DNS_PRIV_KEY_PATH` | no | _(DNSSEC disabled)_ |
| DNSSEC algorithm | `--priv-key-alg` | `DNS_PRIV_KEY_ALG` | no | `RSASHA256` |

---

## Full examples

### CLI — minimal

```bash
a-healthy-dns \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  --ns '["ns1.example.com"]'
```

### CLI — with DNSSEC and tuned intervals

```bash
a-healthy-dns \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["192.168.1.100","192.168.1.101"],"health_port":80},"api":{"ips":["192.168.1.200"],"health_port":8000}}' \
  --ns '["ns1.example.com","ns2.example.com"]' \
  --alias-zones '["www.example.net"]' \
  --port 53 \
  --test-min-interval 10 \
  --test-timeout 2 \
  --log-level info \
  --priv-key-path /etc/dns/private.pem \
  --priv-key-alg RSASHA256
```

### Docker — minimal

```bash
docker run -d \
  -p 53053:53053/udp \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  -e DNS_PORT="53053" \
  indisoluble/a-healthy-dns
```

### Docker — with DNSSEC

```bash
docker run -d \
  -p 53:53/udp \
  -v "$(pwd)/keys:/app/keys:ro" \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  -e DNS_PRIV_KEY_PATH="/app/keys/private.pem" \
  -e DNS_PRIV_KEY_ALG="RSASHA256" \
  indisoluble/a-healthy-dns
```
