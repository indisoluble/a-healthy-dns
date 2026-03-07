# Project Brief

## Overview

A Healthy DNS is a health-aware authoritative DNS server that automatically manages DNS responses based on backend service health. It continuously monitors configured endpoints and dynamically updates DNS zones to return only healthy IP addresses, providing automatic failover and primitive load balancing at the DNS layer.

## Goals

### Primary Goals

1. **Health-aware DNS responses** — Only return IP addresses that pass TCP connectivity tests
2. **Automatic failover** — Remove unhealthy endpoints from DNS responses without manual intervention
3. **Continuous monitoring** — Background health checking at configurable intervals
4. **Multi-domain efficiency** — Serve multiple domains (hosted + aliases) sharing the same backend IPs without duplicating health checks
5. **DNSSEC support** — Optional zone signing for secure DNS deployment
6. **Operational simplicity** — Single-process deployment with minimal configuration surface

### Secondary Goals

1. **Configurable TTLs** — TTL calculation based on health check intervals to balance caching vs responsiveness
2. **Multiple backends per subdomain** — Support multiple IP addresses per subdomain with individual health tracking
3. **Graceful degradation** — Subdomain returns NXDOMAIN when all backends are unhealthy (fail closed)
4. **Docker-first deployment** — Containerized operation as the primary deployment model
5. **Transparent operations** — Comprehensive logging for health check results and zone updates

## Non-Goals

### Explicitly Out of Scope

1. **Recursive DNS resolver** — This is an authoritative-only server for configured zones
2. **Application-layer health checks** — Health checks are TCP connectivity only (no HTTP, gRPC, custom protocols)
3. **Full-featured load balancer** — DNS-level distribution only; no request-level load balancing, session affinity, or traffic shaping
4. **Comprehensive monitoring platform** — Health check results are used for DNS decisions, not exposed as a monitoring API
5. **All DNS record types** — Focus on A records, NS, SOA, and DNSSEC; no MX, CNAME, TXT, SRV, etc.
6. **Dynamic configuration updates** — Configuration is loaded at startup; changes require restart
7. **Multi-master coordination** — No built-in mechanism for coordinating multiple DNS server instances
8. **Persistent health state** — Health status is in-memory only; resets on restart

## Constraints

### Technical Constraints

1. **Python 3.10+ required** — Uses modern Python features and type hints
2. **TCP-only health checks** — Health determination is based solely on TCP socket connectivity success/failure
3. **UDP DNS protocol** — Authoritative server responds to UDP DNS queries only (no TCP DNS, no DoH, no DoT)
4. **Thread-based concurrency** — Background health checking uses threading, not async/await or multiprocessing
5. **In-memory zone storage** — DNS zone data stored in memory using dnspython's versioned zones
6. **Single-process architecture** — One Python process handles DNS queries and health checks

### Dependency Constraints

1. **dnspython (2.8.0+, <3.0.0)** — Core DNS protocol handling and zone management
2. **cryptography (46.0.5+, <47.0.0)** — DNSSEC cryptographic operations

### Operational Constraints

1. **All health checks share timeout** — Single `connection_timeout` setting applies to all IP addresses
2. **All health checks share interval** — Single `min_interval` setting applies to all IP addresses (though adjusted upward if insufficient)
3. **Health check timing precision** — Loop-based health checking with sleep intervals; not real-time event-driven
4. **Restart required for config changes** — No hot-reload capability

## Requirements

### Functional Requirements

#### FR-1: Health Checking
- **FR-1.1** — Perform TCP connectivity tests to configured IP addresses on specified health ports
- **FR-1.2** — Mark IP addresses as healthy if TCP connection succeeds within timeout
- **FR-1.3** — Mark IP addresses as unhealthy if TCP connection fails or times out
- **FR-1.4** — Execute health checks continuously in background thread
- **FR-1.5** — Respect `min_interval` between consecutive health check cycles

#### FR-2: Dynamic Zone Updates
- **FR-2.1** — Update DNS zone A records based on current health status
- **FR-2.2** — Include only healthy IP addresses in DNS responses
- **FR-2.3** — Return NXDOMAIN when all IP addresses for a subdomain are unhealthy
- **FR-2.4** — Sign zone with DNSSEC when private key is provided
- **FR-2.5** — Update SOA serial and timestamps on zone changes

#### FR-3: DNS Query Handling
- **FR-3.1** — Listen for UDP DNS queries on configured port
- **FR-3.2** — Respond to A record queries for configured subdomains
- **FR-3.3** — Respond to NS record queries for zone name servers
- **FR-3.4** — Respond to SOA record queries for zone metadata
- **FR-3.5** — Return authoritative answers (AA flag set)
- **FR-3.6** — Return NXDOMAIN for unknown subdomains or non-hosted zones

#### FR-4: Multi-Domain Support
- **FR-4.1** — Accept queries for hosted zone
- **FR-4.2** — Accept queries for alias zones
- **FR-4.3** — Resolve alias zone queries to same IPs as hosted zone
- **FR-4.4** — Perform health checks once regardless of number of alias zones

#### FR-5: Configuration
- **FR-5.1** — Accept hosted zone name
- **FR-5.2** — Accept zone resolutions (subdomain → IPs + health port mapping) as JSON
- **FR-5.3** — Accept name servers list as JSON
- **FR-5.4** — Accept optional alias zones as JSON
- **FR-5.5** — Accept optional DNSSEC private key path and algorithm
- **FR-5.6** — Accept optional port, test interval, timeout, log level

### Non-Functional Requirements

#### NFR-1: Performance
- **NFR-1.1** — DNS query response time under 10ms for in-memory zones
- **NFR-1.2** — Support at least 100 queries per second on modest hardware
- **NFR-1.3** — Health check loop completes within `min_interval` under normal conditions

#### NFR-2: Reliability
- **NFR-2.1** — Health check failures do not crash DNS query handling
- **NFR-2.2** — DNS query handling failures do not crash health checking
- **NFR-2.3** — Zone updates are transactional (commit/rollback)
- **NFR-2.4** — Graceful shutdown on SIGTERM/SIGINT

#### NFR-3: Observability
- **NFR-3.1** — Log health check results (success/failure) at debug level
- **NFR-3.2** — Log zone updates at info level
- **NFR-3.3** — Log DNS query results at debug level
- **NFR-3.4** — Log configuration validation errors at error level
- **NFR-3.5** — Support log levels: debug, info, warning, error, critical

#### NFR-4: Deployment
- **NFR-4.1** — Provide official Docker image on Docker Hub
- **NFR-4.2** — Support environment variable configuration in Docker
- **NFR-4.3** — Support pip installation from source
- **NFR-4.4** — Provide `a-healthy-dns` CLI entry point

#### NFR-5: Correctness
- **NFR-5.1** — Validate all configuration inputs (IP addresses, ports, subdomains, zone names)
- **NFR-5.2** — Fail fast on invalid configuration at startup
- **NFR-5.3** — Maintain test coverage for core logic
- **NFR-5.4** — Use type hints for static analysis

## Success Criteria

The project achieves its goals when:

1. **Health-driven DNS** — Unhealthy backends are automatically removed from DNS responses within one health check interval
2. **Zero-touch failover** — Service disruption triggers DNS updates without operator intervention
3. **Production readiness** — Successfully deployed in production serving real traffic
4. **Docker adoption** — Docker image is the primary deployment method
5. **Minimal configuration** — Operators can deploy with only hosted zone, resolutions, and name servers

## Risks and Mitigations

### Risk 1: False Negatives (healthy marked unhealthy)
- **Impact:** Removes working backends from rotation
- **Mitigation:** Configurable timeout; operators tune based on network conditions

### Risk 2: False Positives (unhealthy marked healthy)
- **Impact:** DNS returns broken endpoints
- **Mitigation:** TCP connectivity is a strong signal; application-layer failures still possible but rare

### Risk 3: DNS Cache Delay
- **Impact:** Clients cache stale records after health status change
- **Mitigation:** TTL calculated to balance freshness vs cache efficiency; operators can tune `min_interval`

### Risk 4: Thread Safety Issues
- **Impact:** Race conditions between health checker and DNS handler
- **Mitigation:** Use dnspython's versioned zones with transactional updates and reader locks

---

**Last Updated:** March 7, 2026  
**Version:** 1.0 (Bootstrap)
