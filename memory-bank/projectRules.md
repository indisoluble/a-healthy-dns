# Project Rules

**Last Updated**: 2026-02-26

## Code Organization

### Module Structure
```
indisoluble/a_healthy_dns/
├── main.py                           # Entry point, CLI, server lifecycle
├── dns_server_config_factory.py      # Configuration validation and creation
├── dns_server_udp_handler.py         # DNS query handling
├── dns_server_zone_updater.py        # Core zone update logic
├── dns_server_zone_updater_threated.py  # Threaded wrapper
├── records/                          # DNS record types and data structures
│   ├── a_healthy_ip.py               # IP with health status
│   ├── a_healthy_record.py           # A record with multiple IPs
│   ├── a_record.py                   # A record factory
│   ├── dnssec.py                     # DNSSEC key management
│   ├── ns_record.py                  # NS record factory
│   ├── soa_record.py                 # SOA record factory
│   ├── time.py                       # TTL calculation utilities
│   └── zone_origins.py               # Multi-zone name handling
└── tools/                            # Validation and utility functions
    ├── can_create_connection.py      # TCP health check
    ├── is_valid_ip.py                # IP validation
    ├── is_valid_port.py              # Port validation
    ├── is_valid_subdomain.py         # Domain validation
    ├── normalize_ip.py               # IP normalization
    └── uint32_current_time.py        # SOA serial generation
```

**Convention**: 
- One class/factory per file
- Tools are pure functions (no side effects except I/O)
- Records are immutable data structures

---

## Naming Conventions

### Files
- **Snake case**: `dns_server_zone_updater.py`
- **Descriptive**: Name indicates purpose (`make_config`, not `factory`)
- **No abbreviations**: `dns_server` not `dns_srv` (except DNS which is standard)

### Classes
- **PascalCase**: `DnsServerZoneUpdater`
- **Noun phrases**: Describe what it is, not what it does
- **No prefix**: Just `ZoneUpdater`, not `CDnsZoneUpdater`

### Functions
- **Snake case**: `can_create_connection()`
- **Verb phrases**: `make_a_record()`, `calculate_soa_ttl()`
- **Boolean returns**: `is_*` or `can_*` prefix

### Variables
- **Snake case**: `zone_origins`, `healthy_ips`
- **Descriptive**: `connection_timeout` not `timeout` (be specific)
- **No single letters**: Except `ex` for exceptions, `i/j/k` in short loops

### Constants
- **SCREAMING_SNAKE_CASE**: `DELTA_PER_RECORD_MANAGEMENT`
- **Module-level private**: `_VAL_PORT`, `_ARG_LOG_LEVEL`
- **Public constants**: Rare, prefer configuration

---

## Type Hints

### Always Use Type Hints
```python
def make_a_record(max_interval: int, healthy_record: AHealthyRecord) -> Optional[dns.rdataset.Rdataset]:
    ...
```

### Complex Types
```python
from typing import Any, Dict, FrozenSet, Iterator, List, NamedTuple, Optional, Tuple

# Use specific types, avoid Any when possible
def _make_zone_origins(args: Dict[str, Any]) -> Optional[ZoneOrigins]:
    ...
```

### NamedTuple for Immutable Structures
```python
class DnsServerConfig(NamedTuple):
    """DNS server configuration containing zone data and security settings."""
    zone_origins: ZoneOrigins
    name_servers: FrozenSet[str]
    a_records: FrozenSet[AHealthyRecord]
    ext_private_key: Optional[ExtendedPrivateKey]
```

**Convention**: NamedTuple preferred over dataclass for immutability

---

## Immutability Rules

### Domain Objects Are Immutable
```python
class AHealthyIp:
    def updated_status(self, is_healthy: bool) -> "AHealthyIp":
        if is_healthy == self._is_healthy:
            return self  # No change, return same instance
        return AHealthyIp(ip=self.ip, health_port=self.health_port, is_healthy=is_healthy)
```

**Pattern**: Return `self` if unchanged, new instance if changed

### Use FrozenSet for Collections
```python
self._healthy_ips = frozenset(healthy_ips)  # Not list
```

**Rationale**: Prevents accidental mutation, enables hashing

### No Setters
```python
# ❌ Wrong
def set_healthy(self, is_healthy: bool):
    self._is_healthy = is_healthy

# ✅ Correct
def updated_status(self, is_healthy: bool) -> "AHealthyIp":
    return AHealthyIp(...)
```

---

## Validation Patterns

### Return Tuples, Not Exceptions
```python
def is_valid_ip(ip: Any) -> Tuple[bool, str]:
    """Validate IP address format."""
    if not isinstance(ip, str):
        return False, f"must be string, got {type(ip).__name__}"
    try:
        ipaddress.ip_address(ip)
        return True, ""
    except ValueError as ex:
        return False, str(ex)
```

**Usage**:
```python
success, error = is_valid_ip(ip)
if not success:
    raise ValueError(f"Invalid IP address: {error}")
```

**Rationale**: Caller decides exception vs logging

### Validate at Boundaries
- ✅ Validate in `__init__()` before assignment
- ✅ Validate in factory functions before object creation
- ❌ Don't validate in internal methods (assume valid)

### Detailed Error Messages
```python
logging.error("Zone resolution for '%s' must include '%s' key", subdomain, ARG_SUBDOMAIN_IP_LIST)
```

**Convention**: Include context (which subdomain, which key)

---

## Logging Conventions

### Log Levels
- **DEBUG**: Health check results, zone updates, record additions
- **INFO**: Server start/stop, zone updater start/stop
- **WARNING**: Malformed queries, domain not found, parse errors
- **ERROR**: Configuration validation failures, critical issues

### Log Message Format
```python
logging.debug("Created A record with ttl: %d, and IPs: %s", ttl, ips)
logging.warning("Received query for domain not in hosted or alias zones: %s", query_name)
logging.error("Failed to parse zone resolutions: %s", ex)
```

**Convention**: 
- Use `%s` formatting (not f-strings) for lazy evaluation
- Include relevant variables
- Past tense for completed actions ("Created", "Added")

### Module-Level Loggers
```python
import logging

# No explicit logger creation - use root logger
logging.debug("Message")
```

**Convention**: Use root logger (configured in main), not `logging.getLogger(__name__)`

---

## Error Handling

### Fail-Fast Configuration
```python
def make_config(args: Dict[str, Any]) -> Optional[DnsServerConfig]:
    zone_origins = _make_zone_origins(args)
    if not zone_origins:
        return None  # Error already logged

    a_records = _make_a_records(zone_origins.primary, args)
    if a_records is None:
        return None
    ...
```

**Pattern**: Return `None` on validation failure, log error immediately

### Graceful Health Check Failures
```python
def can_create_connection(ip: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((ip, port), timeout):
            logging.debug("TCP connectivity test to '%s:%d' successful", ip, port)
            return True
    except Exception as ex:
        logging.debug("TCP connectivity test to '%s:%d' failed: %s", ip, port, ex)
        return False
```

**Pattern**: Catch all exceptions, log at DEBUG level, return boolean

### No Silent Failures
```python
# ❌ Wrong
try:
    result = some_operation()
except Exception:
    pass  # Silent failure

# ✅ Correct
try:
    result = some_operation()
except Exception as ex:
    logging.error("Operation failed: %s", ex)
    raise  # Or handle appropriately
```

---

## Function Organization

### Private vs Public
- **Private**: Prefix with `_` (e.g., `_clear_zone`, `_make_a_record`)
- **Public**: No prefix (e.g., `update`, `handle`)

**Convention**: Default to private unless externally called

### Function Length
- **Target**: <50 lines per function
- **Maximum**: 100 lines (rare exceptions)
- **Refactor**: Extract helpers when exceeding

### Single Responsibility
```python
# ✅ Good - Each function has one purpose
def _refresh_a_record(self, a_record, should_abort):
    # Only checks one record
    ...

def _refresh_a_recs(self, should_abort):
    # Orchestrates checking all records
    ...

def _recreate_zone_after_refresh(self, should_abort):
    # Decides whether to update zone
    ...
```

---

## Testing Conventions

### File Structure
Mirror source tree:
```
tests/indisoluble/a_healthy_dns/
├── test_main.py
├── test_dns_server_config_factory.py
├── records/
│   ├── test_a_healthy_ip.py
│   ├── test_a_record.py
│   ...
└── tools/
    ├── test_can_create_connection.py
    ...
```

### Test Function Naming
```python
def test_make_a_record_with_healthy_ips():
    ...

def test_make_a_record_with_no_healthy_ips():
    ...

def test_update_response_domain_not_found():
    ...
```

**Pattern**: `test_<function_name>_<scenario>`

### Parameterized Tests
```python
@pytest.mark.parametrize(
    "invalid_subdomain",
    [123, 45.67, None, "invalid..com", "-invalid.com"]
)
def test_valid_subdomain_with_invalid_types(invalid_subdomain):
    success, _ = is_valid_subdomain(invalid_subdomain)
    assert not success
```

### Fixtures Over Setup/Teardown
```python
@pytest.fixture
def args():
    return {
        ARG_HOSTED_ZONE: "example.com",
        ARG_ALIAS_ZONES: "[]",
        ...
    }

def test_make_config_success(args):
    config = make_config(args)
    assert config is not None
```

See [testing-patterns.md](./testing-patterns.md) for comprehensive testing guides.

---

## Documentation

### Module Docstrings
```python
#!/usr/bin/env python3

"""DNS zone updater with health checking capabilities.

Manages DNS zone updates based on health checks of configured IP addresses,
handles DNSSEC signing, and maintains zone freshness with configurable intervals.
"""
```

**Required**: Every module (except `__init__.py`)

### Class Docstrings
```python
class DnsServerZoneUpdater:
    """DNS zone updater that performs health checks and updates zones accordingly."""
```

**Format**: Single line unless complexity requires more

### Function Docstrings
```python
def make_a_record(max_interval: int, healthy_record: AHealthyRecord) -> Optional[dns.rdataset.Rdataset]:
    """Create DNS A record from healthy record containing only healthy IPs."""
```

**Convention**: 
- Public functions: Required
- Private functions: Optional (unless complex)
- One-line summary sufficient for most cases

### Property Docstrings
```python
@property
def zone(self) -> dns.versioned.Zone:
    """Get the current DNS zone."""
    return self._zone
```

**Required**: All public properties

---

## Import Organization

### Order
1. Standard library (alphabetical)
2. Blank line
3. Third-party (alphabetical)
4. Blank line
5. Project imports (alphabetical)

**Example**:
```python
import datetime
import logging

import dns.dnssec
import dns.name

from indisoluble.a_healthy_dns.dns_server_config_factory import DnsServerConfig
from indisoluble.a_healthy_dns.records.a_healthy_record import AHealthyRecord
```

### Import Style
```python
# ✅ Preferred - Explicit imports
from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp

# ⚠️ Avoid - Star imports
from indisoluble.a_healthy_dns.records import *

# ✅ OK - Module import for many items
import dns.dnssec
```

---

## Constants and Configuration

### Module-Level Constants
```python
# Private (internal use)
_ARG_LOG_LEVEL = "log_level"
_VAL_PORT = 53053

# Public (exported)
ARG_HOSTED_ZONE = "zone"
DELTA_PER_RECORD_MANAGEMENT = 1
```

**Convention**: 
- Private constants: Leading underscore
- Public constants: No prefix, rare use

### Magic Numbers
```python
# ❌ Wrong
if timeout > 0 and timeout < 300:
    ...

# ✅ Correct
MAX_TIMEOUT_SECONDS = 300
if 0 < timeout < MAX_TIMEOUT_SECONDS:
    ...
```

---

## Thread Safety

### Shared Mutable State
```python
# ✅ Thread-safe
self._zone = dns.versioned.Zone(...)  # dnspython handles locking

# ❌ Not thread-safe without protection
self._shared_list = []  # Would need lock
```

**Rule**: Only share `dns.versioned.Zone` between threads, all other data is immutable

### Thread Communication
```python
# ✅ Correct - Event for signaling
self._stop_event = threading.Event()
...
should_abort=lambda: self._stop_event.is_set()
```

**Pattern**: Use `threading.Event` for shutdown signaling

---

## Performance Considerations

### Avoid Premature Optimization
- ✅ Clarity over performance unless profiling shows bottleneck
- ✅ Immutability despite allocation cost
- ⚠️ Profile before optimizing

### Known Hot Paths
- Health check loop: Scales with IPs × timeout
- DNS query handling: Single-threaded (acceptable for authoritative)
- Zone signing: DNSSEC signing is expensive (< 1s for typical zones)

**Rule**: Don't optimize without measurement
