# Troubleshooting and Operations Guide

Common issues, debugging techniques, and operational procedures for **A Healthy DNS**.

> **Configuration reference:** see [`docs/configuration-reference.md`](configuration-reference.md) for all parameters.  
> **Architecture reference:** see [`docs/system-patterns.md`](system-patterns.md) for concurrency and zone update patterns.

---

## 1. Quick Diagnostics

### Check Service Status

#### Direct Installation
```bash
# Check if process is running
ps aux | grep a-healthy-dns

# Check port binding
lsof -nP -iUDP:53053  # Or your configured port
```

#### Docker
```bash
# Check container status
docker ps | grep a-healthy-dns

# Check container logs
docker logs a-healthy-dns
docker logs -f a-healthy-dns  # Follow logs in real-time

# Check resource usage
docker stats a-healthy-dns
```

### Test DNS Resolution

```bash
# Using dig (most detailed)
dig @localhost -p 53053 www.example.local

# Using nslookup
nslookup www.example.local 127.0.0.1 -port=53053

# Using host
host -p 53053 www.example.local 127.0.0.1

# Check SOA record
dig @localhost -p 53053 example.local SOA

# Check NS records
dig @localhost -p 53053 example.local NS
```

### Check Health Status (via Logs)

```bash
# Docker
docker logs a-healthy-dns 2>&1 | grep -i "health\|checked ip"

# Direct installation
journalctl -u a-healthy-dns | grep -i "health\|checked ip"
```

## 2. Common Issues

### Issue: DNS Server Not Starting

#### Symptoms
- Container exits immediately
- "Address already in use" error
- Configuration validation errors

#### Diagnosis
```bash
# Check logs for startup errors
docker logs a-healthy-dns

# Check if port is already in use
lsof -nP -iUDP:53053
```

#### Solutions

**Configuration validation failure:**
```bash
# Run with debug logging to see detailed errors
docker run -it \
  -e DNS_LOG_LEVEL="debug" \
  -e DNS_HOSTED_ZONE="example.local" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.local"]' \
  indisoluble/a-healthy-dns
```

Invalid configuration is a fail-fast startup error: the process logs the validation issue and exits with a non-zero status without binding the UDP port.

**Port already in use:**
```bash
# Find process using the port
sudo lsof -i UDP:53053

# Kill the process or use a different port
docker run -d \
  -p 53054:53053/udp \
  -e DNS_PORT="53053" \
  ...
```

**Permission denied (port 53):**
```bash
# Hardened container binding directly to container port 53: add NET_BIND_SERVICE back
docker run -d \
  --cap-add=NET_BIND_SERVICE \
  -p 53:53/udp \
  -e DNS_PORT="53" \
  ...

# Or avoid privileged binds inside the container entirely
docker run -d \
  -p 53:53053/udp \
  -e DNS_PORT="53053" \
  ...
```

### Issue: DNS Queries Not Responding

#### Symptoms
- `dig` times out
- No answer section in DNS responses
- Connection refused errors

#### Diagnosis
```bash
# Verify server is listening
lsof -nP -iUDP:53053

# Check if firewall is blocking
sudo iptables -L -n | grep 53053

# Test with tcpdump
sudo tcpdump -i any -n port 53053

# Check Docker port mapping
docker port a-healthy-dns
```

#### Solutions

**Server not listening:**
```bash
# Restart the service
docker restart a-healthy-dns

# Check configuration
docker logs a-healthy-dns | grep -i "listening"
```

**Firewall blocking:**
```bash
# Allow UDP traffic on DNS port
sudo ufw allow 53053/udp
sudo iptables -A INPUT -p udp --dport 53053 -j ACCEPT
```

**Docker networking issue:**
```bash
# Use host networking (testing only)
docker run -d --network host -e DNS_PORT="53053" ...

# Or verify port mapping
docker run -d -p 53053:53053/udp ...
```

### Issue: Wrong IP Addresses Returned

#### Symptoms
- DNS returns unhealthy IPs
- DNS returns no IPs when some are healthy
- DNS returns different IPs than expected

#### Diagnosis
```bash
# Check current zone state with debug logging
docker logs a-healthy-dns 2>&1 | tail -100 | grep -E "Checking|Checked IP|healthy"

# Verify configuration
docker exec a-healthy-dns env | grep DNS_ZONE_RESOLUTIONS

# Test health check manually
telnet <ip> <health_port>
nc -zv <ip> <health_port>
```

#### Solutions

**All IPs marked unhealthy:**
- Verify backend services are running on configured health ports
- Check health check timeout settings (increase if needed):
  ```bash
  -e DNS_TEST_TIMEOUT="5"
  ```
- Verify network connectivity from DNS server to backends

**Health check false positives:**
- Ensure health port accepts connections (not just HTTP endpoint)
- Verify firewall rules allow connectivity from DNS server

**Wrong subdomain queried:**
```bash
# Check zone configuration
dig @localhost -p 53053 example.local AXFR  # Won't work (no AXFR support)

# Query correct subdomain
dig @localhost -p 53053 www.example.local  # Not apex
```

### Issue: NXDOMAIN for Existing Subdomain

#### Symptoms
- Query returns NXDOMAIN status
- Subdomain exists in configuration but returns no answer

#### Diagnosis
```bash
# Check if subdomain is configured
docker exec a-healthy-dns env | grep DNS_ZONE_RESOLUTIONS

# Check health status in logs
docker logs a-healthy-dns 2>&1 | grep "www" | tail -20

# Verify all IPs for subdomain
dig @localhost -p 53053 www.example.local +short
```

#### Root Causes

1. **All IPs unhealthy** → NXDOMAIN (by design)
2. **Subdomain not in configuration** → NXDOMAIN
3. **Wrong zone queried** → REFUSED

#### Solutions

**All IPs unhealthy (fail-closed behavior):**
- This is expected behavior per [docs/project-brief.md](project-brief.md)
- Fix backend services or adjust health check parameters

**Subdomain misconfiguration:**
- Verify JSON syntax in `DNS_ZONE_RESOLUTIONS`
- Check for typos in subdomain names

**Zone mismatch:**
```bash
# Query with correct zone
dig @localhost -p 53053 www.example.local  # Not: www.wrong.com
```

### Issue: Slow DNS Responses

#### Symptoms
- High query latency (>50ms)
- Timeouts under load
- Client retry behavior

#### Diagnosis
```bash
# Measure response time
time dig @localhost -p 53053 www.example.local

# Check CPU/memory usage
docker stats a-healthy-dns

# Check zone update frequency
docker logs a-healthy-dns 2>&1 | grep "Updating zone" | tail -20

# Monitor packet processing
sudo tcpdump -i any -n port 53053 -c 100
```

#### Solutions

**High CPU usage:**
- Increase resource limits:
  ```yaml
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: '512M'
  ```
- Reduce query load (check for abusive clients)

**Slow health checks blocking queries:**
- Health checks run in separate thread; shouldn't block queries
- Verify using debug logs:
  ```bash
  docker logs a-healthy-dns 2>&1 | grep -E "Checking A record|Checked IP|Updating zone"
  ```

**Docker networking overhead:**
- Use host networking for better performance:
  ```bash
  docker run -d --network host -e DNS_PORT="53" ...
  ```

### Issue: DNSSEC Validation Failures

#### Symptoms
- DNSSEC-aware resolvers reject responses
- `dig +dnssec` shows no DNSSEC records (`RRSIG`, `DNSKEY`, `NSEC`)
- Key loading errors in logs

#### Diagnosis
```bash
# Check if DNSSEC is enabled
dig @localhost -p 53053 www.example.local +dnssec

# Check for DNSKEY records
dig @localhost -p 53053 example.local DNSKEY

# Check logs for signing errors
docker logs a-healthy-dns 2>&1 | grep -i "sign\|dnssec\|rrsig"
```

#### Solutions

**Private key not loaded:**
```bash
# Verify key file exists and is readable
docker exec a-healthy-dns ls -la /app/keys/

# Check file permissions (should be readable)
docker exec a-healthy-dns cat /app/keys/private.pem | head -1
```

**Wrong key format:**
- Key must be PEM format
- Verify with: `openssl rsa -in private.pem -text -noout`

**Algorithm mismatch:**
- Ensure `DNS_PRIV_KEY_ALG` matches key algorithm
- Accepted values: `RSASHA256`, `RSASHA512`, `ECDSAP256SHA256`, `ECDSAP384SHA384`, `ED25519`, `ED448`

### Issue: Memory Leak or High Memory Usage

#### Symptoms
- Memory usage grows over time
- Container OOM killed
- System slowdown

#### Diagnosis
```bash
# Monitor memory over time
docker stats a-healthy-dns

# Check for memory limits
docker inspect a-healthy-dns | grep -i memory

# Review zone size
docker logs a-healthy-dns 2>&1 | grep "Updating zone" | wc -l
```

#### Solutions

**Set resource limits:**
```yaml
deploy:
  resources:
    limits:
      memory: '256M'
    reservations:
      memory: '128M'
```

**Reduce zone update frequency:**
- Increase `DNS_TEST_MIN_INTERVAL` to reduce updates
- Fewer health checks = fewer zone recreations

**Review configuration:**
- Large number of IPs → more memory for zone storage
- Many subdomains → larger zone size

## 3. Log Interpretation

### Log Levels and Their Meaning

#### DEBUG
Shows detailed operational information:
```
Checking A record www.example.local ...
Checked IP 192.168.1.100 on port 8080: from True to False
A record www.example.local checked
Clearing zone...
Added A record www.example.local to zone
Zone signed with expiration time 2026-03-07 12:30:45
```

**Use when:** Troubleshooting health checks, zone updates, DNSSEC signing

#### INFO
Normal operational events:
```
DNS server listening on port 53053...
Initializing zone...
Starting Zone Updater...
A records changed
Updating zone...
```

**Use when:** Normal operations, monitoring zone update frequency

#### WARNING
Unexpected but recoverable conditions:
```
Received query for domain not in hosted or alias zones: example.org
Received query for unknown subdomain: api.example.local
Failed to parse DNS query: Truncated message
Zone Updater is already running
```

**Use when:** Investigating invalid queries, misconfigurations

#### ERROR
Configuration or operational failures:
```
Failed to parse alias zones: Expecting value: line 1 column 1
Zone resolution subdomain 'www@' is not valid: Contains invalid characters
Invalid IP address: Must be string, got int
Failed to load DNSSEC private key: [Errno 2] No such file or directory
```

**Use when:** Startup failures, validation issues

### Common Log Patterns

#### Healthy Operation
```
INFO - Starting Zone Updater...
INFO - DNS server listening on port 53053...
DEBUG - Checking A record www.example.local ...
DEBUG - Checked IP 192.168.1.100 on port 8080: from True to True
DEBUG - A record www.example.local checked
```

#### Health Status Change
```
DEBUG - Checked IP 192.168.1.100 on port 8080: from True to False
INFO - A records changed
INFO - Updating zone...
DEBUG - Clearing zone...
DEBUG - Added A record www.example.local to zone
```

#### All IPs Unhealthy (No A Records)
```
DEBUG - Checked IP 192.168.1.100 on port 8080: from True to False
DEBUG - Checked IP 192.168.1.101 on port 8080: from True to False
INFO - A records changed
INFO - Updating zone...
DEBUG - A record www.example.local skipped
```
Result: Queries return NXDOMAIN

#### Graceful Shutdown
```
INFO - Received SIGTERM signal, shutting down DNS server...
INFO - Stopping Zone Updater...
```

## 4. Performance Tuning

### Optimize for Low Latency

```bash
# Fast health checks
-e DNS_TEST_MIN_INTERVAL="10" \
-e DNS_TEST_TIMEOUT="1"

# Host networking (no Docker bridge overhead)
docker run -d --network host ...

# Resource allocation
docker run -d \
  --cpus="2.0" \
  --memory="512M" \
  ...
```

### Optimize for High Query Load

```bash
# Increase resource limits
docker run -d \
  --cpus="4.0" \
  --memory="1G" \
  ...

# Run multiple instances behind load balancer
docker run -d --name dns1 -p 53053:53053/udp ...
docker run -d --name dns2 -p 53054:53053/udp ...

# Use Anycast DNS for geographic distribution
```

### Optimize for Many Backends

```bash
# Longer health check intervals
-e DNS_TEST_MIN_INTERVAL="60" \
-e DNS_TEST_TIMEOUT="5"

# Results in less frequent zone updates
# Higher TTLs, more caching
```

## 5. Debugging Techniques

### Enable Debug Logging

```bash
# Docker
docker run -d -e DNS_LOG_LEVEL="debug" ...

# Direct installation
a-healthy-dns --log-level debug ...
```

### Interactive Debugging Container

```bash
# Start with shell access
docker run -it --entrypoint sh indisoluble/a-healthy-dns

# Inspect filesystem
ls -la /app
which a-healthy-dns

# Check installed package location and Python environment
python3 -c "import indisoluble.a_healthy_dns.main as m; print(m.__file__)"
python3 --version
pip list
```

### Network Debugging

```bash
# Inspect the container network from the host
docker inspect a-healthy-dns | jq '.[0].NetworkSettings'
docker port a-healthy-dns

# Packet capture
sudo tcpdump -i any -n port 53053 -w dns-traffic.pcap

# Test health check connectivity from the runtime image using Python
docker exec a-healthy-dns python3 -c "import socket; socket.create_connection(('192.168.1.100', 8080), 2).close(); print('ok')"
```

### Zone State Inspection

```bash
# View recent health checks
docker logs a-healthy-dns 2>&1 | grep "Checked IP" | tail -50

# Monitor zone updates in real-time
docker logs -f a-healthy-dns 2>&1 | grep "Updating zone"

# Check A record additions
docker logs a-healthy-dns 2>&1 | grep "Added A record"
```

## 6. Production Monitoring

### Key Metrics to Monitor

1. **Query rate** - Queries per second
2. **Response time** - DNS query latency
3. **Health check success rate** - Percentage of successful health checks
4. **Zone update frequency** - How often zone is recreated
5. **Memory usage** - Container memory consumption
6. **CPU usage** - Container CPU usage

### Monitoring Commands

```bash
# Query rate (approximate)
docker logs a-healthy-dns 2>&1 | grep "Answered query" | wc -l

# Health check results
docker logs a-healthy-dns 2>&1 | grep "Checked IP" | \
  grep -c "True to True"  # Successful checks

# Zone updates per hour
docker logs a-healthy-dns --since 1h 2>&1 | grep -c "Updating zone"

# Resource usage
docker stats --no-stream a-healthy-dns
```

### Health Check Endpoint (Not Built-In)

A Healthy DNS does not provide a built-in health endpoint. To monitor health:

1. Query DNS and verify expected response
2. Parse logs for health check results
3. Monitor process/container liveness

**Example monitoring script:**
```bash
#!/bin/bash
# Check if DNS server is responding
dig @localhost -p 53053 www.example.local +short +timeout=2 > /dev/null
if [ $? -eq 0 ]; then
  echo "DNS server is healthy"
  exit 0
else
  echo "DNS server is unhealthy"
  exit 1
fi
```

## 7. Getting Help

### Information to Collect

When reporting issues, include:

1. **Version:** Docker image tag or git commit
2. **Configuration:** Environment variables or CLI arguments (redact sensitive data)
3. **Logs:** Last 100 lines with debug level enabled
4. **System:** OS, Docker version, network setup
5. **Reproduction:** Steps to reproduce the issue

### Log Collection

```bash
# Docker logs (last 200 lines, debug level)
docker logs --tail 200 a-healthy-dns 2>&1 > dns-logs.txt

# Configuration
docker inspect a-healthy-dns > dns-config.json

# System info
docker version > system-info.txt
uname -a >> system-info.txt
```

### Community Resources

- **GitHub Issues:** [github.com/indisoluble/a-healthy-dns/issues](https://github.com/indisoluble/a-healthy-dns/issues)
- **Documentation:** [`docs/table-of-contents.md`](table-of-contents.md) — full index of all guides
- **Source Code:** [`indisoluble/a_healthy_dns/`](../indisoluble/a_healthy_dns/) — implementation details
