# System Patterns

**Last Updated**: 2026-02-26

## Architecture Overview

```
┌─────────────────┐
│  CLI Arguments  │
└────────┬────────┘
         │
         ↓
┌─────────────────────────┐
│  Config Factory         │  Validates & creates DnsServerConfig
│  dns_server_config_     │
│  factory.py             │
└────────┬────────────────┘
         │
         ├─────────────────────────────┐
         ↓                             ↓
┌─────────────────────────┐   ┌──────────────────────┐
│ Zone Updater (Threaded) │   │  UDP Handler         │
│ dns_server_zone_updater_│   │  dns_server_udp_     │
│ threated.py             │   │  handler.py          │
│                         │   │                      │
│ ┌─────────────────────┐ │   │  Responds to DNS     │
│ │ Zone Updater        │ │   │  queries with zone   │
│ │ dns_server_zone_    │ │   │  data                │
│ │ updater.py          │ │   │                      │
│ │                     │ │   └──────────────────────┘
│ │ • Health checks     │ │
│ │ • Zone recreation   │ │
│ │ • DNSSEC signing    │ │
│ └─────────────────────┘ │
└────────┬────────────────┘
         │
         ↓ (shares)
┌─────────────────────────┐
│  dns.versioned.Zone     │  Thread-safe zone storage
│  (dnspython library)    │
└─────────────────────────┘
```

## Core Patterns

### 1. Immutable Data Structures

**Context**: Need thread-safe data sharing between updater thread and request handler thread

**Pattern**: All domain objects use immutable structures
- `NamedTuple` for configuration objects
- `FrozenSet` for collections
- New instances created on updates (functional approach)

**Implementation**:
```python
class AHealthyIp:
    def updated_status(self, is_healthy: bool) -> "AHealthyIp":
        if is_healthy == self._is_healthy:
            return self  # No change, return same instance
        return AHealthyIp(...)  # Create new instance
```

**Examples**:
- [indisoluble/a_healthy_dns/records/a_healthy_ip.py:49-57](indisoluble/a_healthy_dns/records/a_healthy_ip.py#L49-L57)
- [indisoluble/a_healthy_dns/records/a_healthy_record.py:30-35](indisoluble/a_healthy_dns/records/a_healthy_record.py#L30-L35)
- [indisoluble/a_healthy_dns/dns_server_config_factory.py:18-32](indisoluble/a_healthy_dns/dns_server_config_factory.py#L18-L32)

**Benefits**: Thread-safety without locks, clear mutation points, easier testing

---

### 2. Factory Pattern for Record Creation

**Context**: DNS records require complex validation and TTL calculation

**Pattern**: Dedicated factory functions for each record type
- `make_a_record()` - Filters healthy IPs, calculates TTL
- `make_ns_record()` - Creates NS records from name server list
- `iter_soa_record()` - Generator for SOA with auto-incrementing serial
- `iter_rrsig_key()` - Generator for DNSSEC signing keys with timing

**Implementation**:
```python
def make_a_record(max_interval: int, healthy_record: AHealthyRecord) -> Optional[dns.rdataset.Rdataset]:
    ips = [ip.ip for ip in healthy_record.healthy_ips if ip.is_healthy]
    if not ips:
        return None  # No record if no healthy IPs
    ttl = calculate_a_ttl(max_interval)
    return dns.rdataset.from_text(dns.rdataclass.IN, dns.rdatatype.A, ttl, *ips)
```

**Examples**:
- [indisoluble/a_healthy_dns/records/a_record.py:21-35](indisoluble/a_healthy_dns/records/a_record.py#L21-L35)
- [indisoluble/a_healthy_dns/records/soa_record.py:46-77](indisoluble/a_healthy_dns/records/soa_record.py#L46-L77)
- [indisoluble/a_healthy_dns/records/dnssec.py:41-67](indisoluble/a_healthy_dns/records/dnssec.py#L41-L67)

**Benefits**: Centralized validation, consistent TTL calculation, testability

---

### 3. Transaction-Based Zone Updates

**Context**: Zone must remain consistent even if health checks are interrupted

**Pattern**: Use dnspython's `Zone.writer()` context manager
- All changes in transaction
- Atomic commit on context exit
- Rollback on exception
- Reader/writer isolation

**Implementation**:
```python
def _recreate_zone(self):
    with self._zone.writer() as txn:
        self._clear_zone(txn)
        self._add_records_to_zone(txn)
        self._sign_zone(txn)
    # Zone updated atomically
```

**Examples**:
- [indisoluble/a_healthy_dns/dns_server_zone_updater.py:175-179](indisoluble/a_healthy_dns/dns_server_zone_updater.py#L175-L179)
- [indisoluble/a_healthy_dns/dns_server_udp_handler.py:37-66](indisoluble/a_healthy_dns/dns_server_udp_handler.py#L37-L66)

**Benefits**: Consistency, no partial updates visible to queries, exception safety

---

### 4. Threaded Background Processing

**Context**: Health checks are slow (network I/O), DNS queries must remain fast

**Pattern**: Separate thread for zone updates with abort mechanism
- Main thread: UDP server handles queries
- Background thread: Continuous health check loop
- Shared: `dns.versioned.Zone` (thread-safe)
- Graceful shutdown via `threading.Event`

**Implementation**:
```python
class DnsServerZoneUpdaterThreated:
    def start(self):
        self._updater.update(check_ips=False)  # Initial zone
        self._stop_event.clear()
        self._updater_thread = threading.Thread(target=self._update_zone_loop, daemon=True)
        self._updater_thread.start()
    
    def _update_zone_loop(self):
        while not self._stop_event.is_set():
            self._updater.update(should_abort=lambda: self._stop_event.is_set())
            # Sleep with interrupt check
```

**Examples**:
- [indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py:40-68](indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py#L40-L68)

**Benefits**: Non-blocking queries, graceful shutdown, abort capability

---

### 5. Iterator Pattern for Time-Based Records

**Context**: SOA serial and DNSSEC signatures require continuous updates

**Pattern**: Generator functions yield next record on demand
- `iter_soa_record()` - Yields SOA with incrementing serial
- `iter_rrsig_key()` - Yields DNSSEC keys with calculated inception/expiration

**Implementation**:
```python
def iter_soa_record(max_interval: int, origin_name: dns.name.Name, primary_ns: str):
    serial = _iter_soa_serial()  # Nested generator
    while True:
        admin_info = " ".join([primary_ns, responsible, str(next(serial)), ...])
        yield dns.rdataset.from_text(...)
```

**Examples**:
- [indisoluble/a_healthy_dns/records/soa_record.py:29-42](indisoluble/a_healthy_dns/records/soa_record.py#L29-L42)
- [indisoluble/a_healthy_dns/records/dnssec.py:41-67](indisoluble/a_healthy_dns/records/dnssec.py#L41-L67)

**Benefits**: Infinite sequences, stateful iteration, lazy evaluation

---

### 6. Validation at Boundaries

**Context**: Invalid input must be rejected before creating domain objects

**Pattern**: Validation functions return `(success: bool, error: str)` tuples
- Called before object construction
- Detailed error messages for logging
- Type coercion where appropriate (e.g., IP normalization)

**Implementation**:
```python
def is_valid_ip(ip: Any) -> Tuple[bool, str]:
    if not isinstance(ip, str):
        return False, f"must be string, got {type(ip).__name__}"
    try:
        ipaddress.ip_address(ip)
        return True, ""
    except ValueError as ex:
        return False, str(ex)

# Usage in constructor
success, error = is_valid_ip(ip)
if not success:
    raise ValueError(f"Invalid IP address: {error}")
```

**Examples**:
- [indisoluble/a_healthy_dns/tools/is_valid_ip.py](indisoluble/a_healthy_dns/tools/is_valid_ip.py)
- [indisoluble/a_healthy_dns/tools/is_valid_port.py](indisoluble/a_healthy_dns/tools/is_valid_port.py)
- [indisoluble/a_healthy_dns/tools/is_valid_subdomain.py](indisoluble/a_healthy_dns/tools/is_valid_subdomain.py)

**Benefits**: Clear error messages, fail-fast, consistent validation

---

### 7. Multi-Origin Zone Support

**Context**: Support alias domains resolving to same records as primary zone

**Pattern**: `ZoneOrigins` class manages primary + aliases
- Stores sorted list (most specific first)
- `relativize()` method finds matching origin
- Used by UDP handler to validate query domains

**Implementation**:
```python
class ZoneOrigins:
    def __init__(self, primary: Any, aliases: List[Any]):
        self._primary = _to_abs_name(primary)
        self._origins = sorted(
            {self._primary, *(_to_abs_name(alias) for alias in aliases)},
            key=lambda zone: (-len(zone), zone.to_text()),  # Most specific first
        )
    
    def relativize(self, name: dns.name.Name) -> Optional[dns.name.Name]:
        zone = next((origin for origin in self._origins if name.is_subdomain(origin)), None)
        return name.relativize(zone) if zone else None
```

**Examples**:
- [indisoluble/a_healthy_dns/records/zone_origins.py:19-45](indisoluble/a_healthy_dns/records/zone_origins.py#L19-L45)

**Benefits**: Single zone serves multiple domains, deterministic matching

---

## Data Flow Patterns

### Query Resolution Flow
```
1. UDP packet received → DnsServerUdpHandler.handle()
2. Parse DNS query → dns.message.from_wire()
3. Check question section exists
4. Relativize query name via zone_origins
5. Acquire zone reader → zone.reader()
6. Lookup node in zone
7. Get rdataset for query type
8. Build response with AA flag
9. Send response → sock.sendto()
```

### Zone Update Flow
```
1. Background thread wakes up
2. Check abort flag (shutdown requested?)
3. For each A record:
   a. For each IP in record:
      - Check abort flag
      - Test TCP connectivity
      - Update IP health status
   b. Compare with previous IPs
   c. Update record if changed
4. Check if any changes OR DNSSEC expiring
5. If update needed:
   a. Acquire zone writer
   b. Clear all nodes
   c. Add NS record
   d. Add SOA record (with new serial)
   e. Add A records (healthy IPs only)
   f. Sign zone (if DNSSEC enabled)
   g. Commit transaction
6. Sleep until next interval
```

### Health Check Flow
```
1. Extract IP + health_port from AHealthyIp
2. Create TCP connection with timeout
3. Success → Mark healthy
4. Exception → Mark unhealthy
5. Return new AHealthyIp instance (immutable update)
```

## Error Handling Patterns

### Fail-Fast Validation
- Invalid configuration → Log error, return None, main() exits
- Invalid query → Log warning, return FORMERR/NXDOMAIN
- Connection test failure → Log debug, mark IP unhealthy

### Graceful Degradation
- No healthy IPs → Skip A record (not an error)
- Health check timeout → Mark unhealthy, continue
- Zone update interrupted → Keep previous zone intact

### No Defensive Programming
- Don't catch exceptions without handling them
- Don't return default values on validation failure
- Don't silently ignore errors

## Testing Patterns

See [testing-patterns.md](./testing-patterns.md) for detailed testing conventions.
