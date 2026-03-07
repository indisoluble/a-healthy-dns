# System Patterns

## High-level architecture

A Healthy DNS is a single-process, two-thread system:

1. **Main thread** — runs a `socketserver.UDPServer` that handles DNS queries.
2. **Background thread** (`ZoneUpdaterThread`) — performs periodic TCP health checks and rebuilds the DNS zone.

Both threads share a single `dns.versioned.Zone` which provides transactional read/write access, ensuring query handling never sees a half-built zone.

```
┌─────────────────────────────────────────────────────┐
│  CLI args / env vars                                │
│         │                                           │
│         ▼                                           │
│  make_config()  ──►  DnsServerConfig (immutable)    │
│         │                                           │
│    ┌────┴──────────────┐                            │
│    │                   │                            │
│    ▼                   ▼                            │
│  UDPServer          ZoneUpdaterThreated             │
│  (main thread)      (background thread)             │
│    │                   │                            │
│    │   ┌───────────────┘                            │
│    │   │                                            │
│    ▼   ▼                                            │
│  dns.versioned.Zone  (shared, transactional)        │
└─────────────────────────────────────────────────────┘
```

## Data flow

### Configuration flow

```
CLI args  ──►  _make_arg_parser()  ──►  make_config()
                                            │
                  ┌─────────────────────────┤
                  │           │             │           │
                  ▼           ▼             ▼           ▼
            ZoneOrigins   FrozenSet     FrozenSet   ExtendedPrivateKey
            (primary +    [AHealthy     [str]       (optional DNSSEC)
             aliases)      Record]     name_servers
                  │           │             │           │
                  └─────────────────────────┘
                              │
                              ▼
                      DnsServerConfig (NamedTuple, immutable)
```

Source: `dns_server_config_factory.py:27-35` — `DnsServerConfig` NamedTuple definition.

### Health-check and zone-update cycle

```
ZoneUpdaterThreated._update_zone_loop()
    │
    ▼  every min_interval seconds
DnsServerZoneUpdater.update(check_ips=True)
    │
    ├──► _refresh_a_recs()
    │       for each AHealthyRecord:
    │         for each AHealthyIp:
    │           can_create_connection(ip, health_port, timeout)
    │             ──► TCP 3-way handshake (socket.create_connection)
    │           AHealthyIp.updated_status(is_healthy)
    │       detect changes (old healthy_ips ≠ new healthy_ips)
    │
    ├──► _is_zone_sign_near_to_expire()
    │       check if current time ≥ rrsig resign time
    │
    └──► if changes OR DNSSEC near expiry OR first run:
            _recreate_zone()
              zone.writer() transaction:
                1. _clear_zone()       — delete all nodes
                2. _add_records_to_zone() — NS + SOA + healthy A records
                3. _sign_zone()        — DNSSEC sign (if enabled)
```

Source: `dns_server_zone_updater.py:141-167` — `_recreate_zone()` and `_recreate_zone_after_refresh()`.

### Query handling

```
UDP packet  ──►  DnsServerUdpHandler.handle()
                   │
                   ▼  dns.message.from_wire()
                 parse query
                   │
                   ▼  _update_response()
                 zone_origins.relativize(query_name)
                   │
                   ├── None → NXDOMAIN (unknown zone)
                   │
                   ▼  zone.reader() transaction
                 txn.get_node(relative_name)
                   │
                   ├── None → NXDOMAIN (unknown subdomain)
                   │
                   ▼  node.get_rdataset(rdclass, query_type)
                   │
                   ├── None → NOERROR (subdomain exists, no matching type)
                   │
                   ▼  build RRset → append to response.answer
                   │
                   ▼  dns.message.to_wire() → sendto()
```

Source: `dns_server_udp_handler.py:23-60` — `_update_response()` function.

## Key design patterns

### Immutable configuration

All configuration data uses immutable types — `NamedTuple` for structured data, `FrozenSet` for collections. This makes configuration thread-safe without locks.

- `DnsServerConfig` — `NamedTuple` (`dns_server_config_factory.py:27`)
- `ExtendedPrivateKey` — `NamedTuple` (`dns_server_config_factory.py:23`)
- `AHealthyRecord.healthy_ips` — `FrozenSet[AHealthyIp]` (`a_healthy_record.py:34`)
- Name servers — `FrozenSet[str]` (`dns_server_config_factory.py:32`)

### Identity-based change detection

Value objects return `self` when an update produces no change, enabling cheap identity comparison to detect actual changes:

- `AHealthyIp.updated_status()` — returns `self` if `is_healthy` unchanged (`a_healthy_ip.py:52-55`).
- `AHealthyRecord.updated_ips()` — returns `self` if IP set unchanged (`a_healthy_record.py:37-39`).

The zone updater uses this to decide whether zone recreation is needed (`dns_server_zone_updater.py:220-225`).

### Transactional zone access

The DNS zone (`dns.versioned.Zone`) provides versioned transactions:

- **Writer** (`zone.writer()`) — exclusive access for zone rebuilds. Used in `_recreate_zone()` to atomically clear, populate, and sign.
- **Reader** (`zone.reader()`) — concurrent read access for query handling. Used in `_update_response()` to look up records.

This ensures the main thread never reads a partially rebuilt zone.

### Zone-origin normalization

`ZoneOrigins` maps multiple domain names (primary + aliases) to a single zone. The `relativize()` method matches an incoming absolute query name to the most specific zone origin, returning a relative name for zone lookup.

Origins are sorted by specificity (longest first) to ensure correct matching (`zone_origins.py:36-39`).

### Partial application for dependency injection

External dependencies (network timeout, TTL intervals) are bound via `functools.partial` at initialization time, producing zero-argument or single-argument callables used throughout the update cycle:

- `self._can_create_connection = partial(can_create_connection, timeout=...)` (`dns_server_zone_updater.py:104`)
- `self._make_a_record = partial(make_a_record, max_interval)` (`dns_server_zone_updater.py:102`)

### Cooperative shutdown

The background thread uses `threading.Event` for cooperative abort:

- `_stop_event.set()` signals the thread to stop (`dns_server_zone_updater_threated.py:81`).
- `should_abort` callback is checked between each IP health check, allowing mid-cycle interruption (`dns_server_zone_updater.py:173`).
- `_stop_event.wait(sleep_time)` replaces `time.sleep()` so the thread wakes immediately on stop (`dns_server_zone_updater_threated.py:55`).

### Generator-based DNSSEC key management

DNSSEC signing keys are produced by `iter_rrsig_key()`, an infinite generator that yields fresh `ExtendedRRSigKey` instances with pre-calculated inception, expiration, and resign times. The zone updater simply calls `next()` when re-signing is needed (`dns_server_zone_updater.py:135`).

## TTL strategy

All TTL values derive from `max_interval` (the effective health-check cycle duration), defined in `records/time.py`:

| Record type | TTL formula | Rationale |
|-------------|-------------|-----------|
| A record | `2 × max_interval` | Clients re-query before health state is two cycles stale. |
| NS record | `30 × A TTL` | Nameserver info changes rarely; ~15 min at default settings. |
| SOA record | same as NS TTL | Contains primary NS; same stability expectation. |
| DNSKEY | `10 × A TTL` | Allows ~5 min for manual key rotation and redeployment. |
| RRSIG expiration | `2 × SOA_refresh + SOA_expire + SOA_retry` | Survives worst-case slave refresh failures. |

`max_interval` itself is calculated as the greater of `min_interval` (CLI arg, default 30s) and the sum of all IP timeouts plus per-record overhead (`dns_server_zone_updater.py:46-55`).

## Module structure

```
indisoluble/a_healthy_dns/
├── main.py                              # CLI entry point, server orchestration, signal handling
├── dns_server_config_factory.py         # Config validation, DnsServerConfig construction
├── dns_server_udp_handler.py            # UDP query handler (main thread)
├── dns_server_zone_updater.py           # Zone updater with health checks (core logic)
├── dns_server_zone_updater_threated.py  # Threaded wrapper for background execution
├── records/
│   ├── a_healthy_ip.py                  # IP + port + health status value object
│   ├── a_healthy_record.py              # Subdomain + set of AHealthyIp
│   ├── a_record.py                      # Factory: AHealthyRecord → dns.rdataset (filtered)
│   ├── dnssec.py                        # DNSSEC key generator (RRSigKey, ExtendedRRSigKey)
│   ├── ns_record.py                     # NS record factory
│   ├── soa_record.py                    # SOA record generator (dynamic serial)
│   ├── time.py                          # TTL and DNSSEC timing calculations
│   └── zone_origins.py                  # Primary + alias zone origin matching
└── tools/
    ├── can_create_connection.py          # TCP health check (socket.create_connection)
    ├── is_valid_ip.py                   # IPv4 validation → (bool, error)
    ├── is_valid_port.py                 # Port validation → (bool, error)
    ├── is_valid_subdomain.py            # DNS label validation → (bool, error)
    ├── normalize_ip.py                  # Strip leading zeros from IP octets
    └── uint32_current_time.py           # SOA serial from epoch time
```

### Layer responsibilities

| Layer | Modules | Responsibility |
|-------|---------|----------------|
| **Entry** | `main.py` | CLI parsing, wiring, signal handling, server lifecycle. |
| **Config** | `dns_server_config_factory.py` | Validates CLI args, constructs immutable config. |
| **Serving** | `dns_server_udp_handler.py` | Reads zone transactionally, builds DNS responses. |
| **Updating** | `dns_server_zone_updater.py`, `dns_server_zone_updater_threated.py` | Health checks, zone rebuild, DNSSEC signing, threading. |
| **Records** | `records/*` | DNS record construction, TTL math, DNSSEC key generation. |
| **Tools** | `tools/*` | Pure validation/utility functions with no DNS domain knowledge. |
