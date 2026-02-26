# Product Context

**Last Updated**: 2026-02-26

## User Personas

### DevOps Engineer (Primary)
**Goals**: 
- Automate DNS failover without manual intervention
- Reduce MTTR when backend services fail
- Simplify DNS management for microservices

**Pain Points**:
- Manual DNS updates during outages
- DNS TTL delays in failover scenarios
- Complexity of commercial DNS health checking solutions

**Value Delivered**: Zero-config DNS failover with sub-minute detection

### Platform Engineer (Secondary)
**Goals**:
- Provide self-service DNS for development teams
- Enable local development with production-like DNS behavior
- Containerized deployment for Kubernetes/Docker environments

**Pain Points**:
- Corporate DNS doesn't support local development
- Static DNS records don't reflect dynamic container environments
- Third-party DNS services require network access

**Value Delivered**: Containerized, self-hosted DNS with health awareness

## Market Position

### Alternatives Comparison

| Feature | A Healthy DNS | Route53 Health | CoreDNS | PowerDNS |
|---------|---------------|----------------|---------|----------|
| Health checking | ✅ Built-in | ✅ Paid | ❌ Plugin | ✅ External |
| Self-hosted | ✅ Yes | ❌ Cloud | ✅ Yes | ✅ Yes |
| DNSSEC | ✅ Auto-sign | ✅ Manual | ✅ Yes | ✅ Yes |
| Zero config | ✅ CLI args | ❌ Complex | ⚠️ Config file | ❌ Database |
| Docker ready | ✅ Yes | N/A | ✅ Yes | ⚠️ Complex |

### Differentiation
- **Simplicity**: Single binary, CLI-only configuration
- **Integration**: Health checks without external monitoring
- **Portability**: Pure Python, runs anywhere
- **Development**: Perfect for local microservice environments

## Usage Patterns

### Pattern 1: Docker Compose Stack
```bash
docker-compose up
# DNS automatically tracks container health
```
**Frequency**: Every development session  
**User Impact**: Eliminates manual DNS updates during container restarts

### Pattern 2: Kubernetes Sidecar
```yaml
# Deploy as sidecar to track pod health
```
**Frequency**: Per-namespace deployment  
**User Impact**: Namespace-local DNS with pod awareness

### Pattern 3: Standalone Failover
```bash
a-healthy-dns --hosted-zone example.com \
  --zone-resolutions '{"api":{"ips":["10.0.1.1","10.0.1.2"],"health_port":8080}}'
```
**Frequency**: Production multi-DC deployments  
**User Impact**: Automatic cross-DC failover

## Integration Points

### Upstream Systems
- **None** - Authoritative only, no forwarding

### Downstream Systems
- **Client Resolvers**: Standard DNS clients (dig, nslookup, system resolver)
- **Health Check Targets**: Any TCP-listening service
- **Monitoring**: Logs to stdout/stderr (standard logging module)

### Configuration Sources
- **CLI Arguments**: Primary configuration method
- **Environment Variables**: Docker/K8s deployment
- **DNSSEC Keys**: PEM file on filesystem

## Deployment Environments

### Local Development (Primary)
- Docker Compose with health check ports
- Non-privileged port (53053 default)
- No DNSSEC required

### Production (Secondary)
- Containerized deployment with capability grants for port 53
- DNSSEC with pre-generated keys
- Monitoring via log aggregation

### Testing/CI (Tertiary)
- In-process testing with pytest
- Mocked health checks
- Zone transaction validation
