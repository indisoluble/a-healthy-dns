# Troubleshooting Guide

This document is the canonical home for diagnosing and operating a running **A Healthy DNS** instance.

It owns:
- fast incident triage,
- symptom-based runbooks,
- log interpretation grounded in actual runtime messages,
- live debugging commands,
- and monitoring / incident handoff guidance.

It does not own deployment setup, parameter reference, or architecture details. Use [`docs/docker.md`](docker.md) for Docker deployment, [`docs/configuration-reference.md`](configuration-reference.md) for parameter definitions, [`docs/system-patterns.md`](system-patterns.md) for architecture and timing derivation, and [`docs/RFC-conformance.md`](RFC-conformance.md) for wire-level response semantics.

---

## 1. Fast triage

If you need an answer quickly, run these checks in order.

### 1.1 Is the service up?

Docker:

```bash
docker ps --filter name=a-healthy-dns
docker logs --tail 100 a-healthy-dns
docker port a-healthy-dns
```

Direct process:

```bash
ps aux | grep a-healthy-dns
lsof -nP -iUDP:53053
```

If the logs never reach `DNS server listening on port ...`, the process failed before it started serving queries.

### 1.2 Does the server answer authoritative queries?

```bash
dig @localhost -p 53053 example.local SOA
dig @localhost -p 53053 www.example.local A
dig @localhost -p 53053 www.example.local AAAA
```

Use the hosted zone, subdomain, and port from your own configuration.

### 1.3 Are the backends reachable on their health ports?

From the same host:

```bash
nc -zv 192.168.1.100 8080
nc -zv 192.168.1.101 8080
```

From inside the running container:

```bash
docker exec a-healthy-dns python3 -c "import socket; socket.create_connection(('192.168.1.100', 8080), 2).close(); print('ok')"
```

### 1.4 Interpret the first result correctly

| Observation | Most likely meaning | Next check |
|---|---|---|
| `NOERROR` with answers | The queried name exists and currently has records of that type | Confirm the answer set matches current backend health |
| `NOERROR` with empty answer and SOA in authority | The owner name exists but not for that record type (`NODATA`) | Check the queried type; `AAAA` is often empty because the project serves A records only |
| `NXDOMAIN` with SOA in authority | The queried owner name does not exist in the active zone view | Check for an unknown subdomain or a configured subdomain whose IPs are all unhealthy |
| `REFUSED` | The query is outside the hosted or alias zones, or the query class is unsupported | Check the zone name and query class |
| `FORMERR` | The request is malformed or contains the wrong question count | Check the client or packet generator |
| Timeout / no response | The server is down, UDP is blocked, port mapping is wrong, or the packet was too short to answer | Check service status, firewall, packet capture, and port mapping |

---

## 2. Symptom-based runbooks

### 2.1 The server does not start or exits immediately

**Symptoms:** container stops right away, non-zero exit, no `DNS server listening on port ...` log line.

**Check:**
```bash
docker logs --tail 100 a-healthy-dns
lsof -nP -iUDP:53053
```
Add `--log-level debug` when running the CLI directly.

**Likely causes:** invalid JSON in `DNS_ZONE_RESOLUTIONS`, `DNS_NAME_SERVERS`, or `DNS_ALIAS_ZONES`; invalid hosted zone, subdomain, IP, or NS values; DNSSEC key path/format problems; UDP port in use; port-53 bind constraints in hardened Docker.

**Logs:** `Failed to parse alias zones`, `Failed to create zone origins`, `Failed to parse zone resolutions`, `Zone resolution subdomain '...' is not valid`, `Name server '...' is not a valid FQDN`, `Invalid IP/port address in '...'`, `Failed to load DNSSEC private key`, `Failed to load private key`.

**Next:** validate JSON, parameters, and DNSSEC options with [`docs/configuration-reference.md`](configuration-reference.md). For privileged port or capability failures, use [`docs/docker.md`](docker.md). For port collisions, move the host mapping or stop the conflicting service.

### 2.2 Queries time out or no response is returned

**Symptoms:** `dig` times out, no response on the configured UDP port, intermittent packet loss.

**Check:**
```bash
lsof -nP -iUDP:53053
docker port a-healthy-dns
sudo tcpdump -i any -n udp port 53053
```
When using Docker, confirm you are querying the exposed host port, not only the container port.

**Interpretation:** if the process is not listening, this is a startup failure. If packets reach the host but not the process, inspect firewall rules and Docker networking. Short packets (< 12-byte DNS header) are dropped silently by design.

**Next:** re-run the fast-triage `dig` checks against the exact configured port. Use packet capture to confirm queries arrive and replies leave the host. For network mode, port mapping, or capability issues, fix the deployment in [`docs/docker.md`](docker.md).

### 2.3 The server returns `NXDOMAIN`, `REFUSED`, or the wrong answers

**Distinguish first:** `REFUSED` = query outside hosted/alias zones or non-`IN` class; `NXDOMAIN` = owner name absent from active zone view; `NOERROR` with empty answer = name exists but not for that type.

**Check:**
```bash
dig @localhost -p 53053 www.example.local A
dig @localhost -p 53053 www.example.local AAAA
docker logs --tail 200 a-healthy-dns | grep -E "Checked IP|A records changed|Updating zone|Added A record|skipped|unknown subdomain|not in hosted"
```
Use `--log-level debug` or `DNS_LOG_LEVEL=debug` when you need the per-IP or per-record lines (`Checked IP`, `Added A record`, `A record ... skipped`).

**Common causes:** wrong zone → `REFUSED`; unconfigured subdomain → `NXDOMAIN`; all backend IPs unhealthy → A record skipped → `NXDOMAIN`; record type not published (e.g. `AAAA`) → `NOERROR` empty answer; backend health changed and answer set reflects the new state.

**Backend check:** `nc -zv 192.168.1.100 8080`. When all IPs are unhealthy, look for `A record <name> skipped` after `Updating zone...`.

### 2.4 DNSSEC responses are missing or rejected

**Symptoms:** `dig +dnssec` shows no `RRSIG`, `DNSKEY`, or `NSEC` data; startup fails loading the key; validating resolver rejects the response.

**Check:**
```bash
dig @localhost -p 53053 example.local DNSKEY
dig @localhost -p 53053 www.example.local +dnssec
docker logs --tail 200 a-healthy-dns | grep -i "dnssec\\|sign\\|key"
```
Use `--log-level debug` or `DNS_LOG_LEVEL=debug` when you need signing-detail lines such as `Zone signed with expiration time ...`.

**Likely causes:** no key path configured (DNSSEC disabled); key file missing or unreadable; PEM/algorithm mismatch; signature near expiration.

**Logs:** `Loaded DNSSEC private key from ...`, `Failed to load DNSSEC private key`, `Failed to load private key`, `Zone signing is near to expire`, `Zone signed with expiration time ...`.

**Next:** verify key mount and permissions in [`docs/docker.md`](docker.md); verify `DNS_PRIV_KEY_PATH` and `DNS_PRIV_KEY_ALG` in [`docs/configuration-reference.md`](configuration-reference.md). For DNS wire behavior issues use [`docs/RFC-conformance.md`](RFC-conformance.md).

### 2.5 Responses are slow or the host is under pressure

**Symptoms:** unusually high query latency, CPU/memory spikes, excessive zone updates.

**Check:**
```bash
time dig @localhost -p 53053 www.example.local A
docker stats --no-stream a-healthy-dns
docker logs --since 15m a-healthy-dns | grep -c "Updating zone"
docker logs --since 15m a-healthy-dns | grep -c "A records changed"
```

**Interpretation:** query serving and health checks are separated; slow health checks should not block queries directly, but a resource-constrained host or network can. Frequent `A records changed` / `Updating zone...` lines indicate backend flapping or aggressive check timing. Adjust resources in [`docs/docker.md`](docker.md) and health-check timing in [`docs/configuration-reference.md`](configuration-reference.md).

**Next:** confirm backend stability before tuning timing; check whether the host or container is resource-constrained.

---

## 3. Log interpretation

### 3.1 Log levels

| Level | Use it for |
|---|---|
| `debug` | Per-IP health checks, per-record zone updates, DNSSEC signing details, answered-query detail |
| `info` | Normal lifecycle events: startup, shutdown, zone-updater start/stop, zone rebuilds |
| `warning` | Out-of-zone queries, malformed queries, unsupported query shapes, unexpected updater lifecycle calls |
| `error` | Startup-time configuration failures and key-loading failures |

### 3.2 High-value log messages

These fragments span `info`, `warning`, and `debug`. Use `--log-level debug` or `DNS_LOG_LEVEL=debug` when you need per-IP, per-record, or per-signing detail.

| Message fragment | Meaning | Typical next step |
|---|---|---|
| `Initializing zone...` | First in-memory zone build is starting | Normal during startup |
| `Starting Zone Updater...` | Background health-check thread is starting | Normal during startup |
| `DNS server listening on port ...` | UDP socket is bound and serving | Use `dig` to verify answers |
| `Checked IP ... from ... to ...` | A backend health result was evaluated | Compare with backend reachability tests |
| `A records changed` | At least one backend health state changed | Expect a zone rebuild next |
| `Updating zone...` | The zone is being rebuilt atomically | Watch for added or skipped records |
| `Added A record ... to zone` | A healthy subdomain is present in the new zone | Confirm with `dig` |
| `A record ... skipped` | That subdomain currently has no healthy IPs | Expect `NXDOMAIN` for that name |
| `Zone signing is near to expire` | DNSSEC forced a refresh even without health changes | Confirm fresh signatures if DNSSEC is enabled |
| `Received query for unknown subdomain: ...` | In-zone `NXDOMAIN` path | Check spelling and health state |
| `Received query for domain not in hosted or alias zones: ...` | Out-of-zone `REFUSED` path | Check hosted zone or alias-zone config |
| `Failed to parse DNS query: ...` | Malformed DNS input reached the server | Check the client or packet generator |
| `Received ... signal, shutting down DNS server...` | Graceful shutdown started | Normal during stop / restart |
| `Stopping Zone Updater...` | Background updater is being stopped | Normal during shutdown |
| `Zone Updater thread did not terminate gracefully` | Shutdown was slow or blocked | Inspect long-running health checks |

### 3.3 Query-response clues from logs

- `Received query for domain not in hosted or alias zones: ...` lines correlate with `REFUSED`.
- `Received query for unknown subdomain: ...` lines correlate with `NXDOMAIN`.
- `Answered query for ... with ...` appears only at `debug` level when a matching RRset is found.
- `Subdomain ... exists but has no ... records` appears only at `debug` level for `NODATA` responses.

---

## 4. Live debugging commands

**DNS queries:**
```bash
dig @localhost -p 53053 example.local SOA
dig @localhost -p 53053 example.local NS
dig @localhost -p 53053 www.example.local A
dig @localhost -p 53053 www.example.local AAAA
dig @localhost -p 53053 www.example.local +dnssec
```

**Packet capture:**
```bash
sudo tcpdump -i any -n udp port 53053
sudo tcpdump -i any -n udp port 53053 -w dns-traffic.pcap
```

**Backend connectivity from inside the container** (use when host-to-backend looks healthy but container cannot reach the backend):
```bash
docker exec a-healthy-dns python3 -c "import socket; socket.create_connection(('192.168.1.100', 8080), 2).close(); print('ok')"
```

**Zone-update activity:**
```bash
docker logs --tail 200 a-healthy-dns | grep "Updating zone"
docker logs --tail 200 a-healthy-dns | grep "Checked IP"
docker logs --tail 200 a-healthy-dns | grep "Added A record"
docker logs --tail 200 a-healthy-dns | grep "skipped"
```
Only `Updating zone...` appears at `info` level; the other three patterns require `debug`.

---

## 5. Monitoring and incident handoff

Monitor: process/container liveness, authoritative DNS response success for representative names, backend health-state changes, zone rebuild frequency, and CPU/memory. There is no built-in health endpoint; use a DNS query plus process/container liveness as the health probe.

**Useful checks:**
```bash
dig @localhost -p 53053 www.example.local +short
docker stats --no-stream a-healthy-dns
docker logs --since 1h a-healthy-dns | grep -c "Updating zone"
docker logs --since 1h a-healthy-dns | grep -c "A records changed"
```

**Incident handoff — collect:** Docker image tag or git commit; exact hosted zone, queried name, and UDP port; redacted startup config; last 200 log lines (with `debug` if reproducible); one failing `dig` command and its output; host/container network details if transport-related.

```bash
docker logs --tail 200 a-healthy-dns > dns-logs.txt
docker inspect a-healthy-dns > dns-inspect.json
docker version > system-info.txt
uname -a >> system-info.txt
```
