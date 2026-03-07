# System Patterns and Architecture

## Overview

A Healthy DNS is a single-process Python application that combines:
- A UDP DNS server handling authoritative queries
- A background health checker monitoring backend IP addresses
- A dynamic zone updater applying health results to DNS responses

The architecture emphasizes simplicity, thread safety, and separation of concerns while maintaining high performance for DNS query handling.

## Architectural Principles

### Single-Process Architecture
- One Python process handles all operations (no multiprocessing)
- Two concurrent execution contexts:
  - Main thread: DNS query handling via `socketserver.UDPServer`
  - Background thread: health checking and zone updates via `DnsServerZoneUpdaterThreated`
- Shared state: `dns.versioned.Zone` with reader/writer locks

### Separation of Concerns
- **Configuration** (`dns_server_config_factory.py`) — validation and creation of immutable config
- **Health checking** (`dns_server_zone_updater.py`) — TCP connectivity tests and health status tracking
- **Zone management** (`dns_server_zone_updater.py`) — DNS zone construction and DNSSEC signing
- **Query handling** (`dns_server_udp_handler.py`) — UDP request/response processing
- **Records** (`records/` module) — value objects representing DNS data structures

### Immutability Where Practical
- Configuration objects are immutable `NamedTuple` instances
- Health IP objects return new instances on status change (copy-on-write)
- Zone origins and name servers are frozen sets

### Dependency Injection at Composition Root
- Health checking function (`can_create_connection`) injected with configured timeout
- A record factory (`make_a_record`) injected with calculated TTL
- External dependencies (time, network) isolated in `tools/` module for testability

## Component Structure

```
main.py                              — Entry point, signal handling, server lifecycle
├── dns_server_config_factory.py    — Config validation and assembly
├── dns_server_zone_updater_threated.py — Threaded wrapper for zone updates
│   └── dns_server_zone_updater.py  — Core health checking and zone management
│       ├── records/
│       │   ├── a_healthy_record.py — A record with health-aware IPs
│       │   ├── a_healthy_ip.py     — IP with health status and port
│       │   ├── a_record.py         — DNS A record factory (healthy IPs only)
│       │   ├── soa_record.py       — SOA record with dynamic serial
│       │   ├── ns_record.py        — NS record factory
│       │   ├── dnssec.py           — DNSSEC signing key management
│       │   ├── zone_origins.py     — Zone name normalization (hosted + aliases)
│       │   └── time.py             — TTL calculation logic
│       └── tools/
│           ├── can_create_connection.py — TCP connectivity test
│           ├── is_valid_*.py       — Input validation
│           ├── normalize_ip.py     — IP canonicalization
│           └── uint32_current_time.py — Timestamp utilities
└── dns_server_udp_handler.py       — UDP DNS request handler
```

## Core Patterns

### 1. Configuration Factory Pattern

**Location:** [indisoluble/a_healthy_dns/dns_server_config_factory.py](../indisoluble/a_healthy_dns/dns_server_config_factory.py)

**Purpose:** Centralized configuration validation and assembly

**Implementation:**
- `make_config(args: Dict[str, Any]) -> Optional[DnsServerConfig]`
- Validates all inputs (zones, IPs, ports, subdomains, DNSSEC keys)
- Returns `None` on validation failure (fail-fast at startup)
- Produces immutable `DnsServerConfig` NamedTuple containing:
  - `zone_origins: ZoneOrigins` — hosted zone + aliases
  - `name_servers: FrozenSet[str]` — NS records
  - `a_records: FrozenSet[AHealthyRecord]` — A records with health tracking
  - `ext_private_key: Optional[ExtendedPrivateKey]` — DNSSEC key pair

**Benefits:**
- All validation happens once at startup
- Core logic operates on validated data only
- Configuration immutability prevents accidental mutation

### 2. Value Object Pattern

**Locations:**
- [indisoluble/a_healthy_dns/records/a_healthy_ip.py](../indisoluble/a_healthy_dns/records/a_healthy_ip.py)
- [indisoluble/a_healthy_dns/records/a_healthy_record.py](../indisoluble/a_healthy_dns/records/a_healthy_record.py)

**Purpose:** Represent domain concepts with value semantics

**Key Value Objects:**

#### `AHealthyIp`
```python
AHealthyIp(ip: str, health_port: int, is_healthy: bool)
```
- Immutable IP address with health status
- Validates IP and port on construction
- Copy-on-write via `updated_status(is_healthy: bool) -> AHealthyIp`
- Equality based on IP, port, and health status

#### `AHealthyRecord`
```python
AHealthyRecord(subdomain: dns.name.Name, healthy_ips: List[AHealthyIp])
```
- DNS A record containing multiple IPs with health tracking
- Immutable after construction (`healthy_ips` stored as `frozenset`)
- Copy-on-write via `updated_ips(updated_ips: List[AHealthyIp]) -> AHealthyRecord`
- Equality based only on subdomain (not health status)

**Benefits:**
- Thread-safe sharing without locks (immutable data)
- Clear semantics for health status changes
- Prevents accidental mutation bugs

### 3. Versioned Zone with Transactional Updates

**Location:** [indisoluble/a_healthy_dns/dns_server_zone_updater.py](../indisoluble/a_healthy_dns/dns_server_zone_updater.py)

**Purpose:** Thread-safe zone updates while serving queries

**Implementation:**
- Uses `dns.versioned.Zone` from dnspython
- **Writer pattern** (health checker thread):
  ```python
  with self._zone.writer() as txn:
      self._clear_zone(txn)
      self._add_records_to_zone(txn)
      self._sign_zone(txn)
  # Transaction commits automatically on context exit
  ```
- **Reader pattern** (DNS query handler):
  ```python
  with zone.reader() as txn:
      node = txn.get_node(relative_name)
      rdataset = node.get_rdataset(zone.rdclass, query_type)
  # Read lock released on context exit
  ```

**Thread Safety:**
- Writer acquires exclusive lock during zone reconstruction
- Readers acquire shared locks and see consistent zone snapshots
- Updates are atomic (all-or-nothing via transaction commit/rollback)

**Benefits:**
- No race conditions between DNS handler and health checker
- DNS queries never see partial zone updates
- Zone updates never block each other (sequential via single writer thread)

### 4. Generator Pattern for Dynamic Records

**Locations:**
- [indisoluble/a_healthy_dns/records/soa_record.py](../indisoluble/a_healthy_dns/records/soa_record.py)
- [indisoluble/a_healthy_dns/records/dnssec.py](../indisoluble/a_healthy_dns/records/dnssec.py)

**Purpose:** Generate records with time-varying fields without recreating state

**SOA Record Generator:**
```python
def iter_soa_record(max_interval: int, origin_name: dns.name.Name, 
                    primary_ns: str) -> Iterator[dns.rdataset.Rdataset]:
    serial = _iter_soa_serial()  # Infinite generator yields increasing timestamps
    while True:
        admin_info = " ".join([primary_ns, responsible, str(next(serial)), ...])
        yield dns.rdataset.from_text(...)
```
- SOA serial number is UNIX timestamp (32-bit wraparound safe)
- Each `next()` call produces new SOA with incremented serial
- Timing parameters (refresh, retry, expire) calculated from `max_interval`

**DNSSEC Signing Key Generator:**
```python
def iter_rrsig_key(max_interval: int, ext_key: ExtendedPrivateKey) 
                   -> Iterator[ExtendedRRSigKey]:
    while True:
        inception = datetime.now(utc)
        expiration = inception + delta
        resign = expiration - validity_buffer
        yield ExtendedRRSigKey(key=RRSigKey(...), resign=resign)
```
- Generates DNSSEC signature parameters with rolling expiration times
- `resign` time determines when next signature is needed
- Validity buffer ensures signatures don't expire between checks

**Benefits:**
- No mutable state for time-based values
- Infinite iterators avoid recreation overhead
- Clean separation of timing logic from zone management

### 5. Partial Application for Dependency Injection

**Location:** [indisoluble/a_healthy_dns/dns_server_zone_updater.py](../indisoluble/a_healthy_dns/dns_server_zone_updater.py#L112-L118)

**Purpose:** Inject dependencies without passing them through every call

**Implementation:**
```python
from functools import partial

# In __init__:
self._make_a_record = partial(make_a_record, max_interval)
self._can_create_connection = partial(can_create_connection, 
                                      timeout=float(connection_timeout))

# Later usage:
dataset = self._make_a_record(healthy_record)  # max_interval already bound
is_healthy = self._can_create_connection(ip, port)  # timeout already bound
```

**Benefits:**
- Configuration values bound once at initialization
- Call sites remain clean and focused on domain logic
- Easier to mock for testing (inject partial with test doubles)

### 6. Abort-on-Shutdown Pattern

**Location:** [indisoluble/a_healthy_dns/dns_server_zone_updater.py](../indisoluble/a_healthy_dns/dns_server_zone_updater.py#L192-L218)

**Purpose:** Graceful shutdown of long-running health check loops

**Implementation:**
```python
ShouldAbortOp = Callable[[], bool]

def _refresh_a_record(self, a_record: AHealthyRecord, 
                      should_abort: ShouldAbortOp) -> Optional[AHealthyRecord]:
    for health_ip in a_record.healthy_ips:
        if should_abort():
            logging.debug("Abort record check. Keep A record as it is")
            return None
        # Perform health check...
```

**Shutdown Flow:**
1. Main thread receives SIGTERM/SIGINT
2. Calls `zone_updater.stop()` which sets `_stop_event`
3. Background thread passes `lambda: self._stop_event.is_set()` as `should_abort`
4. Health check loop checks abort condition between each IP test
5. Returns early, allowing thread to join within timeout

**Benefits:**
- Responsive shutdown without killing threads
- Partial health check results are discarded (zone kept in last consistent state)
- Bounded shutdown time (timeout = connection_timeout + management delta)

## Data Flow

### DNS Query Flow

```
Client → UDP Socket → DnsServerUdpHandler.handle()
                      ├─ Parse query with dnspython
                      ├─ Extract question (name, type)
                      ├─ zone.reader() → read lock acquired
                      │  ├─ ZoneOrigins.relativize(query_name)
                      │  ├─ txn.get_node(relative_name)
                      │  └─ node.get_rdataset(rdclass, rdtype)
                      ├─ Build response (AA flag, answer section)
                      └─ Send response to client
```

**Thread:** Main thread (UDP server event loop)  
**Reads:** `server.zone` (versioned zone), `server.zone_origins`  
**Concurrency:** Multiple queries concurrent via reader locks

### Health Check and Zone Update Flow

```
Background Thread Loop (every min_interval seconds):
  DnsServerZoneUpdaterThreated._update_zone_loop()
  └─ DnsServerZoneUpdater.update(check_ips=True)
     ├─ _refresh_a_recs(should_abort)
     │  └─ For each AHealthyRecord:
     │     └─ _refresh_a_record(record, should_abort)
     │        └─ For each AHealthyIp:
     │           ├─ Check should_abort()
     │           ├─ can_create_connection(ip, port)
     │           └─ health_ip.updated_status(is_healthy)
     │        → Return updated AHealthyRecord
     │  → RefreshARecordsResult.CHANGES / NO_CHANGES / ABORTED
     │
     ├─ Check if zone sign near expiration
     ├─ If changes or sign needed:
     │  └─ _recreate_zone()
     │     └─ zone.writer() → write lock acquired
     │        ├─ _clear_zone(txn)
     │        ├─ _add_records_to_zone(txn)
     │        │  ├─ Add NS record
     │        │  ├─ Add SOA record (next from generator)
     │        │  └─ For each AHealthyRecord:
     │        │     └─ make_a_record(record) → only healthy IPs
     │        └─ _sign_zone(txn) if DNSSEC enabled
     │           └─ dns.dnssec.sign_zone(zone, txn, **key_params)
     │        → Transaction commits on context exit
     └─ Sleep until next interval
```

**Thread:** Background daemon thread  
**Writes:** `self._zone` (versioned zone)  
**Concurrency:** Exclusive writer lock during zone reconstruction

### Configuration Flow

```
main() → parse args
       → make_config(args)
          ├─ _make_zone_origins(args) → ZoneOrigins
          ├─ _make_a_records(args) → FrozenSet[AHealthyRecord]
          │  └─ _make_healthy_a_record() for each subdomain
          │     └─ AHealthyIp(ip, health_port, is_healthy=True)
          ├─ _make_name_servers(args) → FrozenSet[str]
          └─ _make_private_key(args) → Optional[ExtendedPrivateKey]
             ├─ _load_dnssec_private_key(path) → bytes
             └─ dns.dnssec.PrivateKey.from_pem(bytes, alg)
          → DnsServerConfig (immutable NamedTuple)
       
       → DnsServerZoneUpdaterThreated(min_interval, timeout, config)
          └─ DnsServerZoneUpdater(...)
             ├─ _calculate_max_interval() based on health check overhead
             ├─ Create NS, SOA, DNSSEC generators with max_interval
             └─ Initialize empty versioned zone
       
       → zone_updater.start()
          ├─ update(check_ips=False) → initial zone creation
          └─ Start background thread
       
       → socketserver.UDPServer(address, DnsServerUdpHandler)
          ├─ Attach server.zone = zone_updater.zone
          ├─ Attach server.zone_origins = config.zone_origins
          └─ serve_forever()
```

## Key Design Decisions

### Why Versioned Zones Instead of Locks?
- **Decision:** Use dnspython's `dns.versioned.Zone` with reader/writer transactions
- **Alternative considered:** Manual locking around zone dict/object
- **Rationale:**
  - Transactional semantics (atomic commit/rollback)
  - Built-in thread safety proven by dnspython
  - Zone snapshot consistency (readers see complete zones)
  - Less error-prone than manual lock management

### Why Thread-Based Instead of Async?
- **Decision:** Threading with `socketserver.UDPServer` and background thread
- **Alternative considered:** asyncio with async DNS library
- **Rationale:**
  - `socketserver` is stdlib battle-tested for simple UDP servers
  - Health checks (TCP socket operations) are blocking I/O anyway
  - Threading simpler for this concurrency model (one writer, many readers)
  - Performance sufficient for target scale (100+ QPS on modest hardware)

### Why Recreate Entire Zone Instead of Incremental Updates?
- **Decision:** Clear zone and rebuild all records on each health check cycle
- **Alternative considered:** Only update changed A records
- **Rationale:**
  - Simpler logic (no diff computation)
  - SOA serial must change on every update anyway
  - DNSSEC requires full zone resign (expensive operation)
  - Health check intervals (tens of seconds) make overhead negligible
  - Avoids bugs from partial state updates

### Why TCP Connectivity Instead of HTTP/HTTPS?
- **Decision:** Health checks via `socket.create_connection()`
- **Alternative considered:** HTTP GET requests, gRPC health checks
- **Rationale:**
  - TCP connectivity is universal (works for any TCP service)
  - Minimal overhead (faster than HTTP)
  - No dependencies on application protocol
  - Sufficient signal for DNS-level load balancing
  - Keeps project scope focused (per [docs/project-brief.md](project-brief.md))

### Why Immutable Configuration Instead of Hot-Reload?
- **Decision:** Configuration loaded once at startup; restart required for changes
- **Alternative considered:** File watching with hot-reload
- **Rationale:**
  - Simpler implementation (no config diff logic)
  - Easier to reason about (no mid-flight config changes)
  - DNS servers typically change config infrequently
  - Restart is acceptable for typical deployment patterns
  - Reduces risk of config validation failures during operation

### Why Return NXDOMAIN for All-Unhealthy Subdomains?
- **Decision:** When all IPs unhealthy, return NXDOMAIN (not empty answer)
- **Alternative considered:** Return SERVFAIL or empty answer section
- **Rationale:**
  - Fail-closed security posture (don't direct traffic to broken backends)
  - Clear signal to clients that service is unavailable
  - Consistent with DNS semantics (subdomain doesn't currently "exist")
  - Forces client failover/retry logic to other mechanisms

## Testing Strategy

### Unit Testing Focus
- **Configuration validation:** All input validators in `tools/` and config factory
- **Value objects:** Immutability contracts, equality semantics
- **Record factories:** TTL calculation, healthy IP filtering
- **Zone origins:** Relativization logic for hosted + alias zones

### Integration Testing Focus
- **dnspython transaction behavior** (see [tests/indisoluble/a_healthy_dns/test_dnspython_transaction.py](../tests/indisoluble/a_healthy_dns/test_dnspython_transaction.py))
- **Zone updater** with mocked connectivity checks
- **UDP handler** with mocked zones

### Not Tested (by design)
- **End-to-end DNS protocol** (would require running server, sending real queries)
- **Threading behavior under load** (difficult to test reliably)
- **DNSSEC signing correctness** (delegated to dnspython)

## Extension Points

If future requirements demand new capabilities:

### Adding New Record Types
1. Create factory in `records/` module (e.g., `mx_record.py`)
2. Add to zone in `DnsServerZoneUpdater._add_records_to_zone()`
3. Update `DnsServerConfig` to include new record configuration

### Adding Application-Layer Health Checks
1. Create new health check implementation in `tools/` (e.g., `can_http_get.py`)
2. Extend `AHealthyIp` to specify health check type
3. Update `DnsServerZoneUpdater._refresh_a_record()` to dispatch on type

### Adding Metrics/Monitoring Endpoint
1. Create separate HTTP server thread (do NOT share main DNS thread)
2. Export zone state, health check results, query counters
3. Consider adding Prometheus client library

### Adding Dynamic Configuration
1. Introduce config version number
2. Watch config file for changes
3. On change, validate new config and atomically swap
4. Requires careful handling of zone updater restart

---

**Last Updated:** March 7, 2026  
**Version:** 1.0 (Bootstrap)
