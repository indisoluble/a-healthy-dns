# Docker Deployment Guide

This document is the canonical home for Docker-specific deployment guidance for **A Healthy DNS**.

It owns:
- how to run the published image or build a local image,
- how to use the repository Compose example,
- the runtime container contract that operators need to preserve,
- and Docker-focused deployment patterns and hardening guidance.

It does not own parameter-by-parameter reference material, repository-side container build rules, or troubleshooting procedures. Those topics live in [`docs/configuration-reference.md`](configuration-reference.md), [`docs/project-rules.md`](project-rules.md), and [`docs/troubleshooting.md`](troubleshooting.md).

Commands below use `docker compose` syntax. If you use the legacy standalone binary, replace it with `docker-compose`.

---

## 1. Runtime contract

The published image and the repository `Dockerfile` expose a few operator-visible behaviors that deployment configs should preserve.

| Aspect | Runtime behavior |
|---|---|
| Base image | Multi-stage build based on `python:3-slim` |
| Process model | `tini` runs as PID 1 and launches `a-healthy-dns` |
| Runtime user | Non-root `appuser` with uid/gid `10000` |
| Default container port | `53/udp` (`DNS_PORT=53` by default inside the image) |
| Configuration surface | `DNS_*` environment variables are translated into CLI flags by the entrypoint |
| DNSSEC key mount | `/app/keys` is the expected mount point for private keys |
| Privileged bind strategy | The Python interpreter has `CAP_NET_BIND_SERVICE` via `setcap` so the process can bind port `53` without running as root |
| Image footprint | The runtime image is intentionally slim; use the troubleshooting guide for diagnostics rather than expecting general debug tools inside the container |

---

## 2. Quick start

### Published image

This startup pattern keeps the container on a high port so local testing does not require binding host port `53`.

```bash
docker run -d \
  --name a-healthy-dns \
  -p 53053:53053/udp \
  -e DNS_HOSTED_ZONE="example.local" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100","192.168.1.101"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.dns.example.net"]' \
  -e DNS_PORT="53053" \
  indisoluble/a-healthy-dns
```

### Build a local image from this repository

```bash
docker build -t a-healthy-dns:local .

docker run -d \
  --name a-healthy-dns-local \
  -p 53053:53053/udp \
  -e DNS_HOSTED_ZONE="example.local" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.dns.example.net"]' \
  -e DNS_PORT="53053" \
  a-healthy-dns:local
```

### Basic verification

```bash
dig @localhost -p 53053 www.example.local
docker ps --filter name=a-healthy-dns
docker logs --tail 50 a-healthy-dns
```

For parameter semantics, defaults, and all accepted `DNS_*` variables, use [`docs/configuration-reference.md`](configuration-reference.md).

---

## 3. Using Compose

The repository ships with [`docker-compose.example.yml`](../docker-compose.example.yml) as the baseline Compose deployment.

```bash
cp docker-compose.example.yml docker-compose.yml
# Edit the DNS_* values for your environment
docker compose up -d
```

The example file already demonstrates the main deployment choices this project expects:
- explicit UDP port mapping,
- `DNS_*` environment-variable configuration,
- a dedicated bridge network,
- non-root execution as `10000:10000`,
- `no-new-privileges`,
- `cap_drop: [ALL]` plus `NET_BIND_SERVICE`,
- and memory/CPU limits.

By default the example builds the image from the local repository (`build: .`). If you want to deploy the published image instead, replace `build: .` with `image: indisoluble/a-healthy-dns:<version>`.

---

## 4. DNSSEC deployment

DNSSEC remains optional. To enable it in Docker:
1. Mount the private-key directory into `/app/keys` as read-only.
2. Set `DNS_PRIV_KEY_PATH` to the mounted file path.
3. Set `DNS_PRIV_KEY_ALG` when you need a non-default algorithm.

Example:

```bash
docker run -d \
  --name a-healthy-dns-dnssec \
  -p 53:53/udp \
  -v "$(pwd)/keys:/app/keys:ro" \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.dns.example.net"]' \
  -e DNS_PRIV_KEY_PATH="/app/keys/private.pem" \
  -e DNS_PRIV_KEY_ALG="RSASHA256" \
  indisoluble/a-healthy-dns
```

Keep key files restrictive on the host side. The runtime image expects `/app/keys` to be private to `appuser`.

For exact parameter semantics, use [`docs/configuration-reference.md`](configuration-reference.md). For DNSSEC design boundaries, use [`docs/system-patterns.md`](system-patterns.md).

---

## 5. Deployment patterns

### High-port local or lab deployment

Use a non-privileged host port such as `53053` when you do not need the service to answer on host port `53`. This is the safest default for local testing and avoids privileged host binds.

### Direct port-53 deployment

For a production-style deployment on the standard DNS port, run the container on `53/udp`:

```bash
docker run -d \
  --name a-healthy-dns \
  -p 53:53/udp \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["10.0.1.100","10.0.1.101"],"health_port":80}}' \
  -e DNS_NAME_SERVERS='["ns1.dns.example.net","ns2.dns.example.net"]' \
  indisoluble/a-healthy-dns
```

If your runtime drops all Linux capabilities, add back `NET_BIND_SERVICE` explicitly to preserve port-53 binding:

```bash
docker run -d \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  -p 53:53/udp \
  ... \
  indisoluble/a-healthy-dns
```

### Redundant authoritative nodes

Run the same zone configuration on more than one host and publish all nodes in the NS set. Health checks remain local to each instance; there is no cross-node health-state synchronization or zone replication.

### Host networking

`--network host` is a valid deployment option when your environment prefers direct host networking over bridge networking. The tradeoff is lower network isolation in exchange for simpler port handling and lower network overhead.

---

## 6. Runtime hardening

Use the image defaults as the baseline, then add only the hardening controls your environment requires.

Recommended controls:
- keep the container non-root; the image already does this by default,
- use `--cap-drop=ALL` and add back only `NET_BIND_SERVICE` when binding container port `53`,
- prefer read-only key mounts (`/app/keys:ro`),
- use `--security-opt=no-new-privileges:true`,
- and consider `--read-only` plus `--tmpfs /tmp:rw,noexec,nosuid` in hardened environments.

Example hardened run:

```bash
docker run -d \
  --name a-healthy-dns \
  --user 10000:10000 \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid \
  --security-opt=no-new-privileges:true \
  -p 53:53/udp \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["10.0.1.100"],"health_port":80}}' \
  -e DNS_NAME_SERVERS='["ns1.dns.example.net"]' \
  indisoluble/a-healthy-dns
```

The repository Compose example already demonstrates a conservative hardened baseline.

---

## 7. Versioning and upgrades

For production deployments, pin a specific image tag instead of `latest`.

```bash
docker pull indisoluble/a-healthy-dns:<version>
docker run -d ... indisoluble/a-healthy-dns:<version>
```

Use `latest` only for development or when you explicitly want the newest published image without pinning.

When upgrading:
1. pull the target image tag,
2. recreate the container or Compose stack,
3. run the same DNS query checks you use for post-deploy verification.

---

## 8. Orchestrator notes

If you deploy through Kubernetes, Swarm, Nomad, or another orchestrator, preserve the same container contract:
- UDP exposure for the DNS listener,
- the `DNS_*` environment-variable interface,
- non-root execution as uid/gid `10000`,
- `/app/keys` for DNSSEC key mounts,
- and `NET_BIND_SERVICE` only when the runtime drops capabilities and still needs port `53`.

This document does not provide full orchestrator manifests. Keep the orchestrator config aligned with the runtime contract above and with the repository's Dockerfile.
