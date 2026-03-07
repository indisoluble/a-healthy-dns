# Configuration

A Healthy DNS is configured entirely through CLI arguments (direct execution) or environment variables (Docker). There are no configuration files.

## CLI arguments

### Required

| Argument | Type | Description |
|----------|------|-------------|
| `--hosted-zone` | string | The domain name this DNS server is authoritative for. |
| `--zone-resolutions` | JSON string | Subdomains with IP addresses and health-check ports (see [Zone resolution schema](#zone-resolution-schema)). |
| `--ns` | JSON array string | Name servers responsible for this zone (e.g. `'["ns1.example.com", "ns2.example.com"]'`). |

### Optional — general

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--port` | int | `53053` | UDP port the DNS server listens on. |
| `--log-level` | string | `info` | Logging verbosity: `debug`, `info`, `warning`, `error`, `critical`. |

### Optional — connectivity tests

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--test-min-interval` | int | `30` | Minimum seconds between health-check cycles. |
| `--test-timeout` | int | `2` | Seconds to wait for each TCP health-check connection. |

### Optional — alias zones

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--alias-zones` | JSON array string | `[]` | Additional domains that resolve to the same records as `--hosted-zone`, without duplicating health checks. |

### Optional — DNSSEC

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--priv-key-path` | string | *(none)* | Path to a PEM-encoded DNSSEC private key. If omitted, DNSSEC signing is disabled. |
| `--priv-key-alg` | string | `RSASHA256` | DNSSEC signing algorithm. Must match the key type. |

## Docker environment variables

When running inside Docker, the entrypoint script converts environment variables to CLI arguments. The mapping is one-to-one:

| Environment variable | CLI equivalent | Default (Docker) | Required |
|---------------------|----------------|-------------------|----------|
| `DNS_HOSTED_ZONE` | `--hosted-zone` | *(empty — must set)* | **yes** |
| `DNS_ZONE_RESOLUTIONS` | `--zone-resolutions` | *(empty — must set)* | **yes** |
| `DNS_NAME_SERVERS` | `--ns` | *(empty — must set)* | **yes** |
| `DNS_PORT` | `--port` | `53` | no |
| `DNS_LOG_LEVEL` | `--log-level` | *(unset — uses CLI default: info)* | no |
| `DNS_TEST_MIN_INTERVAL` | `--test-min-interval` | *(unset — uses CLI default: 30)* | no |
| `DNS_TEST_TIMEOUT` | `--test-timeout` | *(unset — uses CLI default: 2)* | no |
| `DNS_ALIAS_ZONES` | `--alias-zones` | *(unset — uses CLI default: [])* | no |
| `DNS_PRIV_KEY_PATH` | `--priv-key-path` | *(unset — DNSSEC disabled)* | no |
| `DNS_PRIV_KEY_ALG` | `--priv-key-alg` | *(unset — uses CLI default: RSASHA256)* | no |

> **Note:** The Docker default for `DNS_PORT` is `53` (privileged port), not `53053` as in the CLI default. The container grants `cap_net_bind_service` to the Python interpreter to allow this.

## Zone resolution schema

The `--zone-resolutions` argument (or `DNS_ZONE_RESOLUTIONS` env var) accepts a JSON object:

```json
{
  "<subdomain>": {
    "ips": ["<ip1>", "<ip2>"],
    "health_port": <port>
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `<subdomain>` | string (key) | DNS label(s) for the subdomain. Must be alphanumeric plus hyphens; validated by `is_valid_subdomain()`. |
| `ips` | array of strings | IPv4 addresses to serve. Each is validated and normalized (leading zeros stripped). Must be non-empty. |
| `health_port` | int | TCP port used for health checks (1–65535). All IPs in the subdomain share this port. |

### Example

```json
{
  "www": {
    "ips": ["192.168.1.100", "192.168.1.101"],
    "health_port": 8080
  },
  "api": {
    "ips": ["10.0.1.200"],
    "health_port": 8000
  }
}
```

With `--hosted-zone example.com`, this produces:
- `www.example.com` → health-checked A records for `192.168.1.100` and `192.168.1.101` on port 8080.
- `api.example.com` → health-checked A record for `10.0.1.200` on port 8000.

## Alias zones

Alias zones allow multiple domains to share the same records and health-check state. Queries for any alias resolve against the primary zone.

```bash
a-healthy-dns \
  --hosted-zone primary.com \
  --alias-zones '["alias1.com", "alias2.com"]' \
  --zone-resolutions '{"www": {"ips": ["192.168.1.100"], "health_port": 8080}}' \
  --ns '["ns1.primary.com"]'
```

All three domains resolve `www` to the same IP:
- `www.primary.com` → `192.168.1.100`
- `www.alias1.com` → `192.168.1.100`
- `www.alias2.com` → `192.168.1.100`

A single health check covers all three.

## DNSSEC

DNSSEC signing is enabled by providing a private key:

```bash
a-healthy-dns \
  --hosted-zone example.com \
  --zone-resolutions '{"www": {"ips": ["192.168.1.100"], "health_port": 8080}}' \
  --ns '["ns1.example.com"]' \
  --priv-key-path /path/to/private.pem \
  --priv-key-alg RSASHA256
```

- The key must be a PEM-encoded private key compatible with `dnspython`'s `dns.dnssecalgs`.
- The zone is signed on every rebuild. Re-signing happens automatically before signature expiration.
- Signature lifetime is calculated from the health-check interval (see [TTL strategy](system-patterns.md#ttl-strategy) in system-patterns).

## Health-check behavior

- **Mechanism:** TCP 3-way handshake to each IP on its `health_port` via `socket.create_connection()`.
- **Healthy IPs** are included in DNS A record responses.
- **Unhealthy IPs** are excluded. If all IPs for a subdomain are unhealthy, the A record is omitted from the zone (query returns `NXDOMAIN`).
- **TTL:** A record TTL = `2 × max_interval`, where `max_interval` is the effective health-check cycle duration. Clients re-query before health state becomes two cycles stale.
- **Cycle frequency:** health checks run every `--test-min-interval` seconds (or longer if the check cycle itself takes more time).
