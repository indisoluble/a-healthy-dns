# Project Rules and Development Conventions

## Language and Runtime

### Python Version
- **Required:** Python 3.10 or higher
- **Rationale:** Uses modern type hints and language features (structural pattern matching available, though not currently used)

### Dependencies
- **Core dependencies** (from [setup.py](../setup.py)):
  - `dnspython >= 2.8.0, < 3.0.0` — DNS protocol handling and zone management
  - `cryptography >= 46.0.5, < 47.0.0` — DNSSEC cryptographic operations
- **Development dependencies:**
  - `pytest` — Test framework
  - `pytest-cov` — Coverage measurement

### Dependency Management
- Dependencies declared in `setup.py` with version ranges
- Use `pip install .` for normal installation
- Use `pip install -e .` for development (editable mode)

## Python Conventions

### Module Structure
All modules must include:
1. **Shebang line:** `#!/usr/bin/env python3`
2. **Module docstring:** Triple-quoted docstring describing module purpose
3. **Imports:** Grouped in standard order (stdlib, third-party, local)
4. **Type hints:** All function signatures must include type hints

**Example:**
```python
#!/usr/bin/env python3

"""Brief one-line module description.

Optional extended description explaining module purpose,
key responsibilities, and usage patterns.
"""

import logging
import socket

import dns.name

from typing import Optional

from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp
```

### Type Hints
- **Mandatory** for all function/method signatures
- **Use `Optional[T]`** for nullable types (not `T | None` even though Python 3.10+ supports it)
- **Use `FrozenSet[T]`** for immutable sets
- **Use `NamedTuple`** for immutable data structures (not `dataclass` with `frozen=True`)
- **Import from `typing`:** `from typing import Any, Dict, FrozenSet, NamedTuple, Optional`

**Examples:**
```python
def make_config(args: Dict[str, Any]) -> Optional[DnsServerConfig]:
    """Create configuration from arguments."""
    
def _make_a_records(args: Dict[str, Any]) -> Optional[FrozenSet[AHealthyRecord]]:
    """Parse and validate A records from arguments."""
    
class DnsServerConfig(NamedTuple):
    """Immutable DNS server configuration."""
    zone_origins: ZoneOrigins
    name_servers: FrozenSet[str]
    a_records: FrozenSet[AHealthyRecord]
    ext_private_key: Optional[ExtendedPrivateKey]
```

### Naming Conventions
- **Modules:** `snake_case` (e.g., `dns_server_zone_updater.py`)
- **Classes:** `PascalCase` (e.g., `DnsServerZoneUpdater`, `AHealthyRecord`)
- **Functions/methods:** `snake_case` (e.g., `make_config`, `can_create_connection`)
- **Private functions/methods:** Leading underscore `_snake_case` (e.g., `_make_zone_origins`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `DELTA_PER_RECORD_MANAGEMENT`)
- **Private module constants:** Leading underscore `_UPPER_SNAKE_CASE` (e.g., `_DELTA_PER_RECORD_SIGN`)

### Docstrings
- **All public modules, classes, and functions** must have docstrings
- **Format:** Brief one-line summary; optional extended description
- **No parameter/return documentation** in docstrings (type hints convey that information)

**Example:**
```python
def can_create_connection(ip: str, port: int, timeout: float) -> bool:
    """Test TCP connectivity to an IP address and port with timeout."""
    # Implementation...
```

### Error Handling
- **Fail fast at startup** — Validate all configuration; return `None` from factory on error
- **Use `ValueError`** for validation failures in constructors
- **Log errors** before returning `None` or raising exceptions
- **Use `logging` module** — Never use `print()` statements

### Immutability Patterns
- **Prefer immutable data structures:** Use `NamedTuple`, `frozenset`, and immutable properties
- **Copy-on-write for updates:** Return new instances rather than mutating existing ones

**Example:**
```python
class AHealthyIp:
    def updated_status(self, is_healthy: bool) -> "AHealthyIp":
        """Return new instance with updated health status if changed."""
        if is_healthy == self._is_healthy:
            return self
        return AHealthyIp(ip=self.ip, health_port=self.health_port, is_healthy=is_healthy)
```

### Dependency Injection
- **Constructor injection** for external dependencies (network, time, file I/O)
- **Use `functools.partial`** to bind configuration at composition root

**Example:**
```python
from functools import partial

self._can_create_connection = partial(can_create_connection, timeout=float(connection_timeout))
# Later: self._can_create_connection(ip, port)  # timeout already bound
```

## Testing

### Test Framework
- **pytest** as the test runner
- **pytest-cov** for coverage measurement

### Test Structure
- **Location:** Mirror source structure under `tests/` directory
  - Source: `indisoluble/a_healthy_dns/dns_server_config_factory.py`
  - Tests: `tests/indisoluble/a_healthy_dns/test_dns_server_config_factory.py`
- **Naming:** Test files prefixed with `test_`, test functions prefixed with `test_`
- **Fixtures:** Use `@pytest.fixture` for reusable test setup
- **Parametrization:** Use `@pytest.mark.parametrize` for testing multiple inputs

**Example:**
```python
#!/usr/bin/env python3

import pytest
from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp

@pytest.fixture
def valid_ip():
    return "192.168.1.1"

def test_valid_initialization():
    ip = AHealthyIp("192.168.1.1", 8080, True)
    assert ip.ip == "192.168.1.1"
    assert ip.health_port == 8080

@pytest.mark.parametrize(
    "invalid_ip",
    ["256.0.0.1", "192.168.1", "192.168.1.a"],
)
def test_invalid_ip(invalid_ip):
    with pytest.raises(ValueError):
        AHealthyIp(invalid_ip, 8080, True)
```

### Coverage Requirements
- **Configuration:** `.coveragerc` in repository root
- **Source coverage:** `indisoluble.a_healthy_dns` package required
- **Exclusions:** Tests, setup.py, `__repr__`, `__main__`, NotImplementedError
- **Target:** Maintain high coverage; CI reports to Codecov

### Test Categories
- **Unit tests:** Test individual functions/classes in isolation
- **Integration tests:** Test component interactions (e.g., dnspython transaction behavior)
- **No end-to-end tests:** Server integration testing not required

### QA Commands

#### Run All Tests
```bash
# From repository root with venv activated
pytest
```

#### Run Tests with Coverage
```bash
pytest --cov=indisoluble.a_healthy_dns --cov-report=term --cov-report=xml
```

#### Run Specific Test File
```bash
pytest tests/indisoluble/a_healthy_dns/test_dns_server_config_factory.py
```

#### Run Specific Test Function
```bash
pytest tests/indisoluble/a_healthy_dns/test_dns_server_config_factory.py::test_make_config_success
```

#### Run Tests Matching Pattern
```bash
pytest -k "test_invalid"
```

#### Run Tests with Verbose Output
```bash
pytest -v
```

#### Generate HTML Coverage Report
```bash
pytest --cov=indisoluble.a_healthy_dns --cov-report=html
# Open coverage_html_report/index.html
```

## CI/CD Workflow

### GitHub Actions Workflows

#### Test Python Code ([.github/workflows/test-py-code.yml](../.github/workflows/test-py-code.yml))
- **Trigger:** Push to `master`, pull requests to `master`
- **Actions:**
  1. Set up Python 3.10
  2. Install dependencies (`pip install .`)
  3. Install pytest and pytest-cov
  4. Run tests with coverage
  5. Upload coverage to Codecov

#### Validate Tests ([.github/workflows/validate-tests.yml](../.github/workflows/validate-tests.yml))
- **Trigger:** After completion of test workflows
- **Actions:** Validates that all required workflows (Docker, Python, Version) passed

#### Security Scan ([.github/workflows/security-scan.yml](../.github/workflows/security-scan.yml))
- **Trigger:** Push to `master`
- **Actions:**
  1. Build Docker image
  2. Run Trivy vulnerability scanner
  3. Upload results to GitHub Security tab

#### Other Workflows
- **Test Docker:** Validates Docker image builds and runs
- **Test Version:** Validates version consistency
- **Release Version:** Creates GitHub releases
- **Release Docker:** Publishes to Docker Hub

### Local Development Workflow

#### Initial Setup
```bash
# Clone repository
git clone https://github.com/indisoluble/a-healthy-dns.git
cd a-healthy-dns

# Create and activate virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or: venv\Scripts\activate  # On Windows

# Install package in development mode
pip install -e .

# Install test dependencies
pip install pytest pytest-cov
```

#### Before Committing
```bash
# Run all tests
pytest

# Check coverage
pytest --cov=indisoluble.a_healthy_dns --cov-report=term

# Run the server locally (test configuration)
a-healthy-dns \
    --hosted-zone example.local \
    --zone-resolutions '{"www":{"ips":["127.0.0.1"],"health_port":8080}}' \
    --ns '["ns1.example.local"]' \
    --port 53053
```

#### Code Review Checklist
- [ ] All tests pass (`pytest`)
- [ ] Coverage maintained or improved
- [ ] Type hints on all new functions
- [ ] Docstrings on public APIs
- [ ] No print statements (use `logging`)
- [ ] Immutability patterns followed
- [ ] Configuration validated at startup
- [ ] Error cases tested

## Code Quality Standards

### Validation
- **All inputs validated** at the earliest point (usually factory methods)
- **Return `None` from factories** on validation failure (with logged error)
- **Raise `ValueError`** from constructors on invalid input

**Example:**
```python
def make_config(args: Dict[str, Any]) -> Optional[DnsServerConfig]:
    """Create configuration, returning None if validation fails."""
    zone_origins = _make_zone_origins(args)
    if not zone_origins:
        return None  # Error already logged
    # Continue validation...

class AHealthyIp:
    def __init__(self, ip: Any, health_port: Any, is_healthy: bool):
        """Initialize with validation."""
        success, error = is_valid_ip(ip)
        if not success:
            raise ValueError(f"Invalid IP address: {error}")
        # Continue initialization...
```

### Logging
- **Use `logging` module** with appropriate levels:
  - `DEBUG`: Health check results, zone operations, query handling
  - `INFO`: Zone updates, server lifecycle events
  - `WARNING`: Unexpected but recoverable conditions, malformed queries
  - `ERROR`: Validation failures, configuration errors
  - `CRITICAL`: (Not currently used)

**Example:**
```python
import logging

logging.debug("Checking A record %s ...", subdomain)
logging.info("A records changed")
logging.warning("Received query without question section")
logging.error("Failed to parse alias zones: %s", ex)
```

### Thread Safety
- **Use `dns.versioned.Zone`** with reader/writer transactions
- **Never share mutable state** between threads without synchronization
- **Prefer immutable data structures** for shared state
- **Use `threading.Event`** for shutdown signaling

### Performance Guidelines
- **Minimize allocations** in hot paths (DNS query handling)
- **Use generators** for infinite sequences (SOA serial, DNSSEC keys)
- **Batch zone updates** (recreate entire zone, not incremental)
- **Profile before optimizing** (no premature optimization)

## Development Patterns

### Factory Pattern Usage
Create factory functions for complex object construction with validation.

**Location:** `dns_server_config_factory.py`

### Value Object Pattern Usage
Use immutable value objects for domain concepts.

**Locations:** `records/a_healthy_ip.py`, `records/a_healthy_record.py`

### Generator Pattern Usage
Use generators for sequences with time-varying values.

**Locations:** `records/soa_record.py`, `records/dnssec.py`

### Partial Application Pattern Usage
Bind configuration at initialization to simplify call sites.

**Location:** `dns_server_zone_updater.py`

For detailed pattern explanations, see [docs/system-patterns.md](system-patterns.md).

## Tools and Utilities Module

### Validation Functions (`tools/`)
- **Signature:** `is_valid_*(value: Any) -> Tuple[bool, Optional[str]]`
- **Return:** `(True, None)` for valid, `(False, error_message)` for invalid
- **Do not raise exceptions** — return error descriptions for logging

**Example:**
```python
def is_valid_ip(ip: Any) -> Tuple[bool, Optional[str]]:
    """Validate IP address format."""
    if not isinstance(ip, str):
        return False, f"Must be string, got {type(ip).__name__}"
    # Additional validation...
    return True, None
```

### Normalization Functions (`tools/`)
- **Pure functions** that transform input to canonical form
- **Assume input is already validated** (validation happens first)

**Example:**
```python
def normalize_ip(ip: str) -> str:
    """Normalize IP address by removing leading zeros from octets."""
    return ".".join(str(int(octet)) for octet in ip.split("."))
```

## Docker Development

### Building Docker Image
```bash
docker build -t a-healthy-dns:dev .
```

### Running Docker Container
```bash
docker run -d \
  --name a-healthy-dns-dev \
  -p 53053:53053/udp \
  -e DNS_HOSTED_ZONE="example.local" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["127.0.0.1"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.local"]' \
  a-healthy-dns:dev
```

### Viewing Logs
```bash
docker logs -f a-healthy-dns-dev
```

### Testing DNS Queries
```bash
# Using dig
dig @localhost -p 53053 www.example.local

# Using nslookup
nslookup www.example.local 127.0.0.1 -port=53053
```

## Version Management

- **Version location:** `setup.py`
- **Format:** Semantic versioning (`MAJOR.MINOR.PATCH`)
- **Update process:** Modify `setup.py`, commit, tag, push
- **CI handles:** Version validation, GitHub releases, Docker tagging

## Troubleshooting Development Issues

### Tests Fail with Import Errors
```bash
# Ensure package is installed
pip install -e .
```

### Coverage Report Not Generated
```bash
# Ensure pytest-cov is installed
pip install pytest-cov

# Check .coveragerc syntax
cat .coveragerc
```

### Docker Build Fails
```bash
# Check Dockerfile syntax
# Ensure dependencies in setup.py are correct
# Try building with --no-cache
docker build --no-cache -t a-healthy-dns:dev .
```

### Type Checking (Optional)
This project does not currently use mypy or other type checkers in CI, but they can be used locally:
```bash
pip install mypy
mypy indisoluble/
```

---

**Last Updated:** March 7, 2026  
**Version:** 1.0 (Bootstrap)
