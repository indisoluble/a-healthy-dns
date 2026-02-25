# System Patterns

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  main.py  (CLI entry point)                                 │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │ argparse config   │→│ DnsServerConfigFactory           │ │
│  │ signal handling   │  │ (dns_server_config_factory.py)   │ │
│  └──────────────────┘  └───────────────┬──────────────────┘ │
│                                        │ DnsServerConfig     │
│  ┌─────────────────────────────────────▼──────────────────┐ │
│  │ DnsServerZoneUpdaterThreated                           │ │
│  │ (dns_server_zone_updater_threated.py)                  │ │
│  │  ┌─────────────────────────────────────────────────┐   │ │
│  │  │ DnsServerZoneUpdater                            │   │ │
│  │  │ (dns_server_zone_updater.py)                    │   │ │
│  │  │  • health checks (TCP connect)                  │   │ │
│  │  │  • zone recreation (clear → add → sign)         │   │ │
│  │  │  • RRSIG resign scheduling                      │   │ │
│  │  └─────────────────────────────────────────────────┘   │ │
│  └──────────────────────────┬─────────────────────────────┘ │
│                             │ dns.versioned.Zone             │
│  ┌──────────────────────────▼─────────────────────────────┐ │
│  │ socketserver.UDPServer + DnsServerUdpHandler           │ │
│  │ (dns_server_udp_handler.py)                            │ │
│  │  • parse query → lookup zone → authoritative response  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Core Patterns

### 1. Factory Pattern — Configuration (`dns_server_config_factory.py`)
- `make_config(args) → Optional[DnsServerConfig]`
- Validates and transforms raw CLI args into a typed `DnsServerConfig` (NamedTuple).
- Each sub-component (`_make_zone_origins`, `_make_a_records`, `_make_name_servers`, `_make_private_key`) returns `Optional[T]`, propagating `None` on any validation error.
- Logging on every validation failure — no exceptions thrown to caller; `None` = failure.

### 2. Immutable Value Objects
- **`AHealthyIp`**: Validates IP + port on construction (via tools). Returns *new* instance from `updated_status()` when health changes. Implements `__eq__` and `__hash__` on `(ip, port, is_healthy)`.
- **`AHealthyRecord`**: Holds `dns.name.Name` + `FrozenSet[AHealthyIp]`. Returns *new* instance from `updated_ips()`. Equality/hash based on subdomain only.
- **`ZoneOrigins`**: Holds primary origin + sorted list of all origins (primary + aliases). `relativize(name)` matches the most-specific origin first.
- **`DnsServerConfig`**, **`ExtendedPrivateKey`**: `NamedTuple`s — fully immutable.

### 3. Generator/Iterator Pattern — SOA & DNSSEC (`soa_record.py`, `dnssec.py`)
- `iter_soa_record()` → infinite iterator of SOA `Rdataset` with auto-incrementing serial (via `uint32_current_time()`).
- `iter_rrsig_key()` → infinite iterator of `ExtendedRRSigKey` with calculated inception/expiration/resign times.
- Callers just `next()` to get the current record; timing logic is encapsulated in the generator.

### 4. Zone Lifecycle — Clear→Add→Sign (`dns_server_zone_updater.py`)
- `_recreate_zone()`: Acquires a `zone.writer()` transaction, then:
  1. `_clear_zone(txn)` — deletes all nodes.
  2. `_add_records_to_zone(txn)` — adds NS, SOA (via iterator), and A records (only healthy IPs).
  3. `_sign_zone(txn)` — if DNSSEC is configured, signs with next RRSIG key.
- Zone uses `dns.versioned.Zone` for thread-safe reader/writer access.

### 5. Health Check Loop (`dns_server_zone_updater.py` + `_threated.py`)
- Background thread in `DnsServerZoneUpdaterThreated` calls `update()` in a loop.
- `update(check_ips=True)` → `_refresh_a_recs()` → for each `AHealthyRecord`, for each `AHealthyIp`, calls `can_create_connection(ip, port, timeout)`.
- If any IP status changes OR RRSIG is near expiry → `_recreate_zone()`.
- `should_abort` callback checked between each IP test for graceful shutdown.
- `_stop_event` (threading.Event) coordinates shutdown: `stop()` sets event, `join()` waits.

### 6. Timing Hierarchy (`records/time.py`)
- All TTLs derived from `max_interval` (the effective health-check period):
  - `A TTL = 2 × max_interval`
  - `NS TTL = 30 × A TTL`
  - `SOA TTL = NS TTL`
  - `DNSKEY TTL = 10 × A TTL`
  - `SOA refresh = DNSKEY TTL`
  - `SOA retry = A TTL`
  - `SOA expire = 5 × SOA retry`
  - `SOA min TTL = A TTL`
  - `RRSIG resign = SOA refresh`
  - `RRSIG expiration = 2×SOA refresh + SOA expire + SOA retry`
- `max_interval = max(min_interval, sum(len(ips)×timeout + delta) for each record)` ensures the health check loop has enough time.

### 7. Request Handling (`dns_server_udp_handler.py`)
- Extends `socketserver.BaseRequestHandler`.
- Parses wire → `dns.message`, creates response with `AA` flag.
- `_update_response()` relativizes the query name against zone origins, looks up the node/rdataset in the versioned zone reader, appends matching RRsets to the response answer section.
- Returns `NXDOMAIN` for unknown subdomains, `NOERROR` with empty answer for known subdomains without the queried record type.

### 8. Signal Handling (`main.py`)
- `SIGINT` and `SIGTERM` trigger `server.shutdown()` in a new thread (to avoid deadlock with `serve_forever()`).
- After server stops, zone updater is stopped via `zone_updater.stop()`.

## Module Dependency Graph

```
main.py
├── dns_server_config_factory.py
│   ├── records/a_healthy_record.py
│   │   └── records/a_healthy_ip.py
│   │       ├── tools/is_valid_ip.py
│   │       ├── tools/is_valid_port.py
│   │       └── tools/normalize_ip.py
│   ├── records/zone_origins.py
│   │   └── tools/is_valid_subdomain.py
│   └── tools/is_valid_subdomain.py
├── dns_server_udp_handler.py
│   └── records/zone_origins.py
├── dns_server_zone_updater_threated.py
│   └── dns_server_zone_updater.py
│       ├── records/a_record.py
│       │   ├── records/a_healthy_record.py
│       │   └── records/time.py
│       ├── records/dnssec.py
│       │   └── records/time.py
│       ├── records/ns_record.py
│       │   └── records/time.py
│       ├── records/soa_record.py
│       │   ├── records/time.py
│       │   └── tools/uint32_current_time.py
│       └── tools/can_create_connection.py
└── (stdlib: argparse, signal, socketserver, threading)
```

## Data Flow

```
CLI args → make_config() → DnsServerConfig
                                │
                                ▼
                   DnsServerZoneUpdaterThreated
                                │
                   ┌────────────┴────────────┐
                   │                         │
            update loop                dns.versioned.Zone ◄── shared ──► UDPServer
            (background thread)              │                          (main thread)
                   │                         │
         for each AHealthyRecord:            │
           for each AHealthyIp:              │
             can_create_connection()          │
                   │                         │
         if changes or RRSIG expiring:       │
           _recreate_zone() ─────────────────┘
             clear → add NS/SOA/A → sign
```
