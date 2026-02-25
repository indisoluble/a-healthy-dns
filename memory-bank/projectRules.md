# Project Rules

## Code Standards

### General
- **Shebang**: Every `.py` file starts with `#!/usr/bin/env python3`.
- **Docstrings**: Module-level docstrings on every file (2-3 line summary). No class/method docstrings beyond one-liners.
- **Type hints**: Used on function signatures (`-> Optional[T]`, `FrozenSet[X]`, etc.) but not on local variables.
- **Logging over exceptions**: Validation failures log an error and return `None` rather than raising exceptions. Exceptions are reserved for programming errors (`ValueError` in constructors for invariant violations).

### Naming Conventions
- **Files**: `snake_case.py`, prefixed by role (`test_`, `a_record`, `dns_server_`, etc.).
- **Classes**: `PascalCase` — `AHealthyIp`, `DnsServerUdpHandler`, `ZoneOrigins`.
- **Functions**: `snake_case` — `make_config`, `can_create_connection`, `is_valid_ip`.
- **Private functions**: `_` prefix — `_make_zone_origins`, `_clear_zone`, `_refresh_a_record`.
- **Constants**: `_UPPER_SNAKE` for module-private, `UPPER_SNAKE` for public — `_VAL_PORT`, `ARG_HOSTED_ZONE`, `DELTA_PER_RECORD_MANAGEMENT`.
- **CLI arg names**: Kebab-case (`--hosted-zone`, `--test-timeout`), mapped to snake_case dest (`zone`, `timeout`).

### Architecture Rules
- **Immutable value objects**: Domain model objects (`AHealthyIp`, `AHealthyRecord`) return new instances instead of mutating state.
- **`FrozenSet` for collections**: Configuration data uses `FrozenSet` to prevent mutation.
- **`NamedTuple` for DTOs**: `DnsServerConfig`, `ExtendedPrivateKey`, `RRSigKey`, `RRSigLifetime`, `ExtendedRRSigKey`.
- **`Optional` return = failure**: Factory functions return `Optional[T]`; `None` means validation/construction failed. Callers must check.
- **No global mutable state**: All state is held in instances or passed as arguments.
- **Generators for evolving state**: SOA serial numbers and RRSIG keys use infinite generators (`yield`) to encapsulate sequential state.

### Validation Pattern
- Validation tools return `Tuple[bool, str]` — `(True, "")` on success, `(False, "reason")` on failure.
- Used in: `is_valid_ip`, `is_valid_port`, `is_valid_subdomain`.
- Constructor calls validation and raises `ValueError` with the error message.

### Error Handling
- **No bare `except`** — always `except Exception as ex` or specific types.
- **Log then return None** for expected failures (config parsing, file I/O).
- **Raise ValueError** for programming-level invariant violations (negative interval, invalid IP in constructor).

## Testing Rules

### Framework & Style
- **pytest** only — no `unittest.TestCase` subclasses.
- All tests are **module-level functions**, no test classes.
- **No `conftest.py`** — fixtures are local to each test file.

### Patterns
- **`@pytest.fixture`**: For shared setup (configs, mock objects, DNS structures).
- **`@pytest.mark.parametrize`**: Extensively for input validation boundary testing (5-15+ cases).
- **`@patch`**: For external dependencies (socket, time, filesystem).
- **`Mock(spec=...)`**: Always use `spec=` for type safety on mocks.
- **`pytest.raises(ValueError, match="...")`**: For constructor validation testing.
- **Direct `assert`** statements — no `assertEqual` style.

### Structure
- Mirror source tree exactly: `tests/indisoluble/a_healthy_dns/` ↔ `indisoluble/a_healthy_dns/`.
- Test file = `test_` + source file name.
- Function naming: `test_<what>` or `test_<method>_<scenario>`.

### Coverage Expectations
- Every public function and class has tests.
- Validation functions have parametrized invalid-input tests.
- Constructor validation (ValueError paths) are tested.
- Mock-based tests for external I/O (socket, file, time).

## File Organization

### Package Structure
```
indisoluble/
  a_healthy_dns/
    main.py                          # Entry point, CLI, server lifecycle
    dns_server_config_factory.py     # Configuration validation & construction
    dns_server_udp_handler.py        # DNS query handling
    dns_server_zone_updater.py       # Zone update logic + health checks
    dns_server_zone_updater_threated.py  # Threaded wrapper for zone updater
    records/                         # DNS record types and timing
      a_healthy_ip.py                # IP + health status value object
      a_healthy_record.py            # Subdomain + IPs value object
      a_record.py                    # A record factory (healthy IPs only)
      dnssec.py                      # RRSIG key generation
      ns_record.py                   # NS record factory
      soa_record.py                  # SOA record generator
      time.py                        # TTL/timing calculations
      zone_origins.py                # Primary + alias zone management
    tools/                           # Pure utility functions
      can_create_connection.py       # TCP health check
      is_valid_ip.py                 # IPv4 validation
      is_valid_port.py               # Port validation
      is_valid_subdomain.py          # Subdomain name validation
      normalize_ip.py                # IPv4 normalization (strip leading zeros)
      uint32_current_time.py         # 32-bit timestamp for SOA serial
```

### Rules for New Files
- **`tools/`**: Pure functions, no classes, no state. Single responsibility.
- **`records/`**: DNS record factories/value objects. May depend on `tools/`.
- **Root `a_healthy_dns/`**: Server infrastructure. May depend on `records/` and `tools/`.
- No circular dependencies between subpackages.
