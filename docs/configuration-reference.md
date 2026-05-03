# Configuration Reference

Full parameter reference for **A Healthy DNS**, covering the `a-healthy-dns` CLI and Docker command arguments.

This document is the canonical home for CLI flags, default values, and configuration examples. It does not own deployment procedures, architecture details, or troubleshooting runbooks. Those topics live in [`docs/docker.md`](docker.md), [`docs/architecture.md`](architecture.md), and [`docs/troubleshooting.md`](troubleshooting.md).

> **Quick-start:** see [`README.md`](../README.md).  
> **Parameter behaviour details** (TTL derivation, DNSSEC timing): see [`docs/architecture.md`](architecture.md).

---

## Configuration surface

Use CLI flags for both direct execution and Docker execution:

```bash
a-healthy-dns --flag value ...
docker run indisoluble/a-healthy-dns --flag value ...
```

The Docker image entrypoint is `a-healthy-dns`, so arguments after the image name become normal CLI flags.

---

## Required parameters

These three must always be provided. The server will not start and exits with a non-zero status without them.

### Hosted zone

| Flag |
|---|
| `--hosted-zone` |

The domain name for which this server is authoritative.

```
--hosted-zone sub.domain.com
```

### Zone resolutions

| Flag |
|---|
| `--zone-resolutions` |

JSON object mapping subdomain names to their IP list and optional health check port.

There are two first-class record modes for each subdomain entry:

**Health-checked mode** — provide a dict with both `ips` and `health_port`:
```json
{
  "<subdomain>": {
    "ips": ["<ip1>", "<ip2>"],
    "health_port": <port>
  }
}
```

**Standard static mode** — provide a bare list of IPs; no TCP probe is performed and the IPs are published without a health gate:
```json
{
  "<subdomain>": ["<ip1>", "<ip2>"]
}
```

Both modes can be mixed in the same configuration.

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
- Standard static entries are not TCP health-checked and remain publishable without a health probe.

### Name servers

| Flag |
|---|
| `--ns` |

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

`zone-resolutions` is the surface for `A` records. Dict entries with a `health_port` use health-checked mode; bare-list entries use standard static mode. Do not add a nameserver hostname to `zone-resolutions` only to satisfy glue or delegation metadata.

Use an in-zone nameserver hostname only when that owner name is also a real service record (health-checked or standard static). Otherwise, use an out-of-zone nameserver hostname.

---

## Optional parameters

### Port

| Flag | Default |
|---|---|
| `--port` | `53053` |

UDP port the DNS server listens on.

> **Note:** Docker examples that expose container port `53` pass `--port 53` explicitly. The image uses `setcap cap_net_bind_service` on the Python binary to allow binding to privileged port 53 without root.

### Log level

| Flag | Default |
|---|---|
| `--log-level` | `info` |

Log verbosity. Accepted values: `debug`, `info`, `warning`, `error`, `critical`. The CLI parser currently expects these lowercase tokens.

### Minimum update interval

| Flag | Default |
|---|---|
| `--test-min-interval` | `30` |

Minimum seconds between consecutive zone update cycles. Entries with `health_port` are TCP health-checked during these cycles; standard static entries remain publishable without a TCP probe.

The effective interval is `max(test-min-interval, sum of per-health-checked-IP timeout × count + per-record overhead)`. See [docs/architecture.md § 6](architecture.md#6-interval-calculation-pattern) for the full formula.

### Health-check timeout

| Flag | Default |
|---|---|
| `--test-timeout` | `2` |

Maximum seconds to wait for a TCP connection during a health check. If the connection does not succeed within this time the IP is considered unhealthy.

### Alias zones

| Flag | Default |
|---|---|
| `--alias-zones` | `[]` |

JSON array of additional domain names that resolve to the same records as the hosted zone. Health checks are shared; no duplication occurs.

```json
["sub.domain.net", "sub.domain.org"]
```

See [docs/architecture.md § 8](architecture.md#8-multi-domain-support-via-zoneorigins) for the implementation pattern.

---

## DNSSEC parameters (optional)

Both parameters are optional. If `--priv-key-path` is omitted, DNSSEC signing is disabled entirely and no DNSSEC-generated records (`DNSKEY`, `NSEC`, `RRSIG`) are produced.

### Private key path

| Flag | Default |
|---|---|
| `--priv-key-path` | _(none)_ |

Path to a PEM-encoded DNSSEC private key file. In Docker, mount the key directory into `/app/keys` (read-only) and point this to the mounted path.

```bash
# Docker mount option before the image name:
-v "$(pwd)/keys:/app/keys:ro"

# CLI flag after the image name:
--priv-key-path /app/keys/private.pem
```

### Private key algorithm

| Flag | Default |
|---|---|
| `--priv-key-alg` | `RSASHA256` |

Algorithm used to sign the zone. Accepted values are the DNSSEC algorithm names supported by `dnspython` (e.g. `RSASHA256`, `RSASHA512`, `ECDSAP256SHA256`, `ECDSAP384SHA384`, `ED25519`, `ED448`). The full list is validated at startup against the installed `dnspython` version.

---

## Parameter summary table

| Parameter | CLI flag | Required | Default |
|---|---|---|---|
| Hosted zone | `--hosted-zone` | **yes** | — |
| Zone resolutions | `--zone-resolutions` | **yes** | — |
| Name servers | `--ns` | **yes** | — |
| Port | `--port` | no | `53053` |
| Log level | `--log-level` | no | `info` |
| Min update interval | `--test-min-interval` | no | `30` s |
| Check timeout | `--test-timeout` | no | `2` s |
| Alias zones | `--alias-zones` | no | `[]` |
| DNSSEC key path | `--priv-key-path` | no | _(DNSSEC disabled)_ |
| DNSSEC algorithm | `--priv-key-alg` | no | `RSASHA256` |

---

## Full examples

### CLI — mixed static and health-checked

```bash
a-healthy-dns \
  --hosted-zone sub.domain.com \
  --zone-resolutions '{"www":{"ips":["192.168.1.100"],"health_port":8080},"static":["192.168.1.200"]}' \
  --ns '["ns1.dns.example.net"]'
```

### Docker — with DNSSEC

```bash
docker run -d \
  -p 53:53/udp \
  -v "$(pwd)/keys:/app/keys:ro" \
  indisoluble/a-healthy-dns \
  --port 53 \
  --hosted-zone sub.domain.com \
  --zone-resolutions '{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  --ns '["ns1.dns.example.net"]' \
  --priv-key-path /app/keys/private.pem \
  --priv-key-alg RSASHA256
```
