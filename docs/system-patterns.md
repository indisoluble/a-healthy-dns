# System Patterns

Architecture patterns and conventions for **A Healthy DNS**.

---

## 1. High-level architecture

The system is built around two independent, concurrently-running concerns separated from the start of `main()`:

```
┌────────────────────────────────────────────────────────────────┐
│  main.py (_main)                                               │
│                                                                │
│  ┌──────────────────────────────┐                              │
│  │ DnsServerZoneUpdaterThreated │  ← background daemon thread  │
│  │  ┌──────────────────────┐    │                              │
│  │  │ DnsServerZoneUpdater │    │  ← health check + zone write │
│  │  └──────────────────────┘    │                              │
│  └──────────────┬───────────────┘                              │
│                 │ shared dns.versioned.Zone (thread-safe)      │
│  ┌──────────────▼──────────────┐                               │
│  │  socketserver.UDPServer     │  ← main (serving) thread      │
│  │  ┌──────────────────────┐   │                               │
│  │  │ DnsServerUdpHandler  │   │  ← read-only zone queries     │
│  │  └──────────────────────┘   │                               │
│  └─────────────────────────────┘                               │
└────────────────────────────────────────────────────────────────┘
```

Key properties:
- The **zone updater thread** holds the only write path to the zone.
- The **UDP handler thread** performs only reads via `zone.reader()`.
- Concurrency safety is delegated to `dns.versioned.Zone`, which provides a versioned reader/writer API.
- The two concerns share **no mutable state** other than the zone object itself.

---

## 2. Layered module structure

Modules are organised in strict top-down dependency order. Higher layers depend on lower layers; lower layers never import higher layers.

```
Layer 0 – Entry-point
  indisoluble/a_healthy_dns/main.py

Layer 1 – Server orchestration
  dns_server_zone_updater_threated.py   (threading wrapper)
  dns_server_udp_handler.py             (UDP query handler)

Layer 2 – Domain logic
  dns_server_config_factory.py          (config validation + assembly)
  dns_server_zone_updater.py            (health check loop + zone writes)

Layer 3 – Records
  records/a_healthy_ip.py               (IP + health status value object)
  records/a_healthy_record.py           (subdomain → IPs aggregate)
  records/a_record.py                   (DNS A rdataset factory)
  records/ns_record.py                  (DNS NS rdataset factory)
  records/soa_record.py                 (DNS SOA rdataset factory)
  records/dnssec.py                     (RRSIG key + timing)
  records/zone_origins.py               (primary + alias zone set)
  records/time.py                       (TTL and signature timing calculations)

Layer 4 – Tools (pure utilities, no DNS dependencies)
  tools/can_create_connection.py        (TCP health check)
  tools/is_valid_ip.py
  tools/is_valid_port.py
  tools/is_valid_subdomain.py
  tools/normalize_ip.py
  tools/uint32_current_time.py
```

**Convention:** when adding code, place it at the lowest layer it belongs to. Never move a dependency upward.

---

## 3. Configuration as a validated NamedTuple

All validated runtime configuration is assembled once at startup by `dns_server_config_factory.make_config()` and expressed as an immutable `DnsServerConfig` `NamedTuple`.

```python
# dns_server_config_factory.py
class DnsServerConfig(NamedTuple):
    zone_origins: ZoneOrigins
    name_servers: FrozenSet[str]
    a_records: FrozenSet[AHealthyRecord]
    ext_private_key: Optional[ExtendedPrivateKey]
```

The factory validates every field (zone names, IP addresses, ports, DNSSEC algorithm) before constructing the config. If any field is invalid the factory logs the error and returns `None`; `main()` exits without starting a server.

**Convention:** all new configuration fields must be added to `DnsServerConfig` and validated inside `dns_server_config_factory.py`. No ad-hoc parsing elsewhere.

---

## 4. Immutable value objects for domain state

Health state is propagated through **immutable value objects** rather than mutation:

- `AHealthyIp.updated_status(is_healthy)` returns a **new** `AHealthyIp` instance if the status changed, or `self` when unchanged.
- `AHealthyRecord.updated_ips(updated_ips)` returns a **new** `AHealthyRecord` if any IP changed, or `self` when unchanged.

This makes change detection trivially safe: `object is new_object` indicates a change occurred.

**Convention:** domain state objects must remain immutable. Produce updated copies instead of mutating in place.

---

## 5. Zone update cycle

The zone is never partially updated. Each refresh cycle follows a write-all-or-nothing approach:

```
_recreate_zone()
  └─ zone.writer() (transaction)
       ├─ _clear_zone()         — delete all existing nodes
       ├─ _add_records_to_zone()
       │    ├─ NS record (apex)
       │    ├─ SOA record (apex)
       │    └─ A records (one per healthy subdomain; omitted if all IPs unhealthy)
       └─ _sign_zone()          — DNSSEC RRSIG (if key is configured)
```

The `dns.versioned.Zone` writer is used inside a `with` block; the transaction is committed atomically on exit and rolled back on exception.

**Convention:** all zone modifications must go through a single writer transaction. Partial writes are not allowed.

---

## 6. Interval calculation pattern

TTLs and timing values are derived consistently from a single source of truth: the **effective max interval**, calculated in `dns_server_zone_updater.py:_calculate_max_interval()`:

```
max_interval = max(min_interval, sum(per-IP connection_timeout + per-record delta))
```

All record TTLs are then calculated as multiples of `max_interval` by functions in `records/time.py`:

| Record | Formula |
|---|---|
| A TTL | `max_interval × 2` |
| NS TTL | `A TTL × 30` |
| SOA TTL | `= NS TTL` |
| SOA refresh | `= DNSKEY TTL` |
| SOA retry | `= A TTL` |
| SOA expire | `SOA retry × 5` |
| SOA min TTL | `= A TTL` |
| DNSKEY TTL | (see `records/time.py`) |
| RRSIG lifetime | (see `records/time.py`) |

**Convention:** do not hardcode TTL values. All timing must be derived via functions in `records/time.py`, taking `max_interval` as input.

---

## 7. Multi-domain support via ZoneOrigins

`records/zone_origins.ZoneOrigins` holds the primary zone name plus any alias zones. The `DnsServerUdpHandler` relativizes every incoming query name against all known origins.

```python
relative_name = zone_origins.relativize(query_name)
# returns None when query_name matches no known origin
```

Origins are sorted by descending specificity (length) to ensure the most specific zone matches first. The zone itself is always stored under the primary origin; alias zones are lookup aliases only.

**Convention:** alias zones must never appear as a separate `dns.versioned.Zone`. They are handled purely at query-relativization time in `ZoneOrigins.relativize()`.

---

## 8. DNSSEC as an optional, isolated concern

DNSSEC is an additive, opt-in behaviour controlled by the presence of `DnsServerConfig.ext_private_key`:

- `None` → no signing, no RRSIG records, standard A/NS/SOA responses.
- set → `_sign_zone()` is called at the end of each zone-recreation transaction.

RRSIG key rotation timing is managed by `records/dnssec.iter_rrsig_key()`, a stateful generator that yields a new `ExtendedRRSigKey` each time signing is invoked. The zone updater tracks `resign` time and forces a zone recreation before the current signature expires.

**Convention:** DNSSEC logic must remain isolated to `records/dnssec.py` and the `_sign_zone()` call in `DnsServerZoneUpdater`. Do not spread DNSSEC awareness into other layers.

---

## 9. Graceful shutdown pattern

`main()` registers `SIGINT` and `SIGTERM` handlers that:
1. Call `server.shutdown()` in a new thread (avoids deadlock with `serve_forever()`).
2. After `UDPServer` exits its loop, call `zone_updater.stop()`.

`stop()` sets a `threading.Event` to signal the background loop, then `join()`s the thread with a timeout.

**Convention:** any new background thread or resource must be cleanly stopped in the `main()` shutdown sequence following the same `Event + join` pattern.

---

## 10. Tooling conventions

- **Pure utility functions** belong in `tools/`. They must have no imports from `indisoluble.a_healthy_dns` (no circular dependencies).
- **Validation functions** (e.g. `is_valid_ip`, `is_valid_subdomain`) return `(bool, Optional[str])` — success flag and an error message.
- **Record factories** (e.g. `make_a_record`, `make_ns_record`) are module-level functions, not methods. They take scalar inputs and return `dns.rdataset.Rdataset` (or `None`).
- **Iterators as stateful generators** are used for sequences requiring internal state (SOA serial increments, RRSIG key rotation) — see `records/soa_record.iter_soa_record()` and `records/dnssec.iter_rrsig_key()`.
