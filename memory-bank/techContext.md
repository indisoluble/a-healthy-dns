# Technology Context

**Last Updated**: 2026-02-26

## Core Stack

### Language & Runtime
- **Python 3.10+** (Required)
  - Type hints and modern syntax (match/case not used yet)
  - NamedTuple for immutable data structures
  - Type checking via mypy (not enforced in tests)
  - Justification: Chosen for rapid development, extensive DNS library support

### Key Dependencies

#### dnspython 2.8.0+
**Purpose**: DNS protocol implementation and zone management  
**Usage**:
- `dns.versioned.Zone` - Thread-safe in-memory zone storage
- `dns.transaction` - Atomic zone updates
- `dns.message` - DNS query/response parsing
- `dns.dnssec` - DNSSEC signing operations
- `dns.name` - DNS name manipulation

**Critical Features Used**:
- Versioned zones with reader/writer transactions
- DNSSEC signing with custom timing parameters
- DNS message wire format encoding/decoding

**Location**: All core modules depend on it

#### cryptography 46.0.5+
**Purpose**: DNSSEC private key handling  
**Usage**:
- Load RSA private keys from PEM files
- Interface with dnspython's DNSSEC signing

**Location**: [indisoluble/a_healthy_dns/dns_server_config_factory.py](indisoluble/a_healthy_dns/dns_server_config_factory.py#L186-L213)

### Standard Library

#### socketserver
**Purpose**: UDP server infrastructure  
**Pattern**: `socketserver.UDPServer` with custom handler  
**Location**: [indisoluble/a_healthy_dns/main.py:236-242](indisoluble/a_healthy_dns/main.py#L236-L242)

#### threading
**Purpose**: Background zone updater  
**Pattern**: Single daemon thread with Event-based shutdown  
**Location**: [indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py](indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py)

#### socket
**Purpose**: TCP connectivity testing  
**Pattern**: `socket.create_connection()` with timeout  
**Location**: [indisoluble/a_healthy_dns/tools/can_create_connection.py:14-20](indisoluble/a_healthy_dns/tools/can_create_connection.py#L14-L20)

#### ipaddress
**Purpose**: IP address validation and normalization  
**Location**: [indisoluble/a_healthy_dns/tools/is_valid_ip.py](indisoluble/a_healthy_dns/tools/is_valid_ip.py)

#### argparse
**Purpose**: CLI argument parsing  
**Pattern**: Grouped arguments with epilog documentation  
**Location**: [indisoluble/a_healthy_dns/main.py:58-207](indisoluble/a_healthy_dns/main.py#L58-L207)

#### logging
**Purpose**: Structured logging to stdout/stderr  
**Pattern**: Module-level logger with configurable levels  
**Configuration**: [indisoluble/a_healthy_dns/main.py:218-222](indisoluble/a_healthy_dns/main.py#L218-L222)

## Development Tools

### Testing

#### pytest
**Purpose**: Test framework  
**Usage**: Unit and integration tests  
**Structure**: Mirror source tree in `tests/` directory  
**Location**: `tests/indisoluble/a_healthy_dns/`

#### pytest Fixtures
**Conventions**:
- `@pytest.fixture` for reusable test data
- Module-level fixtures in conftest.py (if needed)
- Parametrized tests with `@pytest.mark.parametrize`

**Example**: [tests/indisoluble/a_healthy_dns/test_dns_server_config_factory.py:18-55](tests/indisoluble/a_healthy_dns/test_dns_server_config_factory.py#L18-L55)

### Build & Packaging

#### setuptools
**Purpose**: Package distribution  
**Entry Point**: `a-healthy-dns` console script  
**Location**: [setup.py:1-12](setup.py#L1-L12)

#### Docker
**Purpose**: Containerized deployment  
**Pattern**: Multi-stage build (builder + production)  
**Security**:
- Non-root user (appuser:appuser, uid/gid 10000)
- Capability-based port binding (CAP_NET_BIND_SERVICE)
- Minimal production image (python:3-slim)

**Location**: [Dockerfile](Dockerfile)

## Architecture Decisions

### Why dnspython Over Low-Level DNS?
- **Pro**: Battle-tested DNS protocol implementation
- **Pro**: Thread-safe versioned zones (critical for concurrent access)
- **Pro**: DNSSEC signing built-in
- **Con**: Heavier dependency than raw socket + struct
- **Decision**: Reliability and security over minimal dependencies

### Why Threading Over Asyncio?
- **Pro**: socketserver.UDPServer is synchronous (simpler integration)
- **Pro**: Single background thread sufficient for health checks
- **Pro**: dnspython's Zone is thread-safe, not async-safe
- **Con**: Less efficient for high concurrency
- **Decision**: Simplicity over scalability (authoritative DNS, not recursive)

### Why TCP Health Checks Only?
- **Pro**: Simple, universal (any TCP service)
- **Pro**: Fast (connect + immediate close)
- **Con**: Doesn't validate application health
- **Decision**: Scope limitation - application health is user's responsibility

### Why Immutable Data Structures?
- **Pro**: Thread-safe without locks
- **Pro**: Clear mutation points (factory functions)
- **Pro**: Easier to reason about state changes
- **Con**: More object allocation
- **Decision**: Correctness over performance

## Version Constraints

### Pinned Dependencies
```python
# setup.py
install_requires=[
    "cryptography>=46.0.5,<47.0.0",
    "dnspython>=2.8.0,<3.0.0"
]
```

**Rationale**:
- Major version constraints prevent breaking changes
- Minor version floor ensures required features present

### Python Version
```python
python_requires=">=3.10"
```

**Rationale**:
- Type hints for immutable structures (NamedTuple)
- Modern type annotation support
- datetime.timezone.utc availability

## Known Limitations

### Technical Debt
- No async DNS query handling (single-threaded UDP server)
- No persistent zone storage (in-memory only)
- No hot-reload of configuration (requires restart)
- No metrics/Prometheus endpoint (logging only)

### Performance Constraints
- Health check duration scales linearly with (num_subdomains × num_ips_per_subdomain)
- Maximum ~1000 IPs with 2s timeout before update cycle exceeds reasonable bounds
- No connection pooling for health checks

### Security Considerations
- DNSSEC keys loaded from filesystem (no HSM/KMS support)
- No rate limiting on DNS queries
- No TSIG/SIG(0) transaction authentication
- Logs may contain IP addresses (PII consideration)

## Future Tech Considerations

### Potential Additions
- **HTTP(S) Health Checks**: More comprehensive than TCP
- **Metrics Export**: Prometheus endpoint for health check stats
- **Configuration Reload**: SIGHUP signal handler
- **Multiple Zone Support**: Serve multiple unrelated zones

### Potential Migrations
- **Async DNS Server**: Migrate to asyncio for better concurrency
- **Rust Core**: Performance-critical path (health checks) in Rust with PyO3
- **External Storage**: Redis/etcd for zone data persistence

### Constraints on Future Changes
- Must maintain single-binary deployment model
- Must not require database for basic operation
- Must remain suitable for Docker/K8s deployment
