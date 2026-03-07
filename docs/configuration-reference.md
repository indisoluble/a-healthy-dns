# Configuration Reference

## Overview

A Healthy DNS has two configuration surfaces:

- direct CLI arguments to `a-healthy-dns`
- Docker environment variables translated into CLI arguments by the container
  entrypoint

Structured values such as name-server lists, alias-zone lists, and zone
resolutions are passed as JSON strings in both modes.

For port-mapping, runtime behavior, smoke tests, and troubleshooting, use
[`docs/deployment-and-operations.md`](./deployment-and-operations.md).

## Configuration Surfaces

### Direct CLI

All configuration is provided at process start:

```bash
a-healthy-dns \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  --ns '["ns1.example.com"]'
```

### Docker Environment Variables

The image entrypoint converts environment variables into CLI arguments before
starting the process. `DNS_PORT` is always passed; other variables are passed
only when non-empty.

Minimal container example:

```bash
docker run -d \
  --name a-healthy-dns \
  -p 53053:53053/udp \
  -e DNS_PORT="53053" \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  indisoluble/a-healthy-dns
```

Use backend IPs that are reachable from inside the container.

Important: the CLI default port is `53053`, but the Docker image default
`DNS_PORT` is `53`. If you want the container to listen on another internal
port, set `DNS_PORT` explicitly and map the same container port in `docker run`
or Compose.

## Required Configuration

| CLI argument | Docker env | Type | Required | Notes |
| --- | --- | --- | --- | --- |
| `--hosted-zone` | `DNS_HOSTED_ZONE` | string | Yes | Primary authoritative zone. |
| `--zone-resolutions` | `DNS_ZONE_RESOLUTIONS` | JSON object string | Yes | Maps relative subdomains to backend IPs and one health-check port. |
| `--ns` | `DNS_NAME_SERVERS` | JSON array string | Yes | Non-empty list of authoritative name servers. |

## Optional Configuration

| CLI argument | Docker env | Type | Direct CLI default | Container behavior | Notes |
| --- | --- | --- | --- | --- | --- |
| `--port` | `DNS_PORT` | integer | `53053` | defaults to `53` because the image sets `DNS_PORT=53` | Parsed as an integer CLI value. |
| `--log-level` | `DNS_LOG_LEVEL` | string | `info` | empty env defers to CLI default | Allowed values are `debug`, `info`, `warning`, `error`, `critical`. |
| `--alias-zones` | `DNS_ALIAS_ZONES` | JSON array string | `[]` | empty env defers to CLI default | Additional zones that reuse the same relative names and backend targets. |
| `--test-min-interval` | `DNS_TEST_MIN_INTERVAL` | integer | `30` | empty env defers to CLI default | Minimum requested delay between health checks. |
| `--test-timeout` | `DNS_TEST_TIMEOUT` | integer | `2` | empty env defers to CLI default | TCP connect timeout per backend probe. |
| `--priv-key-path` | `DNS_PRIV_KEY_PATH` | string | unset | empty env disables DNSSEC | Path must be readable from inside the process or container. |
| `--priv-key-alg` | `DNS_PRIV_KEY_ALG` | string | `RSASHA256` | empty env defers to CLI default | Relevant only when a private-key path is supplied. |

## JSON Payload Shapes

### `--ns` / `DNS_NAME_SERVERS`

JSON array of strings:

```json
["ns1.example.com", "ns2.example.com"]
```

Rules:

- must parse as a JSON array
- must not be empty
- every entry must be a non-empty string
- labels may contain only alphanumeric characters or hyphens
- internal runtime form appends a trailing dot, so responses use absolute names

### `--alias-zones` / `DNS_ALIAS_ZONES`

JSON array of strings:

```json
["alias1.example.com", "alias2.example.com"]
```

Rules:

- must parse as a JSON array
- may be empty
- every entry must satisfy the same string and label rules as hosted and name
  server domains
- duplicates are collapsed internally
- matching prefers the most specific configured origin

### `--zone-resolutions` / `DNS_ZONE_RESOLUTIONS`

JSON object keyed by relative subdomain:

```json
{
  "www": {
    "ips": ["192.168.1.100", "192.168.1.101"],
    "health_port": 8080
  },
  "api": {
    "ips": ["192.168.1.200"],
    "health_port": 8000
  }
}
```

Rules:

- top-level value must parse as a JSON object
- top-level object must not be empty
- each key is a relative subdomain under the hosted zone and alias zones
- each subdomain value must be a JSON object
- each subdomain object must include:
  - `ips`: non-empty JSON array of IPv4 strings
  - `health_port`: JSON integer in the range `1..65535`

Current model limitation:

- one subdomain has one shared `health_port` for all of its IPs

## Validation and Normalization Rules

### Domain and Subdomain Names

The hosted zone, alias zones, name servers, and zone-resolution keys all use the
same validator.

Accepted form:

- string type only
- non-empty
- dot-separated labels
- each label contains only alphanumeric characters or hyphens

Rejected examples:

- empty strings
- labels with underscores, spaces, `@`, or `!`
- empty labels such as `example..com`
- non-string JSON values

Normalization behavior:

- hosted and alias zones are stored as absolute names internally
- name servers are normalized to absolute FQDN text with a trailing dot

### IPv4 Addresses

`ips` entries must be IPv4 strings with exactly four numeric octets, each in the
range `0..255`.

Accepted examples:

- `192.168.1.1`
- `010.020.030.040`
- `000.168.1.1`

Normalization behavior:

- leading zeros are stripped from each octet
- `010.020.030.040` becomes `10.20.30.40`
- repeated normalized IP/port pairs collapse to one backend entry because the
  runtime stores them as a set

### Ports

`health_port` must be a JSON integer between `1` and `65535`.

Examples:

- valid: `53`, `80`, `443`, `8080`, `65535`
- invalid: `"8080"`, `0`, `-1`, `65536`

For `--port`, the CLI parser requires an integer value, but explicit preflight
range validation is not performed in the config factory. Use a real UDP port.

### DNSSEC Inputs

When DNSSEC is enabled:

- `--priv-key-path` / `DNS_PRIV_KEY_PATH` must point to a readable private-key
  file
- `--priv-key-alg` / `DNS_PRIV_KEY_ALG` must match one of the DNSSEC algorithm
  text values accepted by `dnspython`
- startup fails if the key cannot be read or parsed with the selected algorithm

If the private-key path is omitted, DNSSEC is disabled and the algorithm setting
has no runtime effect.

## Common Failure Cases

- JSON argument is not quoted, so the shell splits it before the process sees it.
- JSON array expected, but JSON object provided for `--ns` or `--alias-zones`.
- `--zone-resolutions` is empty or not an object.
- `health_port` is given as a string instead of a JSON number.
- a subdomain omits `ips` or `health_port`.
- an IP address has the wrong number of octets or an octet outside `0..255`.
- a domain-like string contains unsupported characters such as `_` or `@`.
- a DNSSEC key path is set but the file is unreadable inside the container.

## Worked Examples

### Minimal Direct CLI

```bash
a-healthy-dns \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  --ns '["ns1.example.com"]'
```

### Direct CLI with Aliases and DNSSEC

```bash
a-healthy-dns \
  --hosted-zone example.com \
  --alias-zones '["example.net","example.org"]' \
  --zone-resolutions '{"www":{"ips":["192.168.1.100","192.168.1.101"],"health_port":8080}}' \
  --ns '["ns1.example.com","ns2.example.com"]' \
  --priv-key-path /etc/dns/private.pem \
  --priv-key-alg RSASHA256 \
  --port 53053 \
  --test-min-interval 15 \
  --test-timeout 3 \
  --log-level info
```

### Docker Compose Fragment

```yaml
services:
  a-healthy-dns:
    build: .
    ports:
      - "53053:53053/udp"
    environment:
      DNS_PORT: "53053"
      DNS_HOSTED_ZONE: "example.com"
      DNS_ALIAS_ZONES: '["example.net"]'
      DNS_ZONE_RESOLUTIONS: '{"www":{"ips":["192.168.1.100"],"health_port":8080}}'
      DNS_NAME_SERVERS: '["ns1.example.com"]'
      DNS_LOG_LEVEL: "info"
```

## Interface Differences to Remember

- Direct CLI defaults to port `53053`; the Docker image defaults to port `53`.
- Container mode uses shell strings for every variable, but JSON payloads still
  need valid JSON syntax because they are forwarded directly to the CLI.
- Empty `DNS_LOG_LEVEL`, `DNS_ALIAS_ZONES`, `DNS_TEST_MIN_INTERVAL`,
  `DNS_TEST_TIMEOUT`, and `DNS_PRIV_KEY_ALG` values defer to CLI defaults
  because the entrypoint omits those flags when the variables are empty.
- Name-server values are emitted as absolute FQDNs with trailing dots in runtime
  records.
