# Project Brief: A Healthy DNS

**Version**: 0.1.26  
**Python**: ≥3.10  
**Status**: Production-ready

## Vision

A health-aware authoritative DNS server that dynamically responds with only healthy IP addresses based on real-time TCP connectivity checks. Enables high availability by automatically excluding failed endpoints from DNS responses.

## Core Objective

Provide DNS resolution that automatically adapts to backend health status, eliminating the need for manual DNS updates when servers fail or recover.

## Key Features

### 1. Health-Aware DNS Resolution
- Continuous TCP connectivity testing to configured health check ports
- Automatic inclusion/exclusion of IPs based on health status
- Configurable health check intervals and timeouts
- Per-subdomain health monitoring with multiple IPs per record

### 2. Authoritative DNS Server
- UDP-based DNS query handling
- Support for A, NS, SOA record types
- Alias zone support (multiple domains resolving to same records)
- RFC-compliant DNS responses with authoritative answer flag

### 3. DNSSEC Support (Optional)
- Zone signing with RSA-SHA256 (configurable algorithm)
- Automatic signature regeneration before expiration
- DNSKEY and RRSIG record management
- Private key-based signing

### 4. Dynamic Zone Management
- Thread-based background zone updates
- Transaction-safe zone modifications using dnspython's versioned zones
- SOA serial auto-increment with time-based uniqueness
- TTL calculation based on health check intervals

## Use Cases

### Primary: High-Availability Load Balancing
Deploy health-aware DNS for services with multiple backend servers:
- Web servers behind DNS round-robin
- API endpoints with redundant instances
- Microservices with multiple replicas
- Geographic failover scenarios

### Secondary: Development/Testing
- Local development DNS for microservice environments
- Integration testing with simulated failures
- Health check validation in CI/CD pipelines

## Non-Goals

- **NOT** a recursive DNS resolver (authoritative only)
- **NOT** a caching DNS server
- **NOT** a DNS proxy or forwarder
- **NO** HTTP/HTTPS health checks (TCP connectivity only)
- **NO** advanced load balancing algorithms (DNS round-robin only)
- **NO** persistent health check history/metrics storage

## Success Metrics

1. **Reliability**: Zone updates never fail mid-transaction
2. **Responsiveness**: Health checks complete within configured timeout
3. **Accuracy**: DNS responses reflect current health status within one update cycle
4. **Security**: DNSSEC signatures valid and auto-renewed before expiration

## Constraints

- Python 3.10+ required for type hints and modern features
- UDP-only DNS (no TCP DNS support)
- Single-threaded zone updater (one background thread)
- In-memory zone storage only (no persistence)
- TCP health checks only (no application-level health protocols)
