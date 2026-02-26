# Architectural Decisions

**Format**: Each decision follows ADR (Architecture Decision Record) structure

---

## 2026-02-26: Memory Bank Initialization

**Status**: Approved  
**Context**: Establishing memory bank for AI-assisted development per AGENTS 2.1 spec  
**Decision**: Create memory bank from codebase analysis, not external documentation  
**Alternatives**: 
- Use README/docstrings only - Rejected: Insufficient detail for complex work
- Manual documentation - Rejected: Inconsistent, hard to maintain

**Consequences**:
- **Positive**: Single source of truth for AI agents, comprehensive project understanding
- **Negative**: Initial time investment, requires maintenance
- **Risks**: Documentation drift if not updated with changes

**References**: AGENTS.md specification

---

## [Inferred] dnspython for DNS Protocol

**Status**: Approved (Inferred from implementation)  
**Context**: Need DNS protocol implementation for zone management and query processing  
**Decision**: Use dnspython library for all DNS operations  
**Alternatives**:
- Raw socket + struct - Rejected: Complex, error-prone, no DNSSEC support
- BIND libraries - Rejected: C dependency, harder to deploy
- Custom protocol implementation - Rejected: Reinventing wheel

**Consequences**:
- **Positive**: Battle-tested implementation, DNSSEC out-of-box, thread-safe zones
- **Negative**: Heavy dependency (~2MB), learning curve
- **Risks**: Breaking changes in dnspython major versions

**References**: 
- [techContext.md#Key Dependencies](./techContext.md)
- All modules in codebase

---

## [Inferred] Threading Over Asyncio

**Status**: Approved (Inferred from implementation)  
**Context**: Need concurrent health checks while serving DNS queries  
**Decision**: Use threading with single background thread for health checks  
**Alternatives**:
- Asyncio - Rejected: socketserver.UDPServer is synchronous, dnspython Zone not async-safe
- Multiprocessing - Rejected: Overkill for single zone, IPC complexity
- Blocking single thread - Rejected: Health checks block DNS queries

**Consequences**:
- **Positive**: Simple integration with socketserver, dnspython thread-safe Zone
- **Negative**: Less scalable than asyncio for many concurrent health checks
- **Risks**: Thread coordination bugs (mitigated by Event-based shutdown)

**References**: 
- [indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py](indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py)
- [systemPatterns.md#Threaded Background Processing](./systemPatterns.md)

---

## [Inferred] Immutable Data Structures

**Status**: Approved (Inferred from implementation)  
**Context**: Need thread-safe data sharing between updater and handler threads  
**Decision**: All domain objects use immutable structures (NamedTuple, FrozenSet)  
**Alternatives**:
- Mutable classes with locks - Rejected: Deadlock risk, complex synchronization
- Copy-on-write with locks - Rejected: Lock contention, error-prone
- Actor model - Rejected: Overkill, adds framework dependency

**Consequences**:
- **Positive**: Thread-safe without locks, clear mutation points, easier testing
- **Negative**: More object allocation, less familiar to some developers
- **Risks**: Performance impact from allocations (acceptable for current scale)

**References**: 
- [indisoluble/a_healthy_dns/records/a_healthy_ip.py:49-57](indisoluble/a_healthy_dns/records/a_healthy_ip.py#L49-L57)
- [systemPatterns.md#Immutable Data Structures](./systemPatterns.md)

---

## [Inferred] TCP Health Checks Only

**Status**: Approved (Inferred from implementation)  
**Context**: Need to test backend availability for DNS responses  
**Decision**: Use TCP connectivity tests (socket.create_connection) only  
**Alternatives**:
- HTTP(S) health checks - Rejected: Scope creep, not all services have HTTP
- ICMP ping - Rejected: Requires elevated privileges, doesn't test service
- Application-specific protocols - Rejected: Too complex, service-dependent

**Consequences**:
- **Positive**: Universal (any TCP service), fast, simple, no elevated privileges
- **Negative**: Doesn't validate application health (connection != healthy app)
- **Risks**: False positives if service accepts connections but not serving

**References**: 
- [indisoluble/a_healthy_dns/tools/can_create_connection.py](indisoluble/a_healthy_dns/tools/can_create_connection.py)
- [techContext.md#Why TCP Health Checks Only](./techContext.md)

---

## [Inferred] Transaction-Based Zone Updates

**Status**: Approved (Inferred from implementation)  
**Context**: Zone must remain consistent even if health checks interrupted  
**Decision**: Use dnspython's `Zone.writer()` context manager for atomic updates  
**Alternatives**:
- Manual locking - Rejected: Error-prone, dnspython already provides transactions
- Optimistic concurrency - Rejected: Retry complexity unnecessary for single updater
- No transactions - Rejected: Partial updates visible to queries

**Consequences**:
- **Positive**: Atomic updates, exception-safe, reader/writer isolation
- **Negative**: Must recreate entire zone on changes (acceptable for small zones)
- **Risks**: Zone writer blocks readers briefly (acceptable for update frequency)

**References**: 
- [indisoluble/a_healthy_dns/dns_server_zone_updater.py:175-179](indisoluble/a_healthy_dns/dns_server_zone_updater.py#L175-L179)
- [systemPatterns.md#Transaction-Based Zone Updates](./systemPatterns.md)

---

## [Inferred] Single Zone Per Instance

**Status**: Approved (Inferred from implementation)  
**Context**: Scope limitation for initial release  
**Decision**: Each server instance manages one primary zone + aliases  
**Alternatives**:
- Multiple unrelated zones - Rejected: Complicates configuration, adds little value
- Zone delegation - Rejected: Out of scope for authoritative-only server
- Dynamic zone loading - Rejected: Restart acceptable for configuration changes

**Consequences**:
- **Positive**: Simpler configuration, clearer operational model
- **Negative**: Need multiple instances for multiple zones
- **Risks**: Scaling limitations (acceptable for target use cases)

**References**: 
- [indisoluble/a_healthy_dns/dns_server_config_factory.py:30-32](indisoluble/a_healthy_dns/dns_server_config_factory.py#L30-L32)

---

## [Inferred] CLI-Only Configuration

**Status**: Approved (Inferred from implementation)  
**Context**: Configuration method for server startup  
**Decision**: Use CLI arguments with JSON for complex structures  
**Alternatives**:
- Config file (YAML/TOML) - Rejected: Adds dependency, less container-friendly
- Environment variables - Rejected: Complex structures hard to express
- REST API configuration - Rejected: Adds attack surface, scope creep

**Consequences**:
- **Positive**: Single-binary deployment, container-friendly, no file management
- **Negative**: Long command lines for complex configs, JSON escaping in shell
- **Risks**: Configuration errors harder to validate (mitigated by detailed validation)

**References**: 
- [indisoluble/a_healthy_dns/main.py:58-207](indisoluble/a_healthy_dns/main.py#L58-L207)

---

## [Inferred] No Persistent Storage

**Status**: Approved (Inferred from implementation)  
**Context**: Zone data storage strategy  
**Decision**: In-memory zone only, recreated from configuration on startup  
**Alternatives**:
- Database storage - Rejected: Adds dependency, complexity, not needed
- File-based zone files - Rejected: Zone is dynamic, file would be stale
- External zone provider - Rejected: Defeats purpose of health-aware DNS

**Consequences**:
- **Positive**: Simple deployment, no state management, stateless containers
- **Negative**: Zone lost on restart (acceptable, rebuilds in seconds)
- **Risks**: None - zone is derived from health checks, not authoritative source

**References**: 
- [indisoluble/a_healthy_dns/dns_server_zone_updater.py:111-113](indisoluble/a_healthy_dns/dns_server_zone_updater.py#L111-L113)

---

## [Inferred] Docker Non-Root User with Capabilities

**Status**: Approved (Inferred from Dockerfile)  
**Context**: Security and privileged port binding in containers  
**Decision**: Run as non-root user (uid 10000), grant CAP_NET_BIND_SERVICE  
**Alternatives**:
- Root user - Rejected: Security risk, unnecessary privileges
- Port forwarding (53053 → 53) - Rejected: Extra container complexity
- Host network mode - Rejected: Breaks container isolation

**Consequences**:
- **Positive**: Minimal privileges, security best practice, can bind port 53
- **Negative**: Capability grant required (not all orchestrators support)
- **Risks**: Capability misconfiguration breaks port binding

**References**: 
- [Dockerfile:33-49](Dockerfile#L33-L49)

---

## Future Decisions Needed

### Potential Areas Requiring ADRs

1. **Metrics/Observability**: How to expose health check metrics?
   - Options: Prometheus endpoint, StatsD, structured logs
   - Timeline: When metrics become required feature

2. **Async Migration**: Should we migrate to asyncio?
   - Options: Full rewrite, hybrid approach, stay with threading
   - Timeline: If query rate becomes bottleneck

3. **HTTP Health Checks**: Add HTTP(S) health check support?
   - Options: Add as alternative, replace TCP, plugin system
   - Timeline: If TCP-only becomes limiting

4. **Configuration Reload**: Support hot-reload without restart?
   - Options: SIGHUP handler, inotify, REST API
   - Timeline: If restart disruption becomes problem

5. **Multi-Zone Support**: Multiple unrelated zones per instance?
   - Options: Full multi-zone, maintain single-zone, separate binary
   - Timeline: If user demand materializes
