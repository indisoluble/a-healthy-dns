# Configuration Reference

## Scope

This document is the authoritative configuration reference for `a-healthy-dns`.

It covers:

1. CLI arguments and defaults.
2. JSON payload schemas for complex arguments.
3. Docker environment variable mapping to CLI.
4. Validation rules and common startup failures.

## Configuration Surfaces

The service accepts configuration through two surfaces:

1. Direct CLI arguments (`a-healthy-dns ...`).
2. Docker environment variables converted to CLI flags by the image entrypoint.

Source anchors:

- `indisoluble/a_healthy_dns/main.py:62`
- `indisoluble/a_healthy_dns/main.py:248`
- `Dockerfile:84`

## CLI Reference

### Required arguments

| Flag | Type | Description | Validation |
| --- | --- | --- | --- |
| `--hosted-zone` | string | Primary authoritative zone (for example `example.com`) | Must be a non-empty domain/subdomain string with labels containing only alphanumeric chars or `-` |
| `--zone-resolutions` | JSON string | Mapping of subdomains to IP lists and health ports | Must parse as non-empty object with valid per-subdomain entries |
| `--ns` | JSON string | Name-server list for the zone | Must parse as non-empty array of valid domain/subdomain strings |

Source anchors:

- `indisoluble/a_healthy_dns/main.py:131`
- `indisoluble/a_healthy_dns/main.py:149`
- `indisoluble/a_healthy_dns/main.py:176`
- `indisoluble/a_healthy_dns/dns_server_config_factory.py:50`
- `indisoluble/a_healthy_dns/dns_server_config_factory.py:129`
- `indisoluble/a_healthy_dns/dns_server_config_factory.py:161`

### Optional arguments

| Flag | Type | Default | Description | Notes |
| --- | --- | --- | --- | --- |
| `--port` | int | `53053` | UDP DNS listen port | Runtime bind port |
| `--log-level` | enum | `info` | Logging verbosity | One of Python standard levels except `NOTSET` |
| `--alias-zones` | JSON string | `[]` | Additional zones sharing the same records | Must parse as array of valid domain/subdomain strings |
| `--test-min-interval` | int | `30` | Minimum time between health-check cycles | Must be positive at updater init |
| `--test-timeout` | int | `2` | TCP connect timeout per endpoint check (seconds) | Must be positive at updater init |
| `--priv-key-path` | string | unset | DNSSEC private key file path | If set, file must be readable and valid PEM key for chosen algorithm |
| `--priv-key-alg` | enum string | `RSASHA256` | DNSSEC signing algorithm | Must be among dnspython-supported algorithms accepted by parser |

Source anchors:

- `indisoluble/a_healthy_dns/main.py:115`
- `indisoluble/a_healthy_dns/main.py:122`
- `indisoluble/a_healthy_dns/main.py:140`
- `indisoluble/a_healthy_dns/main.py:162`
- `indisoluble/a_healthy_dns/main.py:169`
- `indisoluble/a_healthy_dns/main.py:185`
- `indisoluble/a_healthy_dns/main.py:191`
- `indisoluble/a_healthy_dns/dns_server_zone_updater.py:81`

## JSON Schemas

### `--zone-resolutions`

Expected shape:

```json
{
  "subdomain": {
    "ips": ["192.168.1.10", "192.168.1.11"],
    "health_port": 8080
  }
}
```

Rules:

1. Top-level value must be a non-empty object.
2. Each key is the subdomain label/name for a record set.
3. Each subdomain value must be an object containing:
   - `ips`: non-empty array of IPv4 strings.
   - `health_port`: integer in range `1..65535`.
4. IPs are normalized by removing leading zeros per octet (for example `0102.018.001.01` -> `102.18.1.1`).
5. Duplicate IP entries for the same subdomain collapse in-memory because records use set semantics.

Source anchors:

- `indisoluble/a_healthy_dns/dns_server_config_factory.py:133`
- `indisoluble/a_healthy_dns/dns_server_config_factory.py:145`
- `indisoluble/a_healthy_dns/dns_server_config_factory.py:92`
- `indisoluble/a_healthy_dns/dns_server_config_factory.py:111`
- `indisoluble/a_healthy_dns/tools/is_valid_ip.py:12`
- `indisoluble/a_healthy_dns/tools/is_valid_port.py:12`
- `indisoluble/a_healthy_dns/tools/normalize_ip.py:10`
- `indisoluble/a_healthy_dns/records/a_healthy_record.py:32`
- `tests/indisoluble/a_healthy_dns/test_dns_server_config_factory.py:35`
- `tests/indisoluble/a_healthy_dns/test_dns_server_config_factory.py:100`

### `--ns`

Expected shape:

```json
["ns1.example.com", "ns2.example.com"]
```

Rules:

1. Must parse as non-empty JSON array.
2. Each entry must pass subdomain/domain validation.
3. Values are converted to absolute form with trailing `.` internally.

Source anchors:

- `indisoluble/a_healthy_dns/dns_server_config_factory.py:163`
- `indisoluble/a_healthy_dns/dns_server_config_factory.py:174`
- `indisoluble/a_healthy_dns/dns_server_config_factory.py:185`

### `--alias-zones`

Expected shape:

```json
["alias1.example.com", "alias2.example.com"]
```

Rules:

1. Must parse as JSON array (empty allowed).
2. Each entry must be a valid domain/subdomain string.
3. Matching uses the most-specific origin first when multiple origins overlap.

Source anchors:

- `indisoluble/a_healthy_dns/dns_server_config_factory.py:54`
- `indisoluble/a_healthy_dns/dns_server_config_factory.py:59`
- `indisoluble/a_healthy_dns/records/zone_origins.py:33`
- `indisoluble/a_healthy_dns/records/zone_origins.py:43`

## Validation Rules Summary

### Domain/subdomain strings

1. Must be a string.
2. Must be non-empty.
3. Labels may contain only alphanumeric characters and `-`.

Source anchor:

- `indisoluble/a_healthy_dns/tools/is_valid_subdomain.py:12`

### IPv4 strings

1. Must be a string with exactly 4 octets.
2. Each octet must be numeric and within `0..255`.

Source anchor:

- `indisoluble/a_healthy_dns/tools/is_valid_ip.py:12`

### Port values

1. Must be an integer.
2. Must be within `1..65535`.

Source anchor:

- `indisoluble/a_healthy_dns/tools/is_valid_port.py:12`

## Docker Environment Variable Mapping

The Docker image maps environment variables to CLI flags.

| Environment variable | CLI flag | Required in container | Container default |
| --- | --- | --- | --- |
| `DNS_HOSTED_ZONE` | `--hosted-zone` | yes | empty (must be provided) |
| `DNS_ZONE_RESOLUTIONS` | `--zone-resolutions` | yes | empty (must be provided) |
| `DNS_NAME_SERVERS` | `--ns` | yes | empty (must be provided) |
| `DNS_PORT` | `--port` | no | `53` |
| `DNS_LOG_LEVEL` | `--log-level` | no | empty (flag omitted) |
| `DNS_ALIAS_ZONES` | `--alias-zones` | no | empty (flag omitted) |
| `DNS_TEST_MIN_INTERVAL` | `--test-min-interval` | no | empty (flag omitted) |
| `DNS_TEST_TIMEOUT` | `--test-timeout` | no | empty (flag omitted) |
| `DNS_PRIV_KEY_PATH` | `--priv-key-path` | no | empty (flag omitted) |
| `DNS_PRIV_KEY_ALG` | `--priv-key-alg` | no | empty (flag omitted) |

Notes:

1. Docker default port behavior differs from direct CLI defaults: container default is `53`, CLI default is `53053`.
2. Required Docker variables are enforced before process startup.
3. JSON-valued env vars must be quoted correctly for the shell.

Source anchors:

- `Dockerfile:66`
- `Dockerfile:86`
- `Dockerfile:90`
- `Dockerfile:94`
- `Dockerfile:98`
- `indisoluble/a_healthy_dns/main.py:59`

## Startup Failure Behavior

If configuration validation fails:

1. `make_config` returns `None`.
2. Main process returns early without starting updater or UDP server.
3. Error context is logged at startup.

Common failure causes:

1. Invalid JSON in `--zone-resolutions`, `--ns`, or `--alias-zones`.
2. Empty arrays or missing keys in subdomain entries.
3. Invalid IP or port formats.
4. Invalid DNSSEC algorithm or unreadable private key path.

Source anchors:

- `indisoluble/a_healthy_dns/dns_server_config_factory.py:55`
- `indisoluble/a_healthy_dns/dns_server_config_factory.py:135`
- `indisoluble/a_healthy_dns/dns_server_config_factory.py:165`
- `indisoluble/a_healthy_dns/dns_server_config_factory.py:197`
- `indisoluble/a_healthy_dns/main.py:222`
- `indisoluble/a_healthy_dns/main.py:223`
- `tests/indisoluble/a_healthy_dns/test_dns_server_config_factory.py:136`
- `tests/indisoluble/a_healthy_dns/test_dns_server_config_factory.py:166`
- `tests/indisoluble/a_healthy_dns/test_dns_server_config_factory.py:291`

## End-to-End Configuration Examples

### Minimal CLI

```bash
a-healthy-dns \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  --ns '["ns1.example.com"]'
```

### CLI with aliases and DNSSEC

```bash
a-healthy-dns \
  --hosted-zone primary.com \
  --alias-zones '["alias1.com","alias2.com"]' \
  --zone-resolutions '{"www":{"ips":["10.0.0.10","10.0.0.11"],"health_port":80}}' \
  --ns '["ns1.primary.com","ns2.primary.com"]' \
  --priv-key-path /etc/dns/private.pem \
  --priv-key-alg RSASHA256
```

### Minimal Docker

```bash
docker run --rm \
  -p 53053:53/udp \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  indisoluble/a-healthy-dns
```

Source anchors:

- `README.md:23`
- `README.md:49`
