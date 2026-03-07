# System Patterns

## Component map

```
main.py
├── _make_arg_parser()          — CLI / env-var argument definition
├── make_config()               — DnsServerConfig factory (dns_server_config_factory.py)
├── DnsServerZoneUpdaterThreated — background health-check + zone rebuild (zone_updater_threated.py)
│   └── DnsServerZoneUpdater    — core update logic (dns_server_zone_updater.py)
│       ├── AHealthyRecord      — subdomain + set of AHealthyIp   (records/a_healthy_record.py)
│       │   └── AHealthyIp      — IP + port + health status         (records/a_healthy_ip.py)
│       ├── make_a_record()     — A rdataset factory                 (records/a_record.py)
│       ├── make_ns_record()    — NS rdataset factory                (records/ns_record.py)
│       ├── iter_soa_record()   — SOA rdataset generator             (records/soa_record.py)
│       └── iter_rrsig_key()    — DNSSEC key+timing generator        (records/dnssec.py)
└── DnsServerUdpHandler         — UDP query handler                  (dns_server_udp_handler.py)
    └── ZoneOrigins             — primary + alias name normalization  (records/zone_origins.py)
```

Supporting tools (all pure functions, no I/O side effects except `can_create_connection`):

| Module | Responsibility |
|---|---|
| `tools/can_create_connection.py` | TCP connectivity probe |
| `tools/is_valid_ip.py` | IP address validation |
| `tools/is_valid_port.py` | Port number validation |
| `tools/is_valid_subdomain.py` | Domain name validation |
| `tools/normalize_ip.py` | IP address normalization |
| `tools/uint32_current_time.py` | SOA serial number source |
| `records/time.py` | All TTL and DNSSEC timing calculations |

---

## Startup sequence

```
main()
  1. Parse args → dict
  2. make_config(args) → DnsServerConfig (or exit on validation failure)
  3. DnsServerZoneUpdaterThreated.start()
       └─ spawns background thread running _update_zone_loop()
  4. socketserver.UDPServer started on configured port
  5. server.zone and server.zone_origins injected into server instance
  6. Register SIGINT / SIGTERM handlers → server.shutdown() on separate thread
  7. server.serve_forever()
  8. On shutdown: zone_updater.stop() → sets stop_event, joins thread
```

---

## Health-check loop pattern

`DnsServerZoneUpdaterThreated._update_zone_loop()` runs continuously on a background thread:

```
while not stopped:
    t0 = now()
    updater.update(should_abort=lambda: stopped)
    elapsed = now() - t0
    sleep(max(0, min_interval - elapsed))
```

Inside `DnsServerZoneUpdater.update()`:

1. **Probe phase** — for each `AHealthyRecord`, for each `AHealthyIp`:
   - call `can_create_connection(ip, port, timeout)` (TCP socket connect)
   - produce a new `AHealthyIp` via `updated_status(is_healthy)` (immutable update)
   - check `should_abort()` before each probe; if true, discard results and return
2. **Change detection** — compare old vs new `healthy_ips` sets; set `CHANGES` flag if different
3. **Resign check** — if DNSSEC is enabled, check whether signature `resign` time has passed
4. **Zone rebuild** — triggered when: `CHANGES`, resign needed, or zone not yet built once
   - Writer transaction: clear zone → add NS + SOA + A records → sign (if DNSSEC)

Key invariant: the zone is always rebuilt atomically inside a single `dns.versioned.Zone` writer transaction. Readers never see a partial zone.

---

## Zone rebuild pattern

`DnsServerZoneUpdater._recreate_zone()`:

```python
with self._zone.writer() as txn:
    _clear_zone(txn)        # delete all nodes
    _add_records_to_zone(txn)   # NS, SOA, A records
    _sign_zone(txn)             # RRSIG + DNSKEY (if enabled)
```

- `dns.versioned.Zone` from dnspython provides versioned, reader/writer-locked access.
- The zone object is shared between the updater thread and the UDP handler thread via a reference stored on the `UDPServer` instance (`server.zone`).
- No additional locking is needed outside the zone's own transaction model.

---

## Immutable-update pattern

Health state is tracked with immutable value objects:

- `AHealthyIp.updated_status(is_healthy)` — returns `self` if unchanged, otherwise a new `AHealthyIp`.
- `AHealthyRecord.updated_ips(updated_ips)` — returns `self` if unchanged, otherwise a new `AHealthyRecord`.

This makes change detection trivial (identity comparison) and avoids shared mutable state between iterations.

---

## Multi-domain (alias zone) pattern

`ZoneOrigins` holds a primary zone and zero or more alias zones. On each DNS query:

```python
relative_name = zone_origins.relativize(query_name)
```

`relativize` finds the longest matching origin (most specific wins, deterministic order) and strips it from the query name to produce the relative name used for zone lookup. A single `dns.versioned.Zone` keyed on the primary origin serves all aliases — no data is duplicated.

Relevant files:
- `records/zone_origins.py:ZoneOrigins` — origin set + relativize logic
- `dns_server_udp_handler.py:_update_response` — calls `relativize` before every zone lookup

---

## DNSSEC signing pattern

DNSSEC is optional. When `--priv-key-path` is provided:

1. `make_config()` loads the PEM key and builds an `ExtendedPrivateKey(private_key, dnskey)`.
2. `DnsServerZoneUpdater.__init__` creates a `RRSigAction` with `resign` set to epoch 0 (triggers immediate sign on first build) and an `iter_rrsig_key()` generator.
3. `iter_rrsig_key()` yields `ExtendedRRSigKey` values containing a `RRSigKey` (keys, TTLs, inception, expiration) and the `resign` timestamp.
4. On each zone rebuild, `_sign_zone()` calls `dns.dnssec.sign_zone()` using the current key, then advances `resign` to the next rotation time.
5. The updater checks `_is_zone_sign_near_to_expire()` on every health-check cycle; if the resign time has passed, a zone rebuild is forced even if A records are unchanged.

TTL and timing values are derived from `max_interval` using the functions in `records/time.py`:
- A TTL = `max_interval * 2`
- NS TTL = A TTL × 30
- DNSKEY TTL, RRSIG lifetime, resign time — all derived from `max_interval`

---

## Interval / timing calculation pattern

`_calculate_max_interval()` in `dns_server_zone_updater.py` derives a realistic ceiling for one full health-check cycle:

```
max_interval = max(
    min_interval,
    sum over all records of (len(ips) * connection_timeout + delta_per_record)
)
```

`delta_per_record` is `DELTA_PER_RECORD_MANAGEMENT` (1 s) + `_DELTA_PER_RECORD_SIGN` (2 s, only when DNSSEC).  
All TTL and timing values in the zone are derived from `max_interval`, ensuring they scale automatically with the number of backends and health-check parameters.

---

## UDP query handler pattern

`DnsServerUdpHandler` extends `socketserver.BaseRequestHandler`. On each UDP datagram:

1. Parse raw bytes → `dns.message.Message`.
2. Build response with `AA` (Authoritative Answer) flag set.
3. For each question: call `_update_response()` which:
   - relativizes the query name via `ZoneOrigins`
   - opens a zone reader transaction
   - looks up the node and rdataset
   - appends `RRset` to `response.answer`, or sets `NXDOMAIN` / `NOERROR` (no data)
4. Send response wire bytes back on the same UDP socket.

Queries for domains not matching any origin return `NXDOMAIN`. Queries for known subdomains with no matching record type return `NOERROR` with an empty answer section (correct RFC behaviour).

---

## Configuration factory pattern

`make_config(args)` in `dns_server_config_factory.py` is a pure validation + construction function:

- Returns `DnsServerConfig` (a `NamedTuple`) on success, `None` on any validation error.
- All validation errors are logged at `ERROR` level before returning `None`.
- `DnsServerConfig` fields: `zone_origins`, `name_servers`, `a_records`, `ext_private_key` (optional).
- All IPs start with `is_healthy=False`; the first health-check cycle populates real status.

---

## Dependency injection points

| Dependency | How injected |
|---|---|
| `can_create_connection` | `functools.partial` with `timeout` baked in; stored as `self._can_create_connection` in `DnsServerZoneUpdater` |
| `make_a_record` | `functools.partial` with `max_interval` baked in; stored as `self._make_a_record` |
| `zone` reference | Assigned to `server.zone` on the `UDPServer` instance after updater starts |
| `zone_origins` | Assigned to `server.zone_origins` on the `UDPServer` instance at startup |

External I/O (TCP socket, time, file reads) is isolated to:
- `tools/can_create_connection.py` — TCP socket
- `tools/uint32_current_time.py` — wall clock (SOA serial)
- `dns_server_config_factory._load_dnssec_private_key` — file read (startup only)
