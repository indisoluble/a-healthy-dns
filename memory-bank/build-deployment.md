# Build & Deployment

**Last Updated**: 2026-02-26

## Local Development

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)
- Optional: Docker for containerized testing

### Setup Development Environment
```bash
# Clone repository
git clone https://github.com/indisoluble/a-healthy-dns.git
cd a-healthy-dns

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode with dependencies
pip install -e .
```

### Verify Installation
```bash
# Check command available
a-healthy-dns --help

# Run tests
pytest tests/

# Run with example configuration
a-healthy-dns \
  --hosted-zone example.local \
  --zone-resolutions '{"www":{"ips":["127.0.0.1"],"health_port":8080}}' \
  --ns '["ns1.example.local"]' \
  --port 53053 \
  --log-level debug
```

---

## Build Process

### Python Package Build
```bash
# Install build tools
pip install build

# Build source distribution and wheel
python -m build

# Output: dist/a_healthy_dns-0.1.26.tar.gz
#         dist/a_healthy_dns-0.1.26-py3-none-any.whl
```

### Install from Wheel
```bash
pip install dist/a_healthy_dns-0.1.26-py3-none-any.whl
```

---

## Docker Build

### Build Image
```bash
# From repository root
docker build -t a-healthy-dns:latest .

# With specific version tag
docker build -t a-healthy-dns:0.1.26 .

# Build for specific platform
docker build --platform linux/amd64 -t a-healthy-dns:latest .
```

### Multi-Stage Build Details
The Dockerfile uses multi-stage build for minimal image size:

**Stage 1: Builder**
- Base: `python:3-slim`
- Installs build dependencies (gcc, rust, etc.)
- Builds Python packages with native extensions
- Result: Compiled packages in `/root/.local`

**Stage 2: Production**
- Base: `python:3-slim`
- Copies only compiled packages from builder
- Creates non-root user (appuser:appuser, uid/gid 10000)
- Grants CAP_NET_BIND_SERVICE capability for port 53 binding
- Final image: ~200MB (vs ~500MB without multi-stage)

### Image Security Features
1. **Non-root user**: Runs as `appuser` (uid 10000)
2. **Minimal attack surface**: Only runtime dependencies
3. **Capability-based privileges**: CAP_NET_BIND_SERVICE only
4. **DNSSEC key isolation**: Dedicated `/app/keys` directory (mode 700)
5. **Tini init**: Proper signal handling and zombie reaping

---

## Docker Deployment

### Run Container (Non-Privileged Port)
```bash
docker run -d \
  --name healthy-dns \
  -p 53053:53053/udp \
  a-healthy-dns:latest \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  --ns '["ns1.example.com"]' \
  --port 53053
```

### Run Container (Privileged Port 53)
```bash
docker run -d \
  --name healthy-dns \
  -p 53:53/udp \
  --cap-add NET_BIND_SERVICE \
  a-healthy-dns:latest \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  --ns '["ns1.example.com"]' \
  --port 53
```

**Note**: `--cap-add NET_BIND_SERVICE` allows binding to privileged ports

### Run with DNSSEC
```bash
# Generate DNSSEC keys first (outside container)
dnssec-keygen -a RSASHA256 -b 2048 -n ZONE example.com

docker run -d \
  --name healthy-dns \
  -p 53053:53053/udp \
  -v $(pwd)/Kexample.com.*.private:/app/keys/zone.key:ro \
  a-healthy-dns:latest \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  --ns '["ns1.example.com"]' \
  --priv-key-path /app/keys/zone.key \
  --priv-key-alg RSASHA256
```

### Environment Variables
Configuration via environment possible if wrapped in script:
```bash
docker run -d \
  --name healthy-dns \
  -e HOSTED_ZONE=example.com \
  -e ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e NAME_SERVERS='["ns1.example.com"]' \
  wrapper-image:latest
```

**Note**: Base image requires CLI args, wrapper needed for env vars

---

## Docker Compose

### Basic Setup
```yaml
version: '3.8'

services:
  dns:
    image: a-healthy-dns:latest
    container_name: healthy-dns
    ports:
      - "53053:53053/udp"
    command:
      - --hosted-zone=example.local
      - --zone-resolutions={"www":{"ips":["app"],"health_port":8080}}
      - --ns=["ns1.example.local"]
      - --log-level=info
    depends_on:
      - app
    networks:
      - internal

  app:
    image: nginx:alpine
    container_name: test-app
    ports:
      - "8080:80"
    networks:
      - internal

networks:
  internal:
    driver: bridge
```

### Multi-Service with Health Checks
```yaml
version: '3.8'

services:
  dns:
    image: a-healthy-dns:latest
    ports:
      - "53053:53053/udp"
    command:
      - --hosted-zone=myapp.local
      - --zone-resolutions={"api":{"ips":["api1","api2"],"health_port":8080},"web":{"ips":["web1","web2"],"health_port":80}}
      - --ns=["ns1.myapp.local"]
      - --test-min-interval=10
      - --test-timeout=2
    networks:
      - myapp

  api1:
    image: myapi:latest
    networks:
      myapp:
        aliases:
          - api1

  api2:
    image: myapi:latest
    networks:
      myapp:
        aliases:
          - api2

  web1:
    image: myweb:latest
    networks:
      myapp:
        aliases:
          - web1

  web2:
    image: myweb:latest
    networks:
      myapp:
        aliases:
          - web2

networks:
  myapp:
    driver: bridge
```

---

## Kubernetes Deployment

### Deployment Manifest
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: healthy-dns
  namespace: dns-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: healthy-dns
  template:
    metadata:
      labels:
        app: healthy-dns
    spec:
      securityContext:
        runAsUser: 10000
        runAsGroup: 10000
        fsGroup: 10000
      containers:
      - name: dns
        image: a-healthy-dns:0.1.26
        args:
          - --hosted-zone=example.com
          - --zone-resolutions={"www":{"ips":["192.168.1.100","192.168.1.101"],"health_port":8080}}
          - --ns=["ns1.example.com","ns2.example.com"]
          - --port=53053
        ports:
        - name: dns
          containerPort: 53053
          protocol: UDP
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
        livenessProbe:
          exec:
            command:
            - /bin/sh
            - -c
            - pgrep -f a-healthy-dns
          initialDelaySeconds: 10
          periodSeconds: 30
```

### Service Manifest
```yaml
apiVersion: v1
kind: Service
metadata:
  name: healthy-dns
  namespace: dns-system
spec:
  type: LoadBalancer
  ports:
  - name: dns-udp
    port: 53
    targetPort: 53053
    protocol: UDP
  selector:
    app: healthy-dns
```

### ConfigMap for Complex Config
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dns-config
  namespace: dns-system
data:
  zone-resolutions: |
    {
      "www": {"ips": ["192.168.1.100", "192.168.1.101"], "health_port": 8080},
      "api": {"ips": ["192.168.1.200", "192.168.1.201"], "health_port": 8000}
    }
  name-servers: |
    ["ns1.example.com", "ns2.example.com"]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: healthy-dns
spec:
  template:
    spec:
      containers:
      - name: dns
        image: a-healthy-dns:0.1.26
        env:
        - name: ZONE_RESOLUTIONS
          valueFrom:
            configMapKeyRef:
              name: dns-config
              key: zone-resolutions
        - name: NAME_SERVERS
          valueFrom:
            configMapKeyRef:
              name: dns-config
              key: name-servers
        command:
        - /bin/sh
        - -c
        - |
          a-healthy-dns \
            --hosted-zone=example.com \
            --zone-resolutions="$ZONE_RESOLUTIONS" \
            --ns="$NAME_SERVERS"
```

---

## Configuration Management

### Command-Line Arguments
**Primary method**: All configuration via CLI args

**Pros**:
- No config file management
- Container-friendly
- Version control in deployment manifests

**Cons**:
- Long command lines
- JSON escaping complexity

### Configuration File (Not Supported)
A Healthy DNS does not support config files. Use:
- Wrapper scripts for environment variable → CLI arg conversion
- Kubernetes ConfigMaps with shell expansion
- Docker Compose command arrays

### DNSSEC Key Management
```bash
# Generate key pair
dnssec-keygen -a RSASHA256 -b 2048 -n ZONE example.com

# Output:
#   Kexample.com.+008+12345.key      (public key)
#   Kexample.com.+008+12345.private  (private key)

# Use private key in deployment
--priv-key-path=/path/to/Kexample.com.+008+12345.private
--priv-key-alg=RSASHA256
```

**Security**:
- Store private keys in Kubernetes Secrets
- Mount as read-only volumes
- Restrict file permissions (mode 400)
- Rotate keys periodically

---

## Monitoring & Logging

### Log Levels
```bash
# Debug - Verbose, includes health check results
--log-level debug

# Info - Standard operational logs (default)
--log-level info

# Warning - Issues that don't stop operation
--log-level warning

# Error - Critical failures
--log-level error
```

### Log Format
```
2026-02-26 10:30:00,123 - INFO - main._main - DNS server listening on port 53053...
2026-02-26 10:30:05,456 - DEBUG - can_create_connection.can_create_connection - TCP connectivity test to '192.168.1.1:8080' successful
2026-02-26 10:30:05,789 - WARNING - dns_server_udp_handler._update_response - Received query for unknown subdomain: invalid.example.com.
```

**Fields**: timestamp - level - module.function - message

### Container Logs
```bash
# Docker logs
docker logs -f healthy-dns

# Kubernetes logs
kubectl logs -f deployment/healthy-dns -n dns-system

# Stern (multi-pod)
stern -n dns-system healthy-dns
```

### Health Check Monitoring
```bash
# Watch debug logs for health changes
docker logs -f healthy-dns 2>&1 | grep "health check"

# Count healthy vs unhealthy
docker logs healthy-dns 2>&1 | grep "from True to False" | wc -l  # Failures
docker logs healthy-dns 2>&1 | grep "from False to True" | wc -l  # Recoveries
```

---

## Performance Tuning

### Resource Requirements

**Minimum**:
- CPU: 100m (0.1 core)
- Memory: 128Mi
- Storage: None (ephemeral only)

**Recommended**:
- CPU: 250m (0.25 core)
- Memory: 256Mi
- Scale: 1 replica (stateless, multiple OK)

### Scaling Considerations
- **Horizontal**: Multiple replicas OK (stateless)
- **Vertical**: Limited by single-threaded health checks
- **Limits**: ~1000 IPs before cycle time exceeds intervals

### Health Check Tuning
```bash
# Fast failover (higher CPU)
--test-min-interval 10 --test-timeout 1

# Balanced
--test-min-interval 30 --test-timeout 2

# Conservative (lower CPU)
--test-min-interval 60 --test-timeout 5
```

**Formula**: max_cycle_time = (num_ips × timeout) + overhead  
**Goal**: max_cycle_time < min_interval

---

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker logs healthy-dns

# Common issues:
# - Invalid JSON in --zone-resolutions
# - Invalid IP addresses
# - Missing required arguments
```

### DNS Queries Return NXDOMAIN
```bash
# Verify zone configuration
docker exec healthy-dns sh -c 'a-healthy-dns --help'

# Check query matches hosted zone
dig @container-ip -p 53053 www.HOSTED-ZONE A

# Enable debug logging
docker run ... --log-level debug
```

### Health Checks Always Fail
```bash
# Test connectivity from container
docker exec healthy-dns nc -zv target-ip target-port

# Check network connectivity
docker network inspect bridge

# Verify target service listening
docker exec target-container netstat -ln | grep :8080
```

### High CPU Usage
```bash
# Check interval/timeout settings
# Reduce frequency or increase timeout
--test-min-interval 60  # Check less frequently

# Reduce number of IPs
# Split large zones across multiple instances
```

---

## Backup & Recovery

### No Persistent State
A Healthy DNS is stateless - all state is derived from:
1. Configuration (CLI arguments)
2. Runtime health checks

**Backup Strategy**: Version control deployment manifests

### Disaster Recovery
1. Redeploy container with same configuration
2. Zone rebuilds within one update cycle (~30-60s)
3. No data loss (health state is ephemeral)

---

## Security Hardening

### Container Security
```yaml
# Kubernetes SecurityContext
securityContext:
  runAsNonRoot: true
  runAsUser: 10000
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
    add:
      - NET_BIND_SERVICE
  readOnlyRootFilesystem: true
```

### Network Policies
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: healthy-dns-policy
spec:
  podSelector:
    matchLabels:
      app: healthy-dns
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector: {}  # Allow all pods in namespace
    ports:
    - protocol: UDP
      port: 53053
  egress:
  - to:
    - podSelector:
        matchLabels:
          health-check: enabled
    ports:
    - protocol: TCP
      port: 8080
```

### DNSSEC Key Security
- Store in Kubernetes Secrets (not ConfigMaps)
- Encrypt at rest (enable Secret encryption)
- Rotate keys periodically
- Audit key access logs
