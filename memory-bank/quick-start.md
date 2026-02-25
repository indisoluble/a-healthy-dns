# Quick Start

## Run the Server (CLI)

```bash
# From venv
source venv/bin/activate

a-healthy-dns \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["192.168.1.100","192.168.1.101"],"health_port":8080}}' \
  --ns '["ns1.example.com"]' \
  --port 53053
```

## Run the Server (Docker)

```bash
docker build -t a-healthy-dns .
docker run -p 53053:53/udp \
  -e DNS_HOSTED_ZONE=example.com \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  a-healthy-dns
```

## Run Tests

```bash
source venv/bin/activate
./venv/bin/pip install pytest
./venv/bin/python -m pytest --tb=short -q
# 236 passed
```

## Test a DNS Query

```bash
dig @127.0.0.1 -p 53053 www.example.com A
```

## Key CLI Arguments

| Arg | Required | Default | Example |
|-----|----------|---------|---------|
| `--hosted-zone` | Yes | — | `example.com` |
| `--zone-resolutions` | Yes | — | `'{"www":{"ips":["1.2.3.4"],"health_port":80}}'` |
| `--ns` | Yes | — | `'["ns1.example.com"]'` |
| `--port` | No | `53053` | `5353` |
| `--log-level` | No | `info` | `debug` |
| `--alias-zones` | No | `[]` | `'["alias.com"]'` |
| `--test-min-interval` | No | `30` | `60` |
| `--test-timeout` | No | `2` | `5` |
| `--priv-key-path` | No | — | `/path/to/key.pem` |
| `--priv-key-alg` | No | `RSASHA256` | `ECDSAP256SHA256` |

## Common Development Patterns

### Adding a new tool function
1. Create `indisoluble/a_healthy_dns/tools/new_tool.py` — pure function, no classes.
2. Create `tests/indisoluble/a_healthy_dns/tools/test_new_tool.py` — parametrized tests.
3. Import from the calling module.

### Adding a new record type
1. Create factory in `indisoluble/a_healthy_dns/records/new_record.py`.
2. Add TTL calculation to `records/time.py` if needed.
3. Wire into `dns_server_zone_updater.py:_add_records_to_zone()`.
4. Create matching test file.

### Modifying health check logic
- Health check: `tools/can_create_connection.py`
- Record refresh: `dns_server_zone_updater.py:_refresh_a_record()`
- A record filtering: `records/a_record.py:make_a_record()` (only healthy IPs included)

## Session Data
- **Python**: 3.13.12 (venv at `./venv`)
- **Version**: 0.1.26
- **Branch**: `agent-zero` (1 ahead of `master`)
- **Tests**: 236 passing
