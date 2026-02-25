# Decisions

## Architectural Decision Records

### 2025-XX-XX: UDP-Only DNS Transport
**Status**: Implemented
**Context**: DNS supports both UDP and TCP transport. TCP is required for zone transfers (AXFR) and responses exceeding 512 bytes (or EDNS0 limits).
**Decision**: Support UDP only. No TCP transport.
**Rationale**: The server is authoritative-only, no zone transfers. Health-based A records produce small responses well within UDP limits. Simplifies implementation with stdlib `socketserver.UDPServer`.
**Consequences**: Cannot serve large zones or support AXFR. Clients needing TCP will fail.

### 2025-XX-XX: TCP Connect as Health Check
**Status**: Implemented
**Context**: Health checking could use HTTP, ICMP ping, TCP connect, or custom protocols.
**Decision**: Use `socket.create_connection()` (TCP SYN→ACK) with configurable timeout.
**Rationale**: TCP connect is the most universal health signal — works with any TCP service without requiring HTTP endpoints or ICMP privileges. No agent needed on backends.
**Consequences**: Cannot check application-layer health (e.g. HTTP 200). A TCP-listening but unhealthy app will appear healthy.
**References**: `tools/can_create_connection.py`

### 2025-XX-XX: Versioned Zone for Thread Safety
**Status**: Implemented
**Context**: The DNS zone is read by the server thread and written by the updater thread concurrently.
**Decision**: Use `dns.versioned.Zone` with `reader()`/`writer()` transactions.
**Rationale**: dnspython's versioned zone provides MVCC-style isolation — readers see a consistent snapshot while the writer rebuilds the zone atomically.
**Consequences**: Tied to dnspython's versioned zone API. Zone is fully recreated on each update (clear→add→sign), not incrementally patched.
**References**: `dns_server_zone_updater.py:_recreate_zone()`

### 2025-XX-XX: Full Zone Recreation vs Incremental Updates
**Status**: Implemented
**Context**: Zone updates could either patch individual records or recreate the entire zone.
**Decision**: Full zone recreation (clear all nodes → re-add all records → re-sign).
**Rationale**: Simpler and more deterministic. Zone is small (handful of subdomains). DNSSEC signing requires touching all records anyway. Avoids complex diff logic.
**Consequences**: Slightly more work per update cycle, but negligible for expected zone sizes.
**References**: `dns_server_zone_updater.py:_recreate_zone()`

### 2025-XX-XX: Timing Hierarchy Derived from max_interval
**Status**: Implemented
**Context**: DNS TTLs, SOA parameters, and DNSSEC signature lifetimes need to be coherent.
**Decision**: Derive all timing values from a single `max_interval` using fixed multipliers in `records/time.py`.
**Rationale**: Ensures all TTLs are proportional and consistent. A single tuning knob (test interval) controls the entire timing hierarchy.
**Consequences**: Less flexibility for fine-tuning individual TTLs. All timing changes proportionally.
**References**: `records/time.py`

### 2025-XX-XX: Immutable Value Objects for Domain Model
**Status**: Implemented
**Context**: `AHealthyIp` and `AHealthyRecord` need to be compared and stored in sets.
**Decision**: Make them immutable — update methods return new instances. Use `FrozenSet` for collections.
**Rationale**: Thread safety (shared between updater and server threads), hashability for set operations, simpler reasoning about state.
**Consequences**: More object allocations per update cycle (new instances on change). Acceptable for the scale.
**References**: `records/a_healthy_ip.py`, `records/a_healthy_record.py`
