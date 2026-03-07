# Configuration Reference

## Overview

A Healthy DNS accepts configuration through command-line arguments or environment variables (when running in Docker). All configuration is loaded once at startup; changes require a restart.

## Command-Line Configuration

### Required Parameters

#### `--hosted-zone`
- **Type:** String
- **Required:** Yes
- **Description:** The hosted zone domain name for which this DNS server is authoritative
- **Example:** `--hosted-zone example.com`
- **Validation:** Must be a valid DNS name

#### `--zone-resolutions`
- **Type:** JSON object
- **Required:** Yes
- **Description:** Configuration defining subdomains, their IP addresses, and health check ports
- **Format:**
  ```json
  {
    "subdomain_name": {
      "ips": ["ip1", "ip2", ...],
      "health_port": port_number
    }
  }
  ```
- **Example:**
  ```bash
  --zone-resolutions '{"www":{"ips":["192.168.1.100","192.168.1.101"],"health_port":8080},"api":{"ips":["192.168.1.102"],"health_port":8000}}'
  ```
- **Validation:**
  - `ips`: Must be an array of valid IPv4 addresses (non-empty)
  - `health_port`: Must be an integer between 1-65535
  - Subdomain names validated as valid DNS labels

#### `--ns`
- **Type:** JSON array
- **Required:** Yes
- **Description:** Name servers responsible for this zone
- **Example:** `--ns '["ns1.example.com", "ns2.example.com"]'`
- **Validation:** Must be valid fully-qualified domain names

### Optional Parameters

#### `--port`
- **Type:** Integer
- **Default:** `53053`
- **Description:** UDP port on which the DNS server listens
- **Example:** `--port 53`
- **Range:** 1-65535
- **Note:** Port 53 is the standard DNS port; requires root privileges on Unix systems

#### `--test-min-interval`
- **Type:** Integer
- **Default:** `30` (seconds)
- **Description:** Minimum interval between health check cycles
- **Example:** `--test-min-interval 15`
- **Behavior:** Actual interval may be longer if health checks take longer than this value
- **Impact:** Affects TTL calculations and zone update frequency

#### `--test-timeout`
- **Type:** Integer
- **Default:** `2` (seconds)
- **Description:** Maximum time to wait for each TCP health check connection
- **Example:** `--test-timeout 3`
- **Behavior:** Health check fails if connection is not established within this time
- **Tuning:** Increase for high-latency networks; decrease for faster failure detection

#### `--log-level`
- **Type:** String (enum)
- **Default:** `info`
- **Choices:** `debug`, `info`, `warning`, `error`, `critical`
- **Description:** Logging verbosity level
- **Example:** `--log-level debug`
- **Levels:**
  - `debug`: Health check results, zone operations, query details
  - `info`: Zone updates, server lifecycle, configuration
  - `warning`: Unexpected conditions, malformed queries
  - `error`: Validation failures, configuration errors
  - `critical`: (Not currently used)

#### `--alias-zones`
- **Type:** JSON array
- **Default:** `[]` (empty array)
- **Description:** Additional domain names that resolve to the same records as the hosted zone
- **Example:** `--alias-zones '["alias1.com", "alias2.com"]'`
- **Behavior:** Health checks are performed once; all zones return the same healthy IPs
- **Use case:** Serving multiple domains from the same backend infrastructure

### DNSSEC Parameters

#### `--priv-key-path`
- **Type:** String (file path)
- **Required:** No (DNSSEC disabled if omitted)
- **Description:** Path to the DNSSEC private key file in PEM format
- **Example:** `--priv-key-path /etc/dns/keys/private.pem`
- **Validation:** File must exist and be readable
- **Format:** PEM-encoded private key

#### `--priv-key-alg`
- **Type:** String (enum)
- **Default:** `RSASHA256`
- **Description:** Algorithm used for DNSSEC signing
- **Example:** `--priv-key-alg RSASHA256`
- **Supported algorithms:** (from dnspython)
  - `RSASHA1`
  - `RSASHA1NSEC3SHA1`
  - `RSASHA256` (recommended)
  - `RSASHA512`
  - `ECDSAP256SHA256`
  - `ECDSAP384SHA384`
  - `ED25519`
  - `ED448`

## Docker Environment Variables

When running in Docker, configuration is provided via environment variables. Each CLI parameter has a corresponding environment variable.

### Environment Variable Mapping

| CLI Parameter | Environment Variable | Required |
|---------------|---------------------|----------|
| `--hosted-zone` | `DNS_HOSTED_ZONE` | Yes |
| `--zone-resolutions` | `DNS_ZONE_RESOLUTIONS` | Yes |
| `--ns` | `DNS_NAME_SERVERS` | Yes |
| `--port` | `DNS_PORT` | No |
| `--test-min-interval` | `DNS_TEST_MIN_INTERVAL` | No |
| `--test-timeout` | `DNS_TEST_TIMEOUT` | No |
| `--log-level` | `DNS_LOG_LEVEL` | No |
| `--alias-zones` | `DNS_ALIAS_ZONES` | No |
| `--priv-key-path` | `DNS_PRIV_KEY_PATH` | No |
| `--priv-key-alg` | `DNS_PRIV_KEY_ALG` | No |

### Docker Example

```bash
docker run -d \
  --name a-healthy-dns \
  -p 53053:53053/udp \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  -e DNS_PORT="53053" \
  -e DNS_LOG_LEVEL="info" \
  -e DNS_TEST_MIN_INTERVAL="30" \
  -e DNS_TEST_TIMEOUT="2" \
  indisoluble/a-healthy-dns
```

### Docker Compose Example

See [docker-compose.example.yml](../docker-compose.example.yml) for a complete example with security settings, resource limits, and DNSSEC configuration.

## Configuration Patterns

### Single Domain with Multiple Backends

**Scenario:** Serve `example.com` with two subdomains, each having multiple backend IPs.

```bash
a-healthy-dns \
  --hosted-zone example.com \
  --zone-resolutions '{
    "www": {
      "ips": ["10.0.1.100", "10.0.1.101", "10.0.1.102"],
      "health_port": 80
    },
    "api": {
      "ips": ["10.0.2.100", "10.0.2.101"],
      "health_port": 8080
    }
  }' \
  --ns '["ns1.example.com", "ns2.example.com"]'
```

### Multi-Domain (Aliases)

**Scenario:** Serve multiple domains (`example.com`, `example.net`, `example.org`) with the same backend IPs.

```bash
a-healthy-dns \
  --hosted-zone example.com \
  --alias-zones '["example.net", "example.org"]' \
  --zone-resolutions '{
    "www": {
      "ips": ["192.168.1.100", "192.168.1.101"],
      "health_port": 80
    }
  }' \
  --ns '["ns1.example.com"]'
```

Results in:
- `www.example.com` → healthy IPs from 192.168.1.100/101
- `www.example.net` → same healthy IPs
- `www.example.org` → same healthy IPs

### High-Frequency Health Checks

**Scenario:** Fast failover with frequent health checks (10-second intervals, 1-second timeout).

```bash
a-healthy-dns \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["10.0.1.100"],"health_port":8080}}' \
  --ns '["ns1.example.com"]' \
  --test-min-interval 10 \
  --test-timeout 1
```

### DNSSEC-Enabled Configuration

**Scenario:** Zone signing with DNSSEC using RSA SHA-256.

```bash
a-healthy-dns \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["192.168.1.100"],"health_port":80}}' \
  --ns '["ns1.example.com"]' \
  --priv-key-path /etc/dns/keys/example.com.key \
  --priv-key-alg RSASHA256
```

### Production Configuration (Port 53)

**Scenario:** Production deployment on standard DNS port.

```bash
# Requires root or CAP_NET_BIND_SERVICE capability
sudo a-healthy-dns \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["10.0.1.100","10.0.1.101"],"health_port":80}}' \
  --ns '["ns1.example.com", "ns2.example.com"]' \
  --port 53 \
  --test-min-interval 30 \
  --test-timeout 2 \
  --log-level info
```

## TTL Behavior

TTL (Time to Live) values are automatically calculated based on `test-min-interval` and health check overhead. This ensures DNS clients cache records appropriately while maintaining freshness.

### TTL Calculation Formula

Implemented in [indisoluble/a_healthy_dns/records/time.py](../indisoluble/a_healthy_dns/records/time.py):

- **A record TTL** = `max_interval * 2`
- **NS record TTL** = `A record TTL * 30`
- **SOA record TTL** = `NS record TTL`
- **DNSKEY TTL** = `A record TTL * 10`

Where `max_interval` = `max(test-min-interval, actual_health_check_duration)`

### TTL Examples

| test-min-interval | A Record TTL | NS Record TTL | DNSKEY TTL |
|-------------------|--------------|---------------|------------|
| 10 seconds | 20 seconds | 600 seconds (10 min) | 200 seconds (3.3 min) |
| 30 seconds | 60 seconds | 1800 seconds (30 min) | 600 seconds (10 min) |
| 60 seconds | 120 seconds | 3600 seconds (60 min) | 1200 seconds (20 min) |

### TTL Impact

- **Lower TTLs:** Faster propagation of health changes; higher DNS query load
- **Higher TTLs:** Reduced DNS query load; slower propagation of health changes
- **Balance:** Default 30-second interval provides good balance for most use cases

## Health Check Behavior

### TCP Connectivity Test

Health checks use TCP socket connection attempts:

```python
socket.create_connection((ip, health_port), timeout=test_timeout)
```

- **Success:** Connection establishes within timeout → IP marked healthy
- **Failure:** Connection times out or fails → IP marked unhealthy
- **Protocol-agnostic:** Works with any TCP service (HTTP, HTTPS, gRPC, custom)

### Health Check Cycle

1. Health checker wakes up every `test-min-interval` seconds
2. For each subdomain:
   - For each IP:
     - Attempt TCP connection on `health_port`
     - Update IP health status
3. If any health status changed:
   - Recreate DNS zone with updated A records
   - Increment SOA serial number
4. If DNSSEC enabled and signatures near expiration:
   - Resign zone
5. Sleep until next interval

### Subdomain Behavior

#### All IPs Healthy
- DNS query returns all healthy IPs in A record
- Round-robin distribution by DNS client/resolver

#### Some IPs Unhealthy
- DNS query returns only healthy IPs
- Unhealthy IPs excluded from responses

#### All IPs Unhealthy
- DNS query returns NXDOMAIN (subdomain does not exist)
- Fail-closed security posture (no traffic to broken backends)

### Health Check Performance

Health check duration depends on:
- Number of IPs configured
- `test-timeout` setting
- Network latency

**Formula:**
```
duration = sum(num_ips_per_subdomain * test_timeout) + management_overhead
```

If duration exceeds `test-min-interval`, the actual interval becomes the duration.

## Validation and Error Handling

### Startup Validation

All configuration is validated at startup. Invalid configuration causes immediate exit with error message.

**Validated items:**
- Hosted zone is valid DNS name
- Alias zones are valid DNS names
- IP addresses are valid IPv4 addresses
- Ports are in range 1-65535
- Subdomain names are valid DNS labels
- Name servers are valid FQDNs
- JSON is well-formed
- DNSSEC key file exists and is readable (if specified)

### Example Validation Errors

```
Failed to parse zone resolutions: Expecting value: line 1 column 1 (char 0)
```
→ `--zone-resolutions` is not valid JSON

```
Zone resolution subdomain 'www@' is not valid: Contains invalid characters
```
→ Subdomain name contains invalid DNS characters

```
Invalid IP address: Must be string, got int
```
→ IP address in `ips` array is not a string

```
Invalid port: Port must be between 1 and 65535, got 0
```
→ `health_port` is out of range

## Configuration Tuning Guidance

### For Fast Failover
- Set `test-min-interval` to 10-15 seconds
- Set `test-timeout` to 1-2 seconds
- Accept higher DNS query load (lower TTLs)

### For Reduced DNS Load
- Set `test-min-interval` to 60+ seconds
- Accept slower failover propagation (higher TTLs)

### For High-Latency Networks
- Increase `test-timeout` to 5-10 seconds
- Increase `test-min-interval` to accommodate longer health checks

### For Production Workloads
- Use default values (30-second interval, 2-second timeout)
- Enable DNSSEC if supported by infrastructure
- Run on port 53 with appropriate privileges
- Set `log-level` to `info` or `warning`

### For Development/Testing
- Use high port (53053 default) to avoid privilege requirements
- Set `log-level` to `debug` for detailed insight
- Short intervals for rapid testing (10 seconds)

## Security Considerations

### Port Binding
- **Port 53:** Requires root or `CAP_NET_BIND_SERVICE` capability
- **High ports (>1024):** No special privileges required
- **Docker:** Use `cap_add: [NET_BIND_SERVICE]` for port 53

### DNSSEC Key Management
- Store private keys with restricted permissions (0600)
- Use volume mounts (read-only) for Docker deployments
- Rotate keys periodically per DNSSEC best practices

### Resource Limits
- Set memory/CPU limits in Docker to prevent resource exhaustion
- Monitor for abnormal query patterns (potential DDoS)

### Network Exposure
- Bind to specific interface if not serving public DNS
- Use firewall rules to restrict DNS query sources
- Consider rate limiting at network level

---

**Last Updated:** March 7, 2026  
**Version:** 1.0 (Bootstrap)
