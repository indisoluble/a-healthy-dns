# Docker Deployment Guide

Docker is the recommended deployment method for A Healthy DNS. The official image is available on [Docker Hub](https://hub.docker.com/r/indisoluble/a-healthy-dns) and includes all dependencies, security hardening, and production-ready configuration.

> **Quick start:** see [`README.md`](../README.md).  
> **Configuration reference:** see [`docs/configuration-reference.md`](configuration-reference.md) for all parameters.  
> **Troubleshooting:** see [`docs/troubleshooting.md`](troubleshooting.md) for Docker-specific issues and operational procedures.

---

## Quick Start

### Using Pre-Built Image

```bash
docker run -d \
  --name a-healthy-dns \
  -p 53053:53053/udp \
  -e DNS_HOSTED_ZONE="sub.domain.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.domain.com"]' \
  -e DNS_PORT="53053" \
  indisoluble/a-healthy-dns
```

### Building Local Image

```bash
# Clone repository
git clone https://github.com/indisoluble/a-healthy-dns.git
cd a-healthy-dns

# Build image
docker build -t a-healthy-dns:local .

# Run container
docker run -d \
  --name a-healthy-dns \
  -p 53053:53053/udp \
  -e DNS_HOSTED_ZONE="sub.domain.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.domain.com"]' \
  -e DNS_PORT="53053" \
  a-healthy-dns:local
```

## Docker Image Details

### Base Image
- **Base:** `python:3-slim` (Debian-based)
- **Multi-stage build** for minimal image size
- **Non-root user** (UID/GID: 10000) for security

### Security Features
- Runs as non-root user (`appuser`)
- Minimal attack surface (slim base, minimal dependencies)
- Capability management (`CAP_NET_BIND_SERVICE` for port 53)
- Tini init system for proper signal handling
- No unnecessary packages or build tools in final image

### Image Layers
1. **Builder stage:** Installs build dependencies (gcc, rust compiler)
2. **Production stage:** Only runtime dependencies (libffi, libssl)
3. **Application layer:** Python packages installed in user directory

### Exposed Ports
- **53/udp** — DNS (exposed but configurable via `DNS_PORT`)

### Volumes
- **/app/keys** — Optional volume for DNSSEC private keys

## Environment Variables

Configuration is provided via environment variables. For the full parameter reference — including defaults, accepted values, and CLI flag equivalents — see [docs/configuration-reference.md](configuration-reference.md).

Required: `DNS_HOSTED_ZONE`, `DNS_ZONE_RESOLUTIONS`, `DNS_NAME_SERVERS`.  
Optional: `DNS_PORT`, `DNS_LOG_LEVEL`, `DNS_TEST_MIN_INTERVAL`, `DNS_TEST_TIMEOUT`, `DNS_ALIAS_ZONES`, `DNS_PRIV_KEY_PATH`, `DNS_PRIV_KEY_ALG`.

## Docker Compose

### Basic Setup

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  a-healthy-dns:
    image: indisoluble/a-healthy-dns
    ports:
      - "53053:53053/udp"
    environment:
      DNS_HOSTED_ZONE: "sub.domain.com"
      DNS_ZONE_RESOLUTIONS: '{"www":{"ips":["192.168.1.100","192.168.1.101"],"health_port":8080}}'
      DNS_NAME_SERVERS: '["ns1.domain.com", "ns2.domain.com"]'
      DNS_PORT: "53053"
    restart: unless-stopped
```

Deploy:
```bash
docker-compose up -d
```

### Production Setup with Security

Use the provided [docker-compose.example.yml](../docker-compose.example.yml) as a template:

```bash
cp docker-compose.example.yml docker-compose.yml
# Edit docker-compose.yml with your configuration
docker-compose up -d
```

Key security features in example:
- **Security options:** `no-new-privileges:true`
- **Capability dropping:** Drop all, add only `NET_BIND_SERVICE`
- **User specification:** Explicit UID/GID (10000:10000)
- **Resource limits:** Memory and CPU constraints
- **Network isolation:** Custom bridge network

### DNSSEC Setup

**Directory structure:**
```
.
├── docker-compose.yml
└── keys/
    └── private.pem  (chmod 600)
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  a-healthy-dns:
    image: indisoluble/a-healthy-dns
    ports:
      - "53053:53053/udp"
    environment:
      DNS_HOSTED_ZONE: "sub.domain.com"
      DNS_ZONE_RESOLUTIONS: '{"www":{"ips":["192.168.1.100"],"health_port":8080}}'
      DNS_NAME_SERVERS: '["ns1.domain.com"]'
      DNS_PORT: "53053"
      DNS_PRIV_KEY_PATH: "/app/keys/private.pem"
      DNS_PRIV_KEY_ALG: "RSASHA256"
    volumes:
      - ./keys:/app/keys:ro
    restart: unless-stopped
```

**Deploy:**
```bash
# Ensure key permissions
chmod 600 keys/private.pem

# Start service
docker-compose up -d

# Verify DNSSEC signing
docker logs a-healthy-dns 2>&1 | grep -i "sign"
```

## Deployment Patterns

### Single-Node Deployment

**Scenario:** Single DNS server handling all queries.

```bash
docker run -d \
  --name a-healthy-dns \
  -p 53:53/udp \
  --cap-add=NET_BIND_SERVICE \
  --user 10000:10000 \
  --memory="256m" \
  --cpus="0.5" \
  --restart=unless-stopped \
  -e DNS_HOSTED_ZONE="sub.domain.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["10.0.1.100","10.0.1.101"],"health_port":80}}' \
  -e DNS_NAME_SERVERS='["ns1.domain.com","ns2.domain.com"]' \
  -e DNS_PORT="53" \
  indisoluble/a-healthy-dns
```

### Multi-Instance Deployment

**Scenario:** Multiple instances for redundancy (different servers).

**Server 1 (ns1.domain.com):**
```bash
docker run -d \
  --name a-healthy-dns-ns1 \
  -p 53:53/udp \
  -e DNS_HOSTED_ZONE="sub.domain.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["10.0.1.100","10.0.1.101"],"health_port":80}}' \
  -e DNS_NAME_SERVERS='["ns1.domain.com","ns2.domain.com"]' \
  -e DNS_PORT="53" \
  indisoluble/a-healthy-dns
```

**Server 2 (ns2.domain.com):**
```bash
# Same configuration on different physical/virtual server
docker run -d \
  --name a-healthy-dns-ns2 \
  -p 53:53/udp \
  -e DNS_HOSTED_ZONE="sub.domain.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["10.0.1.100","10.0.1.101"],"health_port":80}}' \
  -e DNS_NAME_SERVERS='["ns1.domain.com","ns2.domain.com"]' \
  -e DNS_PORT="53" \
  indisoluble/a-healthy-dns
```

**Note:** Health checks are independent on each instance; no state synchronization.

### Development Setup

**Scenario:** Local testing with debug logging and high port.

```bash
docker run -d \
  --name a-healthy-dns-dev \
  -p 53053:53053/udp \
  -e DNS_HOSTED_ZONE="example.local" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["127.0.0.1"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.local"]' \
  -e DNS_PORT="53053" \
  -e DNS_LOG_LEVEL="debug" \
  -e DNS_TEST_MIN_INTERVAL="10" \
  indisoluble/a-healthy-dns

# Follow logs
docker logs -f a-healthy-dns-dev
```

### Host Networking (Performance)

**Scenario:** Maximum performance, reduced isolation.

```bash
docker run -d \
  --name a-healthy-dns \
  --network host \
  -e DNS_HOSTED_ZONE="sub.domain.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.domain.com"]' \
  -e DNS_PORT="53" \
  indisoluble/a-healthy-dns
```

**Trade-offs:**
- **Pros:** Lower latency, no port mapping overhead
- **Cons:** Less isolation, binds directly to host port

## Container Management

### Lifecycle Operations

```bash
# Start container
docker start a-healthy-dns

# Stop container (graceful shutdown)
docker stop a-healthy-dns

# Restart container
docker restart a-healthy-dns

# Remove container
docker rm a-healthy-dns

# Remove container and volumes
docker rm -v a-healthy-dns
```

### Viewing Logs

```bash
# Last 100 lines
docker logs --tail 100 a-healthy-dns

# Follow logs in real-time
docker logs -f a-healthy-dns

# Logs since timestamp
docker logs --since 2026-03-07T10:00:00 a-healthy-dns

# Logs with timestamps
docker logs -t a-healthy-dns
```

### Inspecting Container

```bash
# Container details
docker inspect a-healthy-dns

# Resource usage
docker stats a-healthy-dns

# Network settings
docker inspect a-healthy-dns | jq '.[0].NetworkSettings'

# Environment variables
docker inspect a-healthy-dns | jq '.[0].Config.Env'
```

### Executing Commands in Container

```bash
# Get shell access
docker exec -it a-healthy-dns sh

# Check listening ports
docker exec a-healthy-dns netstat -uln

# Test health check connectivity
docker exec a-healthy-dns nc -zv 192.168.1.100 8080

# View Python packages
docker exec a-healthy-dns pip list
```

## Resource Management

### Memory Limits

```bash
# Set memory limit
docker run -d \
  --name a-healthy-dns \
  --memory="256m" \
  --memory-reservation="128m" \
  ... \
  indisoluble/a-healthy-dns
```

**Guideline:**
- **Small zones (1-10 IPs):** 128-256 MB
- **Medium zones (10-50 IPs):** 256-512 MB
- **Large zones (50+ IPs):** 512 MB - 1 GB

### CPU Limits

```bash
# Set CPU limit (0.5 = 50% of one core)
docker run -d \
  --name a-healthy-dns \
  --cpus="0.5" \
  ... \
  indisoluble/a-healthy-dns
```

**Guideline:**
- **Light load (<100 QPS):** 0.25-0.5 CPU
- **Moderate load (100-500 QPS):** 0.5-1.0 CPU
- **Heavy load (500+ QPS):** 1.0-2.0 CPU
- **DNSSEC enabled:** Add 0.25-0.5 CPU

### Monitoring Resource Usage

```bash
# Real-time stats
docker stats a-healthy-dns

# Check memory spikes
docker stats --no-stream a-healthy-dns

# View multiple containers
docker stats
```

## Networking

### Port Mapping

```bash
# Map host port 53 to container port 53
docker run -d -p 53:53/udp ...

# Map host port 53053 to container port 53
docker run -d -p 53053:53/udp -e DNS_PORT="53" ...

# Bind to specific interface
docker run -d -p 192.168.1.10:53:53/udp ...
```

### Network Modes

**Bridge (default):**
```bash
docker run -d ... indisoluble/a-healthy-dns
```
- Isolated network namespace
- Requires port mapping
- Better isolation

**Host:**
```bash
docker run -d --network host ... indisoluble/a-healthy-dns
```
- Shares host network stack
- No port mapping needed
- Lower latency, less isolation

**Custom bridge:**
```yaml
# docker-compose.yml
networks:
  dns-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### DNS Resolution from Container

The container needs to reach backend IPs for health checks:

```bash
# Test connectivity from container
docker exec a-healthy-dns ping -c 1 192.168.1.100
docker exec a-healthy-dns nc -zv 192.168.1.100 8080

# Check DNS resolution (if using hostnames)
docker exec a-healthy-dns nslookup backend1.local
```

## Security Hardening

### Run as Non-Root

Built into image (UID/GID 10000):
```bash
# User already configured in image
docker run ... indisoluble/a-healthy-dns

# Or override if needed
docker run --user 10000:10000 ... indisoluble/a-healthy-dns
```

### Capability Management

```bash
# Minimal capabilities
docker run -d \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  -p 53:53/udp \
  -e DNS_PORT="53" \
  ... \
  indisoluble/a-healthy-dns
```

### Read-Only Root Filesystem

```bash
# Make root filesystem read-only
docker run -d \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid \
  ... \
  indisoluble/a-healthy-dns
```

### Security Options

```bash
docker run -d \
  --security-opt=no-new-privileges:true \
  --security-opt=apparmor=docker-default \
  ... \
  indisoluble/a-healthy-dns
```

### DNSSEC Key Security

```bash
# Restrict key file permissions
chmod 600 keys/private.pem
chown 10000:10000 keys/private.pem

# Mount as read-only
docker run -d \
  -v ./keys:/app/keys:ro \
  ... \
  indisoluble/a-healthy-dns
```

## Troubleshooting

For Docker-specific issues — container exits immediately, port binding failures, health check connectivity, and resource limits — see [docs/troubleshooting.md](troubleshooting.md).

## Image Maintenance

### Pulling Updates

```bash
# Pull latest image
docker pull indisoluble/a-healthy-dns:latest

# Pull specific version
docker pull indisoluble/a-healthy-dns:v0.1.26
```

### Version Pinning

```bash
# Pin to specific version (recommended for production)
docker run -d ... indisoluble/a-healthy-dns:v0.1.26

# Use latest (for development)
docker run -d ... indisoluble/a-healthy-dns:latest
```

### Image Cleanup

```bash
# Remove unused images
docker image prune -a

# Remove specific image
docker rmi indisoluble/a-healthy-dns:v0.1.25

# Remove dangling images
docker image prune
```

## Integration with Orchestrators

### Kubernetes

Example pod spec:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: a-healthy-dns
spec:
  containers:
  - name: dns
    image: indisoluble/a-healthy-dns:latest
    ports:
    - containerPort: 53
      protocol: UDP
    env:
    - name: DNS_HOSTED_ZONE
      value: "sub.domain.com"
    - name: DNS_ZONE_RESOLUTIONS
      value: '{"www":{"ips":["192.168.1.100"],"health_port":8080}}'
    - name: DNS_NAME_SERVERS
      value: '["ns1.domain.com"]'
    - name: DNS_PORT
      value: "53"
    resources:
      limits:
        memory: "256Mi"
        cpu: "500m"
    securityContext:
      runAsNonRoot: true
      runAsUser: 10000
      capabilities:
        drop: ["ALL"]
        add: ["NET_BIND_SERVICE"]
```

### Docker Swarm

```bash
docker service create \
  --name a-healthy-dns \
  --publish 53:53/udp \
  --replicas 3 \
  --env DNS_HOSTED_ZONE="sub.domain.com" \
  --env DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  --env DNS_NAME_SERVERS='["ns1.domain.com"]' \
  --limit-memory 256m \
  --limit-cpu 0.5 \
  indisoluble/a-healthy-dns
```
