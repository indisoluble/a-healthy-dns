# Operations and Troubleshooting

## Scope

This document provides runtime operations guidance and troubleshooting playbooks for `a-healthy-dns`.

It focuses on:

1. Service health checks.
2. DNS behavior verification.
3. Common failure patterns and recovery steps.
4. Operational safety during restarts and shutdown.

## Runtime Model (Operator View)

At runtime, the service has two cooperating loops:

1. UDP DNS request handling loop (serves authoritative responses).
2. Background zone-updater loop (checks backend TCP health and rebuilds zone state).

Source anchors:

- `indisoluble/a_healthy_dns/main.py:233`
- `indisoluble/a_healthy_dns/dns_server_udp_handler.py:68`
- `indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py:47`

## Quick Health Checklist

Run these in order when investigating an incident:

1. Process/container is running.
2. Service is listening on expected UDP port.
3. Configuration values are valid JSON and include required fields.
4. DNS queries return expected status codes (`NOERROR`, `NXDOMAIN`, `FORMERR`) for known probes.
5. Backend targets are reachable on configured health ports.

Reference anchors:

- `.github/workflows/test-docker.yml:64`
- `indisoluble/a_healthy_dns/dns_server_config_factory.py:133`
- `indisoluble/a_healthy_dns/dns_server_udp_handler.py:36`
- `indisoluble/a_healthy_dns/dns_server_udp_handler.py:53`
- `indisoluble/a_healthy_dns/tools/can_create_connection.py:13`

## Standard Verification Commands

### 1) Confirm process/container state

```bash
docker ps | grep a-healthy-dns
docker logs a-healthy-dns
docker logs -f a-healthy-dns
```

Source anchor:

- `.github/workflows/test-docker.yml:65`

### 2) Probe DNS answers

Minimal probe:

```bash
dig @127.0.0.1 -p 53053 www.example.com A
```

Status-focused probe:

```bash
dig +time=1 +tries=1 +noall +comments @127.0.0.1 -p 53053 www.example.com A
```

Type-mismatch probe (existing name, unsupported type):

```bash
dig +time=1 +tries=1 +noall +comments @127.0.0.1 -p 53053 www.example.com AAAA
```

Source anchors:

- `README.md:35`
- `.github/workflows/test-docker.yml:105`
- `.github/workflows/test-docker.yml:145`

### 3) Verify NS records

```bash
dig +short +time=1 +tries=1 @127.0.0.1 -p 53053 example.com NS
```

Source anchor:

- `.github/workflows/test-docker.yml:122`

### 4) Validate docker-compose syntax

```bash
docker-compose -f docker-compose.example.yml config
```

Source anchor:

- `.github/workflows/test-docker.yml:157`

## Status Code Semantics

Use these expectations to diagnose behavior:

1. `NXDOMAIN`
   - Query is outside hosted/alias zones, or queried name does not exist in zone.
2. `NOERROR` with empty answer section
   - Name exists, but requested record type is not present.
3. `FORMERR`
   - Query has no question section.

Source anchors:

- `indisoluble/a_healthy_dns/dns_server_udp_handler.py:31`
- `indisoluble/a_healthy_dns/dns_server_udp_handler.py:41`
- `indisoluble/a_healthy_dns/dns_server_udp_handler.py:47`
- `indisoluble/a_healthy_dns/dns_server_udp_handler.py:91`
- `tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py:168`
- `tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py:192`
- `tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py:272`

## Symptom Playbooks

### Symptom: container exits immediately on start

Likely causes:

1. Required env vars missing (`DNS_HOSTED_ZONE`, `DNS_ZONE_RESOLUTIONS`, `DNS_NAME_SERVERS`).
2. Invalid JSON or malformed values cause config factory failure.

Checks:

```bash
docker logs <container-name>
```

Look for required-variable errors and parse/validation errors.

Source anchors:

- `Dockerfile:86`
- `Dockerfile:90`
- `Dockerfile:94`
- `indisoluble/a_healthy_dns/dns_server_config_factory.py:55`
- `indisoluble/a_healthy_dns/dns_server_config_factory.py:165`
- `indisoluble/a_healthy_dns/main.py:222`

### Symptom: DNS queries time out or no response

Likely causes:

1. Wrong port mapping between host and container.
2. Service bound to a different port than queried.
3. Container not running.

Checks:

1. Verify container is running.
2. Verify port mapping in `docker run`/compose.
3. Ensure `DNS_PORT` and published container port are aligned.

Important port note:

- CLI default port is `53053`.
- Docker image default `DNS_PORT` is `53`.
- If you map `53053:53053/udp`, set `DNS_PORT=53053`.
- If you keep Docker default `DNS_PORT=53`, map `53053:53/udp` (or query `53` directly).

Source anchors:

- `indisoluble/a_healthy_dns/main.py:59`
- `Dockerfile:66`
- `Dockerfile:98`
- `README.md:23`
- `.github/workflows/test-docker.yml:48`
- `.github/workflows/test-docker.yml:53`

### Symptom: expected subdomain returns `NXDOMAIN`

Likely causes:

1. Subdomain missing from `zone-resolutions`.
2. Query is outside hosted/alias zones.
3. All backend IPs currently unhealthy, so no A record is published.

Checks:

1. Validate `zone-resolutions` JSON and subdomain keys.
2. Probe both hosted and alias zone names.
3. Verify backend health endpoints are reachable from DNS runtime network.

Source anchors:

- `indisoluble/a_healthy_dns/dns_server_udp_handler.py:31`
- `indisoluble/a_healthy_dns/dns_server_udp_handler.py:41`
- `indisoluble/a_healthy_dns/records/a_record.py:25`
- `indisoluble/a_healthy_dns/tools/can_create_connection.py:16`

### Symptom: name resolves, but only sometimes

Likely causes:

1. Backend health flapping.
2. Test timeout too low for network latency.
3. Interval/timeout settings too aggressive for backend behavior.

Checks:

1. Increase `--test-timeout` and/or `--test-min-interval`.
2. Enable debug logging and inspect health transition lines.
3. Validate backend connectivity from same network namespace.

Source anchors:

- `indisoluble/a_healthy_dns/dns_server_zone_updater.py:194`
- `indisoluble/a_healthy_dns/dns_server_zone_updater.py:198`
- `indisoluble/a_healthy_dns/main.py:162`
- `indisoluble/a_healthy_dns/main.py:169`

### Symptom: DNSSEC-enabled start fails

Likely causes:

1. Private key path unreadable in container/runtime.
2. Key format incompatible with selected algorithm.
3. Invalid algorithm text.

Checks:

1. Confirm file path and mount are correct.
2. Confirm key is PEM and algorithm matches `--priv-key-alg`.
3. Check logs for private-key load errors.

Source anchors:

- `indisoluble/a_healthy_dns/dns_server_config_factory.py:190`
- `indisoluble/a_healthy_dns/dns_server_config_factory.py:207`
- `indisoluble/a_healthy_dns/dns_server_config_factory.py:212`
- `docs/configuration-reference.md:249`

## Debug Logging Guidance

Set log level to `debug` for incident diagnosis:

CLI:

```bash
a-healthy-dns ... --log-level debug
```

Docker:

```bash
docker run -it \
  -e DNS_LOG_LEVEL="debug" \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  indisoluble/a-healthy-dns
```

Source anchors:

- `indisoluble/a_healthy_dns/main.py:122`
- `docs/configuration-reference.md:188`

## Graceful Restart and Shutdown

Behavior:

1. Process handles `SIGINT`/`SIGTERM`.
2. UDP server shutdown is triggered.
3. Updater thread stop is requested and joined with timeout.

Operational recommendation:

1. Prefer graceful stop over force kill.
2. After restart, wait for initial zone initialization before judging DNS answers.

Source anchors:

- `indisoluble/a_healthy_dns/main.py:206`
- `indisoluble/a_healthy_dns/main.py:236`
- `indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py:64`
- `indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py:80`

## Performance and Capacity Notes

For higher load scenarios:

1. Set explicit CPU/memory limits.
2. Consider host networking if latency requirements justify the trade-off.
3. Monitor UDP stats for packet drops.

Source anchors:

- `docker-compose.example.yml:48`
- `docker-compose.example.yml:57`
- `docs/project-rules.md:162`

## Incident Artifact Collection

Collect these artifacts before escalation:

1. Effective command/env configuration (redacting secrets).
2. `docker logs` output around incident window.
3. `dig` outputs for:
   - healthy expected record,
   - missing record,
   - unsupported-type probe.
4. Backend reachability evidence from same network context.

Reference commands:

```bash
dig +short +time=1 +tries=1 @127.0.0.1 -p 53053 www.example.com A
dig +time=1 +tries=1 +noall +comments @127.0.0.1 -p 53053 missing.example.com A
dig +time=1 +tries=1 +noall +comments @127.0.0.1 -p 53053 www.example.com AAAA
```

Source anchors:

- `.github/workflows/test-docker.yml:85`
- `.github/workflows/test-docker.yml:105`
- `.github/workflows/test-docker.yml:145`
- `.github/workflows/test-docker.yml:146`
