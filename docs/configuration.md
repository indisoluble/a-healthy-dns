# Configuration Reference

A Healthy DNS accepts configuration via CLI arguments (direct invocation) or Docker environment variables (container deployment). Both surfaces map 1:1 to the same underlying parameters.

---

## Quick reference table

| CLI argument | Docker env var | Required | Default | Description |
|---|---|---|---|---|
| `--hosted-zone` | `DNS_HOSTED_ZONE` | **Yes** | — | Primary zone name (e.g. `example.com`) |
| `--zone-resolutions` | `DNS_ZONE_RESOLUTIONS` | **Yes** | — | Subdomain health-check config (JSON) |
| `--ns` | `DNS_NAME_SERVERS` | **Yes** | — | Name servers for the zone (JSON array) |
| `--port` | `DNS_PORT` | No | `53053` (`53` in Docker) | Listening port |
| `--log-level` | `DNS_LOG_LEVEL` | No | `info` | Log verbosity |
| `--test-min-interval` | `DNS_TEST_MIN_INTERVAL` | No | `30` | Minimum seconds between health-check cycles |
| `--test-timeout` | `DNS_TEST_TIMEOUT` | No | `2` | TCP probe timeout in seconds |
| `--alias-zones` | `DNS_ALIAS_ZONES` | No | `[]` | Additional zones that resolve to the same records (JSON array) |
| `--priv-key-path` | `DNS_PRIV_KEY_PATH` | No | — | Path to DNSSEC private key PEM file |
| `--priv-key-alg` | `DNS_PRIV_KEY_ALG` | No | `RSASHA256` | DNSSEC signing algorithm |

> **Docker default port note:** The `Dockerfile` sets `DNS_PORT=53` as its default so the container binds to the standard DNS port. When running a non-Docker install, the default is `53053`.

---

## Parameter details

### `--hosted-zone` / `DNS_HOSTED_ZONE` _(required)_

The fully-qualified domain name for which this server is authoritative.

```
--hosted-zone example.com
```

---

### `--zone-resolutions` / `DNS_ZONE_RESOLUTIONS` _(required)_

A JSON object declaring one entry per subdomain. Each entry specifies the list of backend IPs and the TCP port to probe for health checks.

**Schema:**

```json
{
  "<subdomain>": {
    "ips": ["<ip1>", "<ip2>", ...],
    "health_port": <port>
  }
}
```

- `<subdomain>` — relative label (e.g. `www`, `api`); combined with `--hosted-zone` to form the FQDN.
- `ips` — non-empty list of IPv4 addresses.
- `health_port` — TCP port to probe on each IP.

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

On the CLI, pass the JSON as a single-quoted string:

```bash
--zone-resolutions '{"www":{"ips":["192.168.1.100"],"health_port":8080}}'
```

---

### `--ns` / `DNS_NAME_SERVERS` _(required)_

A JSON array of fully-qualified name server names for the zone. Used to populate the NS and SOA records.

```bash
--ns '["ns1.example.com", "ns2.example.com"]'
```

The first element in the array becomes the primary NS in the SOA record.

---

### `--port` / `DNS_PORT` _(optional, default: `53053` / `53` in Docker)_

The UDP port the DNS server listens on.

- Port `53` requires the `NET_BIND_SERVICE` Linux capability (granted by default in the Docker image via `setcap`).
- When running without Docker, use `53053` to avoid requiring root, or grant the capability manually.

```bash
--port 53
```

---

### `--log-level` / `DNS_LOG_LEVEL` _(optional, default: `info`)_

Controls log verbosity. Valid values: `debug`, `info`, `warning`, `error`, `critical`.

```bash
--log-level debug
```

---

### `--test-min-interval` / `DNS_TEST_MIN_INTERVAL` _(optional, default: `30`)_

The minimum number of seconds between health-check cycles. A cycle probes every configured IP.

The actual interval may be longer if a full probe cycle (number of IPs × `--test-timeout` + per-record overhead) exceeds this value. See `docs/system-patterns.md` — _Interval / timing calculation pattern_.

```bash
--test-min-interval 15
```

---

### `--test-timeout` / `DNS_TEST_TIMEOUT` _(optional, default: `2`)_

Maximum seconds to wait for a TCP connection to succeed before declaring the probe failed.

```bash
--test-timeout 3
```

---

### `--alias-zones` / `DNS_ALIAS_ZONES` _(optional, default: `[]`)_

A JSON array of additional domain names that resolve to the same set of health-checked A records as `--hosted-zone`. No data is duplicated; the same in-memory zone is served for all origins.

```bash
--alias-zones '["alias1.com", "alias2.com"]'
```

With `--hosted-zone primary.com` and the above, queries for `www.primary.com`, `www.alias1.com`, and `www.alias2.com` all return the same healthy IPs.

---

### `--priv-key-path` / `DNS_PRIV_KEY_PATH` _(optional)_

Path to a PEM-encoded DNSSEC private key file. When provided, the zone is signed with DNSSEC (RRSIG + DNSKEY records), and signatures are automatically rotated before expiry.

When running in Docker, mount the key file as a volume:

```bash
docker run \
  -v "$(pwd)/keys:/app/keys:ro" \
  -e DNS_PRIV_KEY_PATH="/app/keys/private.pem" \
  ...
```

Omit this parameter entirely to run without DNSSEC.

---

### `--priv-key-alg` / `DNS_PRIV_KEY_ALG` _(optional, default: `RSASHA256`)_

The algorithm corresponding to the private key provided via `--priv-key-path`. Only meaningful when DNSSEC is enabled.

Valid values are the algorithm names supported by dnspython's `dns.dnssectypes.Algorithm` (e.g. `RSASHA256`, `RSASHA512`, `ECDSAP256SHA256`, `ECDSAP384SHA384`, `ED25519`, `ED448`).

```bash
--priv-key-alg ECDSAP256SHA256
```

---

## Full CLI example

```bash
a-healthy-dns \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["10.0.1.100","10.0.1.101"],"health_port":80},"api":{"ips":["10.0.1.200"],"health_port":8080}}' \
  --ns '["ns1.example.com", "ns2.example.com"]' \
  --port 53 \
  --log-level info \
  --test-min-interval 15 \
  --test-timeout 2 \
  --alias-zones '["www.other.com"]' \
  --priv-key-path /etc/dns/private.pem \
  --priv-key-alg RSASHA256
```

---

## Full Docker Compose example

See [`docker-compose.example.yml`](../docker-compose.example.yml) for a ready-to-copy template. Key environment block:

```yaml
environment:
  DNS_HOSTED_ZONE: "example.com"
  DNS_ZONE_RESOLUTIONS: '{"www":{"ips":["192.168.1.100","192.168.1.101"],"health_port":8080}}'
  DNS_NAME_SERVERS: '["ns1.example.com", "ns2.example.com"]'
  DNS_PORT: "53053"
  DNS_LOG_LEVEL: "info"
  DNS_TEST_MIN_INTERVAL: "30"
  DNS_TEST_TIMEOUT: "2"
  # DNS_ALIAS_ZONES: '[]'
  # DNS_PRIV_KEY_PATH: "/app/keys/private.pem"
  # DNS_PRIV_KEY_ALG: "RSASHA256"
```
