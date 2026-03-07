# Docker

## Pre-built image

A multi-platform image (`amd64`, `arm64`) is published to [Docker Hub](https://hub.docker.com/r/indisoluble/a-healthy-dns) on every release.

```bash
docker pull indisoluble/a-healthy-dns
```

## Build from source

```bash
docker build -t a-healthy-dns .
```

The [Dockerfile](../Dockerfile) uses a multi-stage build:

1. **Builder stage** (`python:3-slim`) — installs build dependencies (`gcc`, `libffi-dev`, `libssl-dev`, `cargo`, `rustc`), then `pip install --user .`.
2. **Production stage** (`python:3-slim`) — copies only the installed packages. Installs runtime dependencies (`libffi8`, `libssl3`, `libcap2-bin`, `tini`).

## Run

### Quick start

```bash
docker run -d \
  --name a-healthy-dns \
  -p 53053:53/udp \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  indisoluble/a-healthy-dns
```

> The container listens on port **53** by default (not 53053). The `-p 53053:53/udp` mapping exposes it on the host as 53053. Adjust the host port as needed.

### With DNSSEC

```bash
mkdir -p ./keys
cp your-private-key.pem ./keys/

docker run -d \
  --name a-healthy-dns \
  -p 53053:53/udp \
  -v "$(pwd)/keys:/app/keys:ro" \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  -e DNS_PRIV_KEY_PATH="/app/keys/your-private-key.pem" \
  indisoluble/a-healthy-dns
```

The `/app/keys` volume is owned by the `appuser` (UID 10000) with `700` permissions.

### Environment variables

See [configuration.md — Docker environment variables](configuration.md#docker-environment-variables) for the full reference.

## Docker Compose

Copy the example file and edit it:

```bash
cp docker-compose.example.yml docker-compose.yml
# Edit docker-compose.yml with your configuration
docker compose up -d
```

The example file includes:
- Required and optional environment variables.
- Port mapping (`53053:53053/udp`).
- Security hardening (see below).
- Resource limits (256 MB memory, 0.5 CPU).
- Restart policy (`unless-stopped`).
- Isolated bridge network.

## Security hardening

The Dockerfile and compose example apply several security measures:

| Measure | How |
|---------|-----|
| Non-root user | `appuser` (UID/GID 10000). Set in Dockerfile and compose (`user: "10000:10000"`). |
| Minimal capabilities | `cap_drop: ALL` + `cap_add: NET_BIND_SERVICE`. Only allows binding to privileged ports. |
| No privilege escalation | `security_opt: no-new-privileges:true`. |
| Privileged port binding | `setcap cap_net_bind_service=+ep` on the Python interpreter (no root needed for port 53). |
| Process manager | `tini` as PID 1. Properly forwards signals and reaps zombie processes. |
| Read-only keys volume | DNSSEC keys mounted with `:ro`. |
| Minimal image | Multi-stage build; production stage has no build tools. |

## Troubleshooting

### Check if the server is running

```bash
docker ps | grep a-healthy-dns
docker logs a-healthy-dns
```

### Test DNS resolution

```bash
dig @localhost -p 53053 www.example.com
```

### Enable debug logging

```bash
docker run -d \
  -e DNS_LOG_LEVEL="debug" \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  indisoluble/a-healthy-dns
```

### Shell access

```bash
# Running container
docker exec -it a-healthy-dns sh

# Fresh container
docker run -it --entrypoint sh indisoluble/a-healthy-dns
```

### Validate Compose file

```bash
docker compose -f docker-compose.example.yml config --quiet
```
