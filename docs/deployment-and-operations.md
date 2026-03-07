# Deployment and Operations

## Overview

This guide covers how to run A Healthy DNS in production-like environments,
what the container image does at startup, how to verify the service is working,
and what to check when it is not.

For option syntax and JSON payload details, use
[`docs/configuration-reference.md`](./configuration-reference.md).

## Deployment Modes

### Direct Process

Use direct CLI execution when:

- you want to run the service under your own process manager
- you do not need the packaged container image
- you want the CLI defaults directly, including the default port `53053`

Example:

```bash
a-healthy-dns \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  --ns '["ns1.example.com"]' \
  --port 53053
```

### Docker Container

Use the container image when you want:

- a packaged runtime with dependencies included
- a non-root execution model
- standard container operations such as `docker logs`, `docker stop`, and
  Compose deployment

Minimal example:

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

### Docker Compose

Use Compose when you want repeatable local or single-host deployments:

```bash
cp docker-compose.example.yml docker-compose.yml
docker-compose -f docker-compose.yml config
docker-compose up -d
```

## Container Runtime Characteristics

The image is opinionated in a few important ways:

- multi-stage build to reduce runtime image size
- non-root runtime user `appuser` with uid/gid `10000`
- `tini` as PID 1 for signal handling and child-process reaping
- `/app/keys` reserved for DNSSEC key material
- environment variables translated into CLI arguments before startup

Default container behavior:

- internal listen port defaults to `53`
- `53/udp` is exposed from the image
- the runtime process is `a-healthy-dns`

## Privileged Port Binding

There are two common ways to expose DNS:

### Internal High Port

Keep the process on an unprivileged container port and map a host port to it:

```bash
docker run -d \
  -p 53053:53053/udp \
  -e DNS_PORT="53053" \
  ...
```

This is the simplest setup for local testing.

### Internal Port 53

Run the process on port `53` inside the container:

```bash
docker run -d \
  -p 53:53/udp \
  -e DNS_PORT="53" \
  ...
```

The image prepares for privileged-port binding by granting
`cap_net_bind_service` to the Python interpreter. The Compose example also
retains `NET_BIND_SERVICE` while dropping all other capabilities.

Operational rule:

- keep `DNS_PORT` aligned with the container-side port in your `-p` or Compose
  port mapping

## Startup Sequence

At process start:

1. logging is configured
2. all configuration is validated
3. the first zone snapshot is built before the repeating health-check loop starts
4. the UDP server starts listening on the configured port
5. background health checks continue to update the zone over time

Operational implication:

- startup failures are usually configuration or DNSSEC key problems
- a running process does not mean backends are healthy; it only means the server
  started and accepted the configuration

## Backend Reachability Requirements

Health checks are TCP connectivity checks to each configured `ip:health_port`
pair.

This means:

- the DNS process or container must be able to route to backend IPs
- firewalls and network policy must allow outbound TCP to the health-check ports
- unhealthy or unreachable backends are omitted from A answers

If all backends for one subdomain are unhealthy:

- the subdomain's A rdataset is omitted from the zone
- A queries for that missing name resolve as `NXDOMAIN`

## DNSSEC Key Mounting

When DNSSEC is enabled in containers:

1. mount the host directory read-only
2. point `DNS_PRIV_KEY_PATH` at the in-container file path
3. ensure the key file is readable by the container's runtime user

Example:

```bash
mkdir -p ./keys

docker run -d \
  --name a-healthy-dns \
  -p 53:53/udp \
  -v "$(pwd)/keys:/app/keys:ro" \
  -e DNS_PORT="53" \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  -e DNS_PRIV_KEY_PATH="/app/keys/private.pem" \
  -e DNS_PRIV_KEY_ALG="RSASHA256" \
  indisoluble/a-healthy-dns
```

Because the container runs as `appuser`, a mounted key that is readable only by
host root may still fail inside the container.

## Logging

### Log Levels

Supported levels:

- `debug`
- `info`
- `warning`
- `error`
- `critical`

Use `debug` when diagnosing:

- backend health flaps
- unexpected `NXDOMAIN` responses
- DNSSEC signing issues
- startup argument forwarding inside the container

### Log Access

Container logs:

```bash
docker logs a-healthy-dns
docker logs -f a-healthy-dns
```

The image entrypoint also prints the exact CLI arguments it is about to launch,
which is useful when checking Docker environment-variable mapping.

## Operational Verification

### Basic Smoke Test

Check that the container is running:

```bash
docker ps | grep a-healthy-dns
```

Then query it:

```bash
dig @127.0.0.1 -p 53053 www.example.com A
```

### Expected Query Behavior

Operationally useful expectations:

- configured healthy A names return an answer section with backend IPs
- configured names queried for unsupported record types return `NOERROR` with no
  answer
- missing subdomains return `NXDOMAIN`
- names outside the hosted or alias zones return `NXDOMAIN`
- zone apex NS queries return the configured name servers

Examples:

```bash
dig +short @127.0.0.1 -p 53053 www.example.com A
dig +noall +comments @127.0.0.1 -p 53053 www.example.com AAAA
dig +noall +comments @127.0.0.1 -p 53053 missing.example.com A
dig +short @127.0.0.1 -p 53053 example.com NS
```

### Alias-Zone Verification

If alias zones are configured, verify both primary and alias names:

```bash
dig +short @127.0.0.1 -p 53053 www.primary.example A
dig +short @127.0.0.1 -p 53053 www.alias.example A
```

The Docker CI workflow validates exactly this behavior against hosted and alias
zones plus expected `NOERROR` and `NXDOMAIN` statuses.

## Runtime Operations

### Restart

Container restart:

```bash
docker restart a-healthy-dns
```

Compose restart:

```bash
docker-compose restart a-healthy-dns
```

### Stop

Container stop:

```bash
docker stop a-healthy-dns
```

The process handles `SIGINT` and `SIGTERM`, shuts down the UDP server, and then
stops the background updater thread.

### Interactive Debugging

Run in foreground:

```bash
docker run --rm -it \
  -e DNS_LOG_LEVEL="debug" \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  indisoluble/a-healthy-dns
```

Open a shell in a running container:

```bash
docker exec -it a-healthy-dns sh
```

## Troubleshooting

### Container Exits Immediately

Likely causes:

- required environment variables are missing
- JSON payloads are malformed
- DNSSEC key path is set but unreadable
- DNSSEC algorithm does not match the key material

Check:

```bash
docker logs a-healthy-dns
```

### Server Starts but A Answers Are Empty or Missing

Likely causes:

- backend IPs are unreachable from the container
- the health-check port is wrong
- all backends are currently unhealthy

Check:

- debug logs for TCP connectivity failures
- network reachability from the container to the backend IPs
- whether you are querying the right hosted or alias zone name

### `NXDOMAIN` for an Alias Zone You Expected to Work

Likely causes:

- alias zone was not configured
- the queried name is outside the configured alias hierarchy
- the alias text is malformed and was rejected at startup

Check:

- startup configuration
- `docker logs`
- primary-zone query versus alias-zone query side by side

### Port Appears Closed

Likely causes:

- `DNS_PORT` and container port mapping do not match
- you mapped TCP instead of UDP
- you are querying the host on the wrong port

Check:

```bash
docker ps
docker logs a-healthy-dns
```

### DNSSEC Startup Failure

Likely causes:

- wrong in-container key path
- unreadable mounted key file
- mismatched algorithm

Check:

- mounted path under `/app/keys`
- read permissions for the runtime user
- `DNS_PRIV_KEY_ALG`

## Operational Recommendations

- Prefer explicit `DNS_PORT` in containers so host and container port mappings
  are obvious.
- Mount DNSSEC keys read-only.
- Use `debug` logs only while diagnosing issues; `info` is a better steady-state
  default.
- Validate Compose files with `docker-compose config` before deployment.
- Re-run smoke tests after changing configuration, port mappings, or backend
  network placement.
