# Testing Patterns

**Last Updated**: 2026-02-26

## Test Organization

### Directory Structure
```
tests/
├── __init__.py
└── indisoluble/
    ├── __init__.py
    └── a_healthy_dns/
        ├── __init__.py
        ├── test_dns_server_config_factory.py
        ├── test_dns_server_udp_handler.py
        ├── test_dns_server_zone_updater.py
        ├── test_dns_server_zone_updater_threated.py
        ├── test_main.py
        ├── records/
        │   ├── __init__.py
        │   ├── test_a_healthy_ip.py
        │   ├── test_a_healthy_record.py
        │   ├── test_a_record.py
        │   ├── test_dnssec.py
        │   ├── test_ns_record.py
        │   ├── test_soa_record.py
        │   └── test_zone_origins.py
        └── tools/
            ├── __init__.py
            ├── test_can_create_connection.py
            ├── test_is_valid_ip.py
            ├── test_is_valid_port.py
            ├── test_is_valid_subdomain.py
            ├── test_normalize_ip.py
            └── test_uint32_current_time.py
```

**Convention**: Mirror source tree exactly, prefix test files with `test_`

---

## Test Naming

### Test Function Names
**Pattern**: `test_<function_name>_<scenario>`

```python
# Testing function behavior
def test_make_a_record_with_healthy_ips():
    ...

def test_make_a_record_with_no_healthy_ips():
    ...

# Testing class methods
def test_update_response_with_relative_name_found():
    ...

def test_update_response_domain_not_found():
    ...
```

**Conventions**:
- Descriptive scenario names (not `test_1`, `test_2`)
- Positive cases before negative cases
- Edge cases clearly labeled

---

## Test Structure

### Arrange-Act-Assert Pattern
```python
def test_example():
    """Test example function with valid input."""
    # Arrange - Setup test data
    input_value = "test"
    expected_output = "expected"
    
    # Act - Call function under test
    result = my_function(input_value)
    
    # Assert - Verify behavior
    assert result == expected_output
```

**Convention**: Use comments to mark sections in complex tests

---

## Fixtures

### Basic Fixture
```python
@pytest.fixture
def valid_args():
    """Create valid configuration arguments for testing."""
    return {
        ARG_HOSTED_ZONE: "example.com",
        ARG_ALIAS_ZONES: "[]",
        ARG_ZONE_RESOLUTIONS: '{"www":{"ips":["192.168.1.1"],"health_port":8080}}',
        ARG_NAME_SERVERS: '["ns1.example.com"]',
    }

def test_make_config_success(valid_args):
    """Test config creation with valid arguments."""
    config = make_config(valid_args)
    assert config is not None
```

**Usage**: Fixtures for reusable test data

### Fixture with Cleanup
```python
@pytest.fixture
def mock_server():
    """Start mock server for testing, cleanup after."""
    server = start_mock_server()
    yield server
    server.stop()
```

**Pattern**: Use `yield` for cleanup logic

---

## Parameterized Tests

### Basic Parameterization
```python
@pytest.mark.parametrize(
    "invalid_ip",
    ["invalid", "256.1.1.1", "192.168.1", None, 123]
)
def test_is_valid_ip_with_invalid_values(invalid_ip):
    """Test IP validation rejects invalid values."""
    success, error = is_valid_ip(invalid_ip)
    assert not success
    assert error  # Non-empty error message
```

### Multiple Parameters
```python
@pytest.mark.parametrize(
    "ip,expected_normalized",
    [
        ("192.168.1.1", "192.168.1.1"),
        ("  192.168.1.1  ", "192.168.1.1"),
        ("::1", "::1"),
    ]
)
def test_normalize_ip(ip, expected_normalized):
    """Test IP normalization."""
    result = normalize_ip(ip)
    assert result == expected_normalized
```

### Named Parameters
```python
@pytest.mark.parametrize(
    "subdomain,expected_valid",
    [
        ("valid", True),
        ("valid-sub", True),
        ("-invalid", False),
        ("invalid.", False),
    ],
    ids=["simple", "with-dash", "leading-dash", "trailing-dot"]
)
def test_subdomain_validation(subdomain, expected_valid):
    """Test subdomain validation rules."""
    success, _ = is_valid_subdomain(subdomain)
    assert success == expected_valid
```

**Convention**: Use `ids` parameter for readable test names

---

## Mocking

### Mock External Dependencies
```python
def test_can_create_connection_success(monkeypatch):
    """Test successful connection returns True."""
    # Mock socket.create_connection
    def mock_connection(address, timeout):
        return MockSocket()
    
    monkeypatch.setattr("socket.create_connection", mock_connection)
    
    result = can_create_connection("192.168.1.1", 8080, 2.0)
    assert result is True
```

### Mock with Side Effects
```python
def test_can_create_connection_failure(monkeypatch):
    """Test connection failure returns False."""
    def mock_connection_error(address, timeout):
        raise ConnectionRefusedError("Connection refused")
    
    monkeypatch.setattr("socket.create_connection", mock_connection_error)
    
    result = can_create_connection("192.168.1.1", 8080, 2.0)
    assert result is False
```

**Convention**: Use pytest's `monkeypatch` fixture for mocking

---

## Testing Immutable Objects

### Test Immutability
```python
def test_healthy_ip_updated_status_returns_new_instance():
    """Test updated_status creates new instance on change."""
    original = AHealthyIp("192.168.1.1", 8080, False)
    updated = original.updated_status(True)
    
    # Different instances
    assert updated is not original
    
    # Original unchanged
    assert original.is_healthy is False
    
    # Updated has new value
    assert updated.is_healthy is True
```

### Test Same-Instance Optimization
```python
def test_healthy_ip_updated_status_returns_same_if_unchanged():
    """Test updated_status returns same instance if no change."""
    original = AHealthyIp("192.168.1.1", 8080, True)
    updated = original.updated_status(True)
    
    # Same instance (optimization)
    assert updated is original
```

**Pattern**: Verify both mutation and optimization behavior

---

## Testing Validation Functions

### Test Valid Cases
```python
def test_is_valid_ip_with_valid_ipv4():
    """Test valid IPv4 addresses pass validation."""
    success, error = is_valid_ip("192.168.1.1")
    assert success is True
    assert error == ""
```

### Test Invalid Cases
```python
def test_is_valid_ip_with_invalid_format():
    """Test invalid IP format fails validation."""
    success, error = is_valid_ip("invalid")
    assert success is False
    assert "does not appear to be" in error
```

### Test Type Errors
```python
def test_is_valid_ip_with_non_string():
    """Test non-string type fails validation."""
    success, error = is_valid_ip(123)
    assert success is False
    assert "must be string" in error
```

**Pattern**: Test success path, format errors, and type errors separately

---

## Testing Zone Operations

### Test Zone Creation
```python
def test_zone_updater_creates_zone():
    """Test zone updater creates initial zone."""
    config = create_test_config()
    updater = DnsServerZoneUpdater(30, 2, config)
    
    updater.update(check_ips=False)
    
    zone = updater.zone
    with zone.reader() as txn:
        soa_node = txn.get_node(dns.name.empty)
        assert soa_node is not None
```

### Test Zone Updates
```python
def test_zone_updater_updates_a_records():
    """Test zone updater modifies A records based on health."""
    config = create_test_config_with_unhealthy_ips()
    updater = DnsServerZoneUpdater(30, 2, config)
    
    # Initial update
    updater.update(check_ips=False)
    
    # Simulate health check changes
    updater.update(check_ips=True, should_abort=lambda: False)
    
    # Verify zone reflects health changes
    zone = updater.zone
    with zone.reader() as txn:
        # Verify A record excludes unhealthy IPs
        ...
```

**Pattern**: Initial state → Action → Verify state change

---

## Testing Threading

### Test Thread Lifecycle
```python
def test_threaded_updater_starts_and_stops():
    """Test threaded updater lifecycle."""
    config = create_test_config()
    updater = DnsServerZoneUpdaterThreated(30, 2, config)
    
    # Start
    updater.start()
    assert updater._updater_thread.is_alive()
    
    # Stop
    result = updater.stop()
    assert result is True
    assert not updater._updater_thread.is_alive()
```

### Test Abort Mechanism
```python
def test_zone_updater_aborts_on_signal():
    """Test zone updater respects abort signal."""
    config = create_test_config()
    updater = DnsServerZoneUpdater(30, 2, config)
    
    abort_after_first = create_abort_after_n_calls(1)
    result = updater.update(check_ips=True, should_abort=abort_after_first)
    
    # Verify update was aborted
    assert result is RefreshARecordsResult.ABORTED
```

**Pattern**: Test start/stop and graceful shutdown

---

## Testing Error Handling

### Test Error Logging
```python
def test_make_config_logs_error_on_invalid_json(caplog):
    """Test config factory logs error on invalid JSON."""
    args = {ARG_ZONE_RESOLUTIONS: "invalid json"}
    
    with caplog.at_level(logging.ERROR):
        config = make_config(args)
    
    assert config is None
    assert "Failed to parse zone resolutions" in caplog.text
```

**Convention**: Use `caplog` fixture to verify logging

### Test Exception Handling
```python
def test_function_handles_exception_gracefully():
    """Test function returns False on exception."""
    result = can_create_connection("invalid", -1, 2.0)
    assert result is False  # No exception raised, graceful handling
```

**Pattern**: Verify graceful degradation, not exception propagation

---

## Testing DNS Protocol

### Test Query Parsing
```python
def test_handle_valid_query():
    """Test UDP handler processes valid DNS query."""
    query = dns.message.make_query("www.example.com.", dns.rdatatype.A)
    query_data = query.to_wire()
    
    mock_socket = MockSocket()
    handler = create_test_handler(query_data, mock_socket)
    handler.handle()
    
    # Verify response sent
    assert mock_socket.sent_data is not None
    response = dns.message.from_wire(mock_socket.sent_data)
    assert response.answer  # Has answer section
```

### Test Response Flags
```python
def test_response_has_authoritative_flag():
    """Test DNS response has authoritative answer flag."""
    query = dns.message.make_query("www.example.com.", dns.rdatatype.A)
    response = create_test_response(query)
    
    assert response.flags & dns.flags.AA  # Authoritative Answer flag set
```

**Pattern**: Create wire-format messages, verify protocol compliance

---

## Coverage Guidelines

### What to Test
- ✅ All validation functions (100% coverage)
- ✅ All record factories (positive + negative cases)
- ✅ Zone update logic (state transitions)
- ✅ Configuration parsing (valid + all error paths)
- ✅ Health check logic (success + failures)
- ✅ DNS query handling (all response codes)

### What NOT to Test
- ❌ Third-party library internals (dnspython, cryptography)
- ❌ Python standard library (socket, threading)
- ❌ Trivial getters/setters (properties with no logic)
- ❌ `__repr__` methods (unless complex logic)

### Edge Cases to Cover
- Empty collections (no IPs, no name servers)
- Boundary values (port 1, port 65535, timeout 0, interval 0)
- Type mismatches (string vs int, None vs value)
- Concurrent access (zone reader during update)
- Shutdown during operation (abort flag)

---

## Test Utilities

### Mock Objects
```python
class MockSocket:
    """Mock socket for testing UDP handler."""
    def __init__(self):
        self.sent_data = None
        self.sent_address = None
    
    def sendto(self, data, address):
        self.sent_data = data
        self.sent_address = address
```

### Test Data Builders
```python
def create_test_config(**overrides):
    """Create test configuration with defaults."""
    defaults = {
        "zone_origins": ZoneOrigins("example.com", []),
        "name_servers": frozenset(["ns1.example.com"]),
        "a_records": frozenset(),
        "ext_private_key": None,
    }
    defaults.update(overrides)
    return DnsServerConfig(**defaults)
```

**Pattern**: Builder functions for common test objects

---

## Running Tests

### All Tests
```bash
pytest tests/
```

### Specific Module
```bash
pytest tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py
```

### Specific Test
```bash
pytest tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py::test_handle_valid_query
```

### With Coverage
```bash
pytest --cov=indisoluble.a_healthy_dns --cov-report=html tests/
```

### With Verbose Output
```bash
pytest -v tests/
```

### With Test Output (prints)
```bash
pytest -s tests/
```

### Stop on First Failure
```bash
pytest -x tests/
```

---

## Test Anti-Patterns

### ❌ Testing Implementation Details
```python
# Wrong - Testing internal state
def test_internal_counter_increments():
    obj = MyClass()
    obj.method()
    assert obj._counter == 1  # ❌ Testing private attribute
```

**Instead**: Test observable behavior, not internal state

### ❌ Fragile Assertions
```python
# Wrong - Exact message matching
assert str(ex) == "Invalid IP address: must be string, got int"

# Better - Partial matching
assert "must be string" in str(ex)
```

### ❌ Test Interdependence
```python
# Wrong - Tests depend on order
def test_first():
    global_state = "modified"

def test_second():
    assert global_state == "modified"  # ❌ Depends on test_first
```

**Instead**: Each test independent, use fixtures for shared setup

### ❌ Overly Complex Tests
```python
# Wrong - Test does too much
def test_everything():
    # 100 lines of setup
    # Test 10 different scenarios
    # Multiple assertions for different features
```

**Instead**: One test per scenario, clear focus

---

## Continuous Integration

### Test Requirements
- All tests must pass before merge
- No skipped tests without justification
- No test warnings (use `pytest -W error`)

### Performance Requirements
- Full test suite < 30 seconds
- Individual test < 5 seconds
- No arbitrary sleep() calls (use mocks/events)

### Quality Requirements
- Descriptive test names
- Clear failure messages
- Minimal test boilerplate
