# Quick Start Guide

**Last Updated**: 2026-02-26

## Common Session Patterns

### Session Startup (Fast Track)
**For**: Bug fixes, small changes
```
1. Load activeContext.md
2. Load relevant file(s) from codebase
3. Make changes
```

### Session Startup (Standard)
**For**: New features, testing work
```
1. Load activeContext.md + projectbrief.md
2. Load systemPatterns.md for architectural context
3. Load projectRules.md for coding standards
4. Proceed with work
```

---

## Common Code Patterns

### Creating Immutable Domain Objects

**Pattern**:
```python
class MyDomainObject:
    def __init__(self, value: str):
        # Validate first
        success, error = is_valid_value(value)
        if not success:
            raise ValueError(f"Invalid value: {error}")
        
        # Assign to private attributes
        self._value = value
    
    @property
    def value(self) -> str:
        return self._value
    
    def updated_value(self, new_value: str) -> "MyDomainObject":
        """Return new instance with updated value if changed."""
        if new_value == self._value:
            return self  # No allocation if unchanged
        return MyDomainObject(value=new_value)
```

**Examples**: [AHealthyIp](indisoluble/a_healthy_dns/records/a_healthy_ip.py), [AHealthyRecord](indisoluble/a_healthy_dns/records/a_healthy_record.py)

---

### Creating Factory Functions

**Pattern**:
```python
def make_my_record(config_param: int, source: MyDataSource) -> Optional[dns.rdataset.Rdataset]:
    """Create DNS record from source data with validation."""
    # Filter/validate data
    items = [item for item in source.items if item.is_valid]
    if not items:
        logging.debug("No valid items for record %s", source.name)
        return None
    
    # Calculate TTL based on config
    ttl = calculate_ttl(config_param)
    
    # Create and return record
    return dns.rdataset.from_text(dns.rdataclass.IN, dns.rdatatype.A, ttl, *items)
```

**Examples**: [make_a_record](indisoluble/a_healthy_dns/records/a_record.py), [make_ns_record](indisoluble/a_healthy_dns/records/ns_record.py)

---

### Creating Validation Functions

**Pattern**:
```python
from typing import Any, Tuple

def is_valid_my_type(value: Any) -> Tuple[bool, str]:
    """Validate my type with detailed error message.
    
    Returns:
        (True, "") if valid
        (False, "error message") if invalid
    """
    # Type check
    if not isinstance(value, str):
        return False, f"must be string, got {type(value).__name__}"
    
    # Format validation
    try:
        # Validation logic
        if not meets_criteria(value):
            return False, "does not meet criteria"
        return True, ""
    except Exception as ex:
        return False, str(ex)
```

**Usage**:
```python
success, error = is_valid_my_type(value)
if not success:
    raise ValueError(f"Invalid value: {error}")
```

**Examples**: [is_valid_ip](indisoluble/a_healthy_dns/tools/is_valid_ip.py), [is_valid_port](indisoluble/a_healthy_dns/tools/is_valid_port.py)

---

### Zone Update Transaction Pattern

**Pattern**:
```python
def update_zone(self):
    """Update zone atomically within transaction."""
    with self._zone.writer() as txn:
        # All changes in transaction
        txn.delete(some_name)
        txn.add(name, rdataset)
        
        # Optional: complex operations
        self._sign_zone(txn)
    # Transaction commits on context exit
```

**Note**: Exception rolls back automatically

**Examples**: [_recreate_zone](indisoluble/a_healthy_dns/dns_server_zone_updater.py#L175-L179)

---

### Zone Query Pattern

**Pattern**:
```python
def query_zone(self, query_name: dns.name.Name, query_type: dns.rdatatype.RdataType):
    """Query zone within reader transaction."""
    with self._zone.reader() as txn:
        node = txn.get_node(relative_name)
        if not node:
            return None
        
        rdataset = node.get_rdataset(self._zone.rdclass, query_type)
        return rdataset
```

**Note**: Multiple readers can run concurrently

**Examples**: [_update_response](indisoluble/a_healthy_dns/dns_server_udp_handler.py#L21-L66)

---

## Common Test Patterns

### Basic Unit Test
```python
def test_function_with_valid_input():
    """Test function with valid input returns expected output."""
    # Arrange
    input_value = "valid"
    
    # Act
    result = my_function(input_value)
    
    # Assert
    assert result is not None
    assert result.property == expected_value
```

### Parameterized Test
```python
@pytest.mark.parametrize(
    "invalid_input,expected_error",
    [
        (123, "must be string"),
        (None, "must be string"),
        ("", "cannot be empty"),
    ]
)
def test_function_with_invalid_input(invalid_input, expected_error):
    """Test function rejects invalid input."""
    success, error = validate_input(invalid_input)
    assert not success
    assert expected_error in error
```

### Fixture Pattern
```python
@pytest.fixture
def mock_zone():
    """Create mock zone for testing."""
    zone = dns.versioned.Zone("example.com.")
    with zone.writer() as txn:
        # Setup test data
        txn.add(dns.name.empty, test_soa_record)
    return zone

def test_with_fixture(mock_zone):
    """Test using fixture."""
    with mock_zone.reader() as txn:
        node = txn.get_node(dns.name.empty)
        assert node is not None
```

See [testing-patterns.md](./testing-patterns.md) for comprehensive guide.

---

## File Location Quick Reference

### Need to modify DNS query handling?
→ [indisoluble/a_healthy_dns/dns_server_udp_handler.py](indisoluble/a_healthy_dns/dns_server_udp_handler.py)

### Need to modify health checking?
→ [indisoluble/a_healthy_dns/dns_server_zone_updater.py](indisoluble/a_healthy_dns/dns_server_zone_updater.py)

### Need to modify configuration parsing?
→ [indisoluble/a_healthy_dns/dns_server_config_factory.py](indisoluble/a_healthy_dns/dns_server_config_factory.py)

### Need to modify CLI arguments?
→ [indisoluble/a_healthy_dns/main.py](indisoluble/a_healthy_dns/main.py) (_make_arg_parser function)

### Need to modify TTL calculations?
→ [indisoluble/a_healthy_dns/records/time.py](indisoluble/a_healthy_dns/records/time.py)

### Need to add validation?
→ [indisoluble/a_healthy_dns/tools/](indisoluble/a_healthy_dns/tools/) (create new validation function)

### Need to modify record creation?
→ [indisoluble/a_healthy_dns/records/](indisoluble/a_healthy_dns/records/) (a_record.py, ns_record.py, etc.)

---

## Common Debugging Patterns

### Enable Debug Logging
```bash
a-healthy-dns --log-level debug <other args>
```

### Test Health Checks
```bash
# Start server in terminal
a-healthy-dns --hosted-zone test.local \
  --zone-resolutions '{"www":{"ips":["127.0.0.1"],"health_port":8080}}' \
  --ns '["ns1.test.local"]' \
  --log-level debug

# In another terminal, start simple HTTP server
python -m http.server 8080

# Watch logs for health check results
```

### Test DNS Queries
```bash
# With dig
dig @127.0.0.1 -p 53053 www.example.com A

# With nslookup
nslookup -port=53053 www.example.com 127.0.0.1
```

### Run Tests
```bash
# All tests
pytest tests/

# Specific test file
pytest tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py

# Specific test
pytest tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py::test_handle_valid_query

# With verbose output
pytest -v tests/

# With test output (prints)
pytest -s tests/
```

---

## Common Error Patterns

### "Failed to parse zone resolutions"
**Cause**: Invalid JSON in `--zone-resolutions`  
**Fix**: Validate JSON, ensure proper escaping in shell
```bash
# Wrong (unescaped quotes)
--zone-resolutions '{"www":{"ips":["192.168.1.1"],"health_port":8080}}'

# Correct (escaped quotes or use double quotes outside)
--zone-resolutions "{\"www\":{\"ips\":[\"192.168.1.1\"],\"health_port\":8080}}"
```

### "Zone resolution for 'X' must include 'ips' key"
**Cause**: Missing required key in zone resolution config  
**Fix**: Ensure each subdomain has both `ips` and `health_port`
```json
{
  "www": {
    "ips": ["192.168.1.1"],
    "health_port": 8080
  }
}
```

### "Invalid IP address: ..."
**Cause**: Invalid IP format in configuration  
**Fix**: Use valid IPv4/IPv6 addresses
```json
// Wrong
"ips": ["invalid", "192.168.1.999"]

// Correct
"ips": ["192.168.1.1", "192.168.1.2"]
```

### "Invalid port: must be between 1 and 65535"
**Cause**: Port out of valid range  
**Fix**: Use valid port numbers
```json
// Wrong
"health_port": 0
"health_port": 99999

// Correct
"health_port": 8080
```

### DNS queries return NXDOMAIN
**Cause**: Query for domain not in hosted/alias zones  
**Fix**: Ensure query matches configured zone
```bash
# If hosted-zone is "example.com"
dig @127.0.0.1 -p 53053 www.example.com A  # ✅ Correct
dig @127.0.0.1 -p 53053 www.other.com A    # ❌ NXDOMAIN
```

### Health checks always fail
**Cause**: Target service not listening on configured port  
**Debug**:
```bash
# Test connectivity manually
nc -zv <ip> <port>
telnet <ip> <port>

# Check logs at debug level
--log-level debug
```

---

## Integration Points

### Docker Integration
```dockerfile
FROM indisoluble/a-healthy-dns:latest

# Mount DNSSEC keys (optional)
VOLUME ["/app/keys"]

# Expose DNS port
EXPOSE 53/udp

CMD ["a-healthy-dns", \
     "--hosted-zone", "example.com", \
     "--zone-resolutions", "{...}", \
     "--ns", "[...]"]
```

### Docker Compose Integration
```yaml
version: '3'
services:
  dns:
    image: indisoluble/a-healthy-dns:latest
    ports:
      - "53053:53053/udp"
    command:
      - --hosted-zone=example.com
      - --zone-resolutions={"www":{"ips":["app"],"health_port":8080}}
      - --ns=["ns1.example.com"]
    depends_on:
      - app
  
  app:
    image: myapp:latest
    ports:
      - "8080:8080"
```

### Kubernetes Integration
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: healthy-dns
spec:
  containers:
  - name: dns
    image: indisoluble/a-healthy-dns:latest
    args:
      - --hosted-zone=example.com
      - --zone-resolutions={"www":{"ips":["10.0.1.1"],"health_port":8080}}
      - --ns=["ns1.example.com"]
    ports:
    - containerPort: 53053
      protocol: UDP
```

---

## Performance Tuning

### Health Check Interval
```bash
# Faster detection (more CPU)
--test-min-interval 10

# Slower detection (less CPU)
--test-min-interval 60
```

**Trade-off**: Lower interval = faster failover, higher CPU usage

### Health Check Timeout
```bash
# Faster failure detection
--test-timeout 1

# Tolerate slower responses
--test-timeout 5
```

**Trade-off**: Lower timeout = faster detection, more false negatives

### TTL Calculation
TTLs are auto-calculated based on health check interval:
- A record TTL = max_interval (calculated from min_interval + health check duration)
- Lower TTLs = clients retry sooner after failure
- Higher TTLs = less query load, slower failover at client

**Note**: TTL calculation is automatic, no configuration needed
