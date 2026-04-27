# Configuration Reference

Full parameter reference for **A Healthy DNS**, covering both the CLI (`a-healthy-dns`) and Docker environment variables.

This document is the canonical home for CLI flags, Docker environment variables, default values, and configuration examples. It does not own deployment procedures, architecture details, or troubleshooting runbooks. Those topics live in [`docs/docker.md`](docker.md), [`docs/system-patterns.md`](system-patterns.md), and [`docs/troubleshooting.md`](troubleshooting.md).

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

These three must always be provided. The server will not start and exits with a non-zero status without them.

### Hosted zone

| Surface | Name |
|---|---|
| CLI | `--hosted-zone` |
| Docker | `DNS_HOSTED_ZONE` |

The domain name for which this server is authoritative.

```
--hosted-zone sub.domain.com
```

### Zone resolutions

| Surface | Name |
|---|---|
| CLI | `--zone-resolutions` |
| Docker | `DNS_ZONE_RESOLUTIONS` |

JSON object mapping subdomain names to their IP list and optional health check port.

There are two formats for each subdomain entry:

**Health-checked** — provide a dict with both `ips` and `health_port`:
```json
{
  "<subdomain>": {
    "ips": ["<ip1>", "<ip2>"],
    "health_port": <port>
  }
}
```

**Always-on** — provide a bare list of IPs (no health check is performed):
```json
{
  "<subdomain>": ["<ip1>", "<ip2>"]
}
```

Both formats can be mixed in the same configuration.

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
  },
  "static": ["192.168.1.200"]
}
```

- Each `<subdomain>` is relative to the hosted zone (e.g. `www` → `www.sub.domain.com`).
- `ips` must be valid IPv4 addresses (IPv6/AAAA is not supported).
- `health_port` is the TCP port used for health checks. It is required when using the dict format.
- All IPs for a subdomain share the same health port.
- Always-on IPs (bare list format) are never TCP health-checked; the zone updater treats them as healthy during refresh cycles.

### Name servers

| Surface | Name |
|---|---|
| CLI | `--ns` |
| Docker | `DNS_NAME_SERVERS` |

JSON array of fully-qualified name server hostnames for the zone's apex `NS` record. Single-label hostnames such as `ns1` are rejected. Provide names without a trailing root dot; the server normalizes them to absolute DNS names internally.

```json
["ns1.dns.example.net", "ns2.dns.example.net"]
```

This parameter publishes only two pieces of data inside the configured hosted zone:

- the zone apex `NS` RRset,
- and the SOA primary nameserver value, using the first hostname in the JSON array.

It does not create `A` records for the nameserver hostnames.

#### Recommended nameserver naming

For delegated subzones, prefer nameserver hostnames outside the delegated child zone. The nameserver hostname usually lives in the parent zone or in another DNS zone you operate.

Example:

| Role | Example |
|---|---|
| Parent / operator zone | `example.test` |
| Delegated hosted zone served by this project | `app.example.test` |
| Recommended nameserver hostname | `ns-192-0-2-53.example.test` |
| Less convenient in-zone nameserver hostname | `ns-192-0-2-53.app.example.test` |

With the recommended out-of-zone pattern:

- the `app.example.test` zone publishes `NS ns-192-0-2-53.example.test.`,
- the `A` record for `ns-192-0-2-53.example.test` is served by the authoritative DNS for `example.test`,
- and this `app.example.test` server does not need to serve an address record for its own nameserver hostname.

If you query this server directly for `ns-192-0-2-53.example.test A`, the name is outside its hosted zone. A `REFUSED` response is expected and matches this project's authoritative-only behavior.

#### In-zone nameserver names

An in-zone nameserver name such as `ns-192-0-2-53.app.example.test` is DNS-valid, but it is more operationally demanding:

- the parent delegation needs glue for that hostname,
- the child zone should also serve authoritative address data for that same hostname,
- and this project does not currently provide a separate static address-record surface for nameserver glue.

`zone-resolutions` is the surface for `A` records. Dict entries with a `health_port` are health-checked; bare-list entries are always-on. Do not add a nameserver hostname to `zone-resolutions` only to satisfy glue or delegation metadata.

Use an in-zone nameserver hostname only when that owner name is also a real service record (health-checked or always-on). Otherwise, use an out-of-zone nameserver hostname.

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

Log verbosity. Accepted values: `debug`, `info`, `warning`, `error`, `critical`. The CLI parser currently expects these lowercase tokens.

### Minimum health-check interval

| Surface | Name | Default |
|---|---|---|
| CLI | `--test-min-interval` | `30` |
| Docker | `DNS_TEST_MIN_INTERVAL` | _(not set — falls back to CLI default)_ |

Minimum seconds between consecutive zone update cycles. Entries with `health_port` are TCP health-checked during these cycles; bare-list entries are treated as healthy without a TCP probe.

The effective interval is `max(test-min-interval, sum of per-health-checked-IP timeout × count + per-record overhead)`. See [docs/system-patterns.md § 6](system-patterns.md#6-interval-calculation-pattern) for the full formula.

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
["sub.domain.net", "sub.domain.org"]
```

See [docs/system-patterns.md § 8](system-patterns.md#8-multi-domain-support-via-zoneorigins) for the implementation pattern.

---

## DNSSEC parameters (optional)

Both parameters are optional. If `--priv-key-path` / `DNS_PRIV_KEY_PATH` is omitted, DNSSEC signing is disabled entirely and no DNSSEC-generated records (`DNSKEY`, `NSEC`, `RRSIG`) are produced.

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
  --hosted-zone sub.domain.com \
  --zone-resolutions '{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  --ns '["ns1.dns.example.net"]'
```

### Docker — with DNSSEC

```bash
docker run -d \
  -p 53:53/udp \
  -v "$(pwd)/keys:/app/keys:ro" \
  -e DNS_HOSTED_ZONE="sub.domain.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.dns.example.net"]' \
  -e DNS_PRIV_KEY_PATH="/app/keys/private.pem" \
  -e DNS_PRIV_KEY_ALG="RSASHA256" \
  indisoluble/a-healthy-dns
```
