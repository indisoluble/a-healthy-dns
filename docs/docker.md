# Docker Deployment Guide

This document is the canonical home for Docker-specific deployment guidance for **A Healthy DNS**.

It owns:
- how to run the published image or build a local image,
- how to use the repository Compose example,
- the runtime container contract that operators need to preserve,
- and Docker-focused deployment patterns and hardening guidance.

It does not own parameter-by-parameter reference material, repository-side container build rules, or troubleshooting procedures. Those topics live in [`docs/configuration-reference.md`](configuration-reference.md), [`docs/engineering-rules.md`](engineering-rules.md), and [`docs/troubleshooting.md`](troubleshooting.md).

Commands below use `docker compose` syntax. If you use the legacy standalone binary, replace it with `docker-compose`.

---

## 1. Runtime contract

The published image and the repository `Dockerfile` expose a few operator-visible behaviors that deployment configs should preserve.

| Aspect | Runtime behavior |
|---|---|
| Base image | Multi-stage build based on `cgr.dev/chainguard/python:latest-dev` and `cgr.dev/chainguard/python:latest` |
| Process model | `a-healthy-dns` runs directly as PID 1 and handles `SIGINT` / `SIGTERM` |
| Runtime user | Chainguard default non-root user, uid `65532`; runtime files are owned by this uid instead of introducing custom user-management steps |
| Exposed container port | `53/udp`; pass `--port 53` when the process should listen on that port |
| Configuration surface | Pass normal `a-healthy-dns` CLI flags as the container command |
| DNSSEC key mount | `/app/keys` is the expected mount point for private keys |
| Privileged bind strategy | Recommended: set `net.ipv4.ip_unprivileged_port_start=53` (or `=0`) on the host so no capability is required. Fallback: add `NET_BIND_SERVICE` at runtime when the sysctl cannot be set. |
| Image footprint | The runtime image is distroless and does not include a shell, `pip`, or an OS package manager; use the troubleshooting guide for diagnostics |

The Chainguard base image (`cgr.dev/chainguard/python:latest`) defaults to uid `65532` (`nonroot`). The repository `Dockerfile` relies on this default and does not override it with an explicit `USER` instruction. Because runtime files inside the image — the virtual environment and the DNSSEC key directory — are owned by that uid, operators who mount external DNSSEC keys must ensure the host directory is readable by numeric uid `65532`. This does not require a host user account named `65532`; Docker resolves ownership by numeric uid, not by name. Orchestrator manifests that pin the uid explicitly (for example `"user": "65532"` in ECS task definitions or `runAsUser: 65532` in Kubernetes pod specs) preserve the non-root identity even when the orchestrator does not propagate the image default.

---

## 2. Quick start

### Published image

This startup pattern keeps the container on a high port so local testing does not require binding host port `53`. The example intentionally mixes one health-checked record and one standard static record.

```bash
docker run -d \
  --name a-healthy-dns \
  -p 53053:53053/udp \
  indisoluble/a-healthy-dns \
  --port 53053 \
  --hosted-zone example.local \
  --zone-resolutions '{"www":{"ips":["192.168.1.100","192.168.1.101"],"health_port":8080},"static":["192.168.1.200"]}' \
  --ns '["ns1.dns.example.net"]'
```

### Build a local image from this repository

```bash
docker build -t a-healthy-dns:local .

docker run -d \
  --name a-healthy-dns-local \
  -p 53053:53053/udp \
  a-healthy-dns:local \
  --port 53053 \
  --hosted-zone example.local \
  --zone-resolutions '{"www":{"ips":["192.168.1.100"],"health_port":8080},"static":["192.168.1.200"]}' \
  --ns '["ns1.dns.example.net"]'
```

### Basic verification

```bash
dig @localhost -p 53053 www.example.local
dig @localhost -p 53053 static.example.local
docker ps --filter name=a-healthy-dns
docker logs --tail 50 a-healthy-dns
```

For parameter semantics, defaults, and all accepted CLI flags, use [`docs/configuration-reference.md`](configuration-reference.md).

---

## 3. Using Compose

The repository ships with [`docker-compose.example.yml`](../docker-compose.example.yml) as the baseline Compose deployment.

```bash
cp docker-compose.example.yml docker-compose.yml
# Edit the command arguments for your environment
docker compose up -d
```

The example file already demonstrates the main deployment choices this project expects:
- explicit UDP port mapping,
- CLI flag configuration through the Compose `command`,
- a dedicated bridge network,
- non-root execution as uid `65532` (inherited from the Chainguard base image default),
- `no-new-privileges` hardening,
- `cap_drop: [ALL]` with no capabilities added (assumes `net.ipv4.ip_unprivileged_port_start=53` is set on the host — see the inline comments),
- and memory/CPU limits.

If the host sysctl cannot be set, uncomment `cap_add: [NET_BIND_SERVICE]` in the example file as a fallback.

By default the example builds the image from the local repository (`build: .`). If you want to deploy the published image instead, replace `build: .` with `image: indisoluble/a-healthy-dns:<version>`.

---

## 4. DNSSEC deployment

DNSSEC remains optional. To enable it in Docker:
1. Mount the private-key directory into `/app/keys` as read-only.
2. Pass `--priv-key-path` with the mounted file path.
3. Pass `--priv-key-alg` when you need a non-default algorithm.

Example:

```bash
docker run -d \
  --name a-healthy-dns-dnssec \
  -p 53:53/udp \
  -v "$(pwd)/keys:/app/keys:ro" \
  indisoluble/a-healthy-dns \
  --port 53 \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["192.168.1.100"],"health_port":8080},"static":["192.168.1.200"]}' \
  --ns '["ns1.dns.example.net"]' \
  --priv-key-path /app/keys/private.pem \
  --priv-key-alg RSASHA256
```

Keep key files restrictive on the host side. When keys are mounted from the host, their permissions must allow numeric uid `65532` to read them inside the container.

For exact parameter semantics, use [`docs/configuration-reference.md`](configuration-reference.md). For DNSSEC design boundaries, use [`docs/architecture.md`](architecture.md).

---

## 5. Deployment patterns

### High-port local or lab deployment

Use a non-privileged host port such as `53053` when you do not need the service to answer on host port `53`. This is the safest default for local testing and avoids privileged host binds.

### Direct port-53 deployment

For a production-style deployment on the standard DNS port, run the container on `53/udp`.

**Recommended approach — host sysctl:**

Set `net.ipv4.ip_unprivileged_port_start=53` once on the host before starting the container. This allows the non-root process to bind privileged ports without any additional capability:

```bash
# One-time host configuration
sudo sysctl -w net.ipv4.ip_unprivileged_port_start=53
# To persist across reboots, add to /etc/sysctl.d/99-dns.conf:
#   net.ipv4.ip_unprivileged_port_start=53

docker run -d \
  --name a-healthy-dns \
  --cap-drop=ALL \
  --security-opt=no-new-privileges:true \
  -p 53:53/udp \
  indisoluble/a-healthy-dns \
  --port 53 \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["10.0.1.100","10.0.1.101"],"health_port":80},"static":["10.0.1.200"]}' \
  --ns '["ns1.dns.example.net","ns2.dns.example.net"]'
```

**Fallback — `NET_BIND_SERVICE` capability:**

Use this when the host sysctl cannot be set (shared hosts, restricted cloud runtimes):

```bash
docker run -d \
  --name a-healthy-dns \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  --security-opt=no-new-privileges:true \
  -p 53:53/udp \
  indisoluble/a-healthy-dns \
  --port 53 \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["10.0.1.100","10.0.1.101"],"health_port":80},"static":["10.0.1.200"]}' \
  --ns '["ns1.dns.example.net","ns2.dns.example.net"]'
```

### Redundant authoritative nodes

Run the same zone configuration on more than one host and publish all nodes in the NS set. Health checks remain local to each instance; there is no cross-node health-state synchronization or zone replication.

### Host networking

`--network host` is a valid deployment option when your environment prefers direct host networking over bridge networking. The tradeoff is lower network isolation in exchange for simpler port handling and lower network overhead. Apply the same port-53 binding strategy as the direct port-53 pattern above: prefer the host sysctl and fall back to `NET_BIND_SERVICE` when the sysctl cannot be set.

---

## 6. Runtime hardening

Use the image defaults as the baseline, then add only the hardening controls your environment requires.

Recommended controls:
- keep the container non-root; the image already does this by default,
- use `--security-opt=no-new-privileges:true` so the process and its children cannot acquire additional privileges after startup; this is a baseline hardening requirement,
- use `--cap-drop=ALL`; no capabilities need to be added when `net.ipv4.ip_unprivileged_port_start=53` (or `=0`) is set on the host,
- add `NET_BIND_SERVICE` only as a fallback when the host sysctl cannot be set,
- prefer read-only key mounts (`/app/keys:ro`),
- consider `--read-only` plus `--tmpfs /tmp:rw,noexec,nosuid` when a hardened deployment should make the image filesystem immutable while still providing a constrained writable `/tmp`.

Example hardened run (with host sysctl set):

```bash
# One-time host prerequisite
sudo sysctl -w net.ipv4.ip_unprivileged_port_start=53

docker run -d \
  --name a-healthy-dns \
  --user 65532 \
  --cap-drop=ALL \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid \
  --security-opt=no-new-privileges:true \
  -p 53:53/udp \
  indisoluble/a-healthy-dns \
  --port 53 \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["10.0.1.100"],"health_port":80},"static":["10.0.1.200"]}' \
  --ns '["ns1.dns.example.net"]'
```

If the host sysctl cannot be set, add `--cap-add=NET_BIND_SERVICE` to the command above.

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
- the CLI-argument configuration surface,
- non-root execution as uid `65532` (the Chainguard base image default; pin it explicitly with `runAsUser: 65532` in Kubernetes pod specs or `"user": "65532"` in ECS task definitions),
- `/app/keys` for DNSSEC key mounts,
- `no-new-privileges` enabled,
- and the privileged-port binding strategy: set `net.ipv4.ip_unprivileged_port_start=53` on the node (or via a Kubernetes `securityContext.sysctls` entry) when possible. In Kubernetes, the equivalent pod-level setting is:

  ```yaml
  securityContext:
    sysctls:
      - name: net.ipv4.ip_unprivileged_port_start
        value: "53"
  ```

  When the sysctl cannot be set, add `NET_BIND_SERVICE` to the container's `securityContext.capabilities.add`.

### AWS ECS Anywhere / external VMs

For Amazon ECS external instances, use the `EXTERNAL` launch type. External instances do not support `awsvpc` networking, ECS service load balancing, or ECS service discovery, so authoritative DNS traffic must reach the VM directly. Publish the external VM addresses in your DNS delegation and allow inbound UDP `53` through the VM firewall and any upstream network firewall.

Use `host` networking when the task should answer directly on the VM's UDP port `53`. This keeps DNS port ownership explicit: only one task per VM can bind host port `53`.

**Privileged-port note for ECS Anywhere:** ECS does not expose kernel sysctl configuration at the task level. The recommended approach is to set `net.ipv4.ip_unprivileged_port_start=53` on the external VM itself (e.g., in `/etc/sysctl.d/99-dns.conf`) before the task starts. When that sysctl is set on the VM, `NET_BIND_SERVICE` can be removed from `linuxParameters.capabilities.add`. When the sysctl cannot be applied to the VM, keep `NET_BIND_SERVICE` in the task definition as the fallback.

Task definition shape (with `NET_BIND_SERVICE` as fallback; remove it when the host sysctl is set):

```json
{
  "family": "a-healthy-dns",
  "requiresCompatibilities": ["EXTERNAL"],
  "networkMode": "host",
  "cpu": "256",
  "memory": "256",
  "containerDefinitions": [
    {
      "name": "a-healthy-dns",
      "image": "indisoluble/a-healthy-dns:<version>",
      "essential": true,
      "user": "65532",
      "readonlyRootFilesystem": true,
      "dockerSecurityOptions": ["no-new-privileges"],
      "linuxParameters": {
        "capabilities": {
          "drop": ["ALL"],
          "add": ["NET_BIND_SERVICE"]
        }
      },
      "portMappings": [
        {
          "containerPort": 53,
          "hostPort": 53,
          "protocol": "udp"
        }
      ],
      "command": [
        "--port", "53",
        "--hosted-zone", "example.com",
        "--zone-resolutions", "{\"www\":{\"ips\":[\"10.0.1.100\"],\"health_port\":80}}",
        "--ns", "[\"ns1.dns.example.net\"]"
      ],
      "mountPoints": [
        {
          "sourceVolume": "dnssec-keys",
          "containerPath": "/app/keys",
          "readOnly": true
        }
      ]
    }
  ],
  "volumes": [
    {
      "name": "dnssec-keys",
      "host": {
        "sourcePath": "/etc/a-healthy-dns/keys"
      }
    }
  ]
}
```

In ECS task definitions, `"readonlyRootFilesystem": true` is the orchestrator equivalent of Docker `--read-only`: it makes the container root filesystem immutable after startup. This is optional hardening, not a functional requirement for `a-healthy-dns`. Keep it enabled when the task only reads image contents and read-only DNSSEC key mounts. If runtime writes become necessary, provide an explicit writable mount or temporary filesystem for those paths.

If DNSSEC is disabled, omit `mountPoints` and `volumes`. If DNSSEC is enabled, make the host key directory readable by uid `65532` and keep the mount read-only.

External instances must also be able to reach the required ECS and SSM regional endpoints. If you send logs to CloudWatch Logs, configure a task execution IAM role and an ECS logging driver on the external instance.

`bridge` networking is also valid on ECS external instances. Use it only when you need Docker bridge isolation; map `hostPort` `53` to the container port passed with `--port`. Mapping host port `53` to a non-privileged container port such as `53053` avoids needing `NET_BIND_SERVICE` inside the container.

This document does not provide full orchestrator manifests. Keep the orchestrator config aligned with the runtime contract above and with the repository's Dockerfile.
