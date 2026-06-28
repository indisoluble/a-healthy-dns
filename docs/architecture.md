# Architecture

Architecture patterns and conventions for **A Healthy DNS**.

This document is the canonical home for:
- current system structure,
- runtime and concurrency model,
- component boundaries and data flow,
- module and package dependency direction,
- integration points,
- and physical file-placement rules.

This document distinguishes between **design invariants** and **current patterns** using the terminology in [`AGENTS.md`](../AGENTS.md#3-terminology-and-task-classification). Design invariants must remain true unless the task explicitly changes the architecture contract. Current patterns should be followed by default for new and touched work, but may be improved through the scoped pattern-change process in [`docs/engineering-rules.md`](engineering-rules.md#changing-established-patterns).

It does not own requirements, major decision rationale, repository workflow, code-style conventions, parameter syntax, or protocol-level DNS behavior. Those topics live in [`docs/requirements.md`](requirements.md), [`docs/decisions.md`](decisions.md), [`docs/workflow.md`](workflow.md), [`docs/implementation-notes.md`](implementation-notes.md), [`docs/configuration-reference.md`](configuration-reference.md), and [`docs/RFC-conformance.md`](RFC-conformance.md).

---

## 1. High-level architecture

The runtime is built around two concerns that share one `dns.versioned.Zone`: a zone-updater component that owns all writes, and a UDP server that serves read-only queries. Startup creates the initial zone synchronously before serving begins; subsequent refreshes run in the background updater thread.

```
┌────────────────────────────────────────────────────────────────┐
│  main.py (_main)                                               │
│                                                                │
│  ┌──────────────────────────────┐                              │
│  │ DnsServerZoneUpdaterThreaded │  ← initial sync + daemon loop│
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
- The **zone updater component** holds the only write path to the zone. `DnsServerZoneUpdaterThreaded.start()` performs the first `initialize_zone()` synchronously, then starts the background refresh loop.
- The **UDP serving path** performs only reads via `zone.reader()`.
- Concurrency safety is delegated to `dns.versioned.Zone`, which provides a versioned reader/writer API.
- The two concerns share **no mutable state** other than the zone object itself.

---

## 2. Layered module structure

Modules are organised in strict top-down dependency order. Higher layers depend on lower layers; lower layers never import higher layers.

```
Layer 0 – Entry-point
  indisoluble/a_healthy_dns/main.py

Layer 1 – Server orchestration
  dns_server_zone_updater_threaded.py   (threading wrapper)
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
  records/dnssec.py                     (DNSSEC signing inputs + timing)
  records/zone_origins.py               (primary + alias zone set)
  records/time.py                       (TTL and signature timing calculations)

Layer 4 – Tools (low-level utilities, no DNS wire/message handling or record-construction dependencies)
  tools/can_create_connection.py        (TCP health check)
  tools/is_valid_ip.py
  tools/is_valid_port.py
  tools/is_valid_subdomain.py
  tools/normalize_ip.py
  tools/uint32_current_time.py
```

**Design invariant:** when adding code, place it at the lowest layer it belongs to. Never move a dependency upward unless the task explicitly changes the layer contract and updates this document, affected tests, and relevant decisions.

---

## 3. DNS configuration as a validated NamedTuple

Validated DNS zone configuration is assembled once at startup by `dns_server_config_factory.make_config()` and expressed as an immutable `DnsServerConfig` `NamedTuple`.

```python
# dns_server_config_factory.py
class DnsServerConfig(NamedTuple):
    zone_origins: ZoneOrigins
    primary_name_server: str
    name_servers: frozenset[str]
    a_records: frozenset[AHealthyRecord]
    ext_private_key: ExtendedPrivateKey | None
```

The factory validates every DNS configuration field (zone names, IP addresses, optional health-check ports, and DNSSEC algorithm) before constructing the config. If any field is invalid the factory logs the error and returns `None`; `main()` exits with a non-zero status without starting a server.

Operational process arguments that are not part of DNS zone state stay outside `DnsServerConfig`: listener port, log level, minimum update interval, and health-check timeout. The argument parser validates syntax and choices, the updater constructors validate positive timing values at the component boundary, and `socketserver.UDPServer` owns listener-port bind validity and availability.

The NS RRset is stored as a set because DNS RRset ordering is not meaningful. The SOA primary nameserver is stored separately as `primary_name_server`, derived from the first configured nameserver so SOA generation remains deterministic.

**Design invariant:** new DNS zone, record, alias, nameserver, or DNSSEC configuration fields must be added to `DnsServerConfig` and validated inside `dns_server_config_factory.py`. Operational process arguments remain in `main.py` unless they become shared domain configuration.

---

## 4. Immutable value objects for domain state

Externally, the product supports two record modes: health-checked entries and standard static entries. Internally, both modes share the same health-state model so the updater and zone writer can stay simple.

Health state is propagated through **immutable value objects** rather than mutation:

- `AHealthyIp.updated_status(is_healthy)` returns a **new** `AHealthyIp` instance if the status changed, or `self` when unchanged.
- `AHealthyRecord.updated_ips(updated_ips)` returns a **new** `AHealthyRecord` if any IP changed, or `self` when unchanged.

This makes change detection trivially safe: `object is new_object` indicates a change occurred.

`AHealthyIp` is a passive value object: it validates and stores `ip`, `health_port`, and `is_healthy`, but it does not infer health state from the port value. Configuration parsing constructs all IPs with an initial unhealthy state. `DnsServerZoneUpdater` is the single source of truth for runtime health interpretation: it performs TCP checks for IPs with a `health_port` and treats `health_port is None` as healthy during refresh cycles. That shared internal treatment is an implementation detail; product-facing documentation should describe the feature as two supported record modes rather than as one mode being implicit.

**Design invariant:** domain state objects must remain immutable. Produce updated copies instead of mutating in place.

---

## 5. Zone update cycle

The zone is never partially updated. Each refresh cycle follows a write-all-or-nothing approach:

```
initialize_zone()
  └─ zone.writer() (transaction)
       ├─ _clear_zone()         — delete all existing nodes
       ├─ _add_records_to_zone()
       │    ├─ NS record (apex)
       │    ├─ SOA record (apex)
       │    └─ A records (one per subdomain with currently publishable IPs)
       └─ _sign_zone()          — DNSSEC artifacts (if key is configured)
```

The `dns.versioned.Zone` writer is used inside a `with` block; the transaction is committed atomically on exit and rolled back on exception.

`DnsServerZoneUpdaterThreaded.start()` initializes the zone once from the current health state before starting the refresh loop. Because configuration-created IPs start unhealthy, standard static entries (IPs with no health check) become publishable on the first updater refresh rather than during raw configuration parsing.

**Design invariant:** all zone modifications must go through a single writer transaction. Partial writes are not allowed.

---

## 6. Interval calculation pattern

TTLs and timing values are derived consistently from a single source of truth: the **effective max interval**, calculated in `dns_server_zone_updater.py:_calculate_max_interval()`.

The effective interval is the larger of:

- the configured `min_interval`;
- the sum, for each configured A-record owner name, of `(health-checked IP count * connection_timeout) + per-record overhead`.

The per-record overhead is `DELTA_PER_RECORD_MANAGEMENT`, plus the DNSSEC signing overhead when signing is enabled.

```
max_interval = max(
    min_interval,
    sum(
        (health_checked_ip_count * connection_timeout) + per_record_overhead
        for each configured A-record owner name
    ),
)
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
| DNSKEY TTL | `A TTL × 10` |
| RRSIG resign | `= DNSKEY TTL` |
| RRSIG expiration | `2 × SOA refresh + SOA expire + SOA retry` |

Generated DNS TTL and timing values are clamped by `records/time.py` to the RFC 8767 TTL range: `0 <= value <= 2^31-1`.

RFC 8482 synthesized HINFO answers are not stored zone records. Their response TTL is copied in the UDP handler from the same `min(SOA TTL, SOA.MINIMUM)` value used for matched-apex SOA authority in negative responses, so they inherit the SOA timing derived here without adding separate updater state.

**Design invariant:** do not hardcode TTL values or bypass clamping. All timing must be derived via functions in `records/time.py`, taking `max_interval` as input, or copied from another already-derived DNS timing value when a response is synthesized from that protocol context.

---

## 7. Folder hierarchy

This section is the canonical reference for physical directory layout and placement rules. Agents must consult it, consistent with `AGENTS.md` required context rules, when creating or moving files.

### 7.1 Top-level structure

```
a-healthy-dns/
├── .github/              # GitHub-specific automation and IDE bridge files
│   ├── copilot-instructions.md  # minimal bridge back to AGENTS.md
│   └── workflows/        # CI/CD pipeline definitions (GitHub Actions)
├── docs/                 # all long-form documentation
├── indisoluble/          # source package tree (regular Python package)
├── tests/                # test tree — mirrors indisoluble/ by default
├── .dockerignore         # Docker build-context exclusions
├── .gitignore            # local/generated file exclusions
├── AGENTS.md             # AI agent contract
├── Dockerfile            # container image definition
├── LICENSE               # project license
├── README.md             # quick-start entrypoint
├── docker-compose.example.yml  # example Compose configuration
└── pyproject.toml        # packaging, versioning, dependency declarations, and test/coverage tool config
```

This tree lists tracked, project-owned files and directories. Local generated artifacts such as virtual environments, caches, coverage output, and IDE state are ignored and are not part of the repository layout.

**Design invariant:** root-level files are project-wide concerns (packaging, containerisation, CI configuration, agent contract, license, and ignore rules). Do not add source modules or tests at the root level.

### 7.2 Source package: `indisoluble/a_healthy_dns/`

```
indisoluble/              # regular Python package; package root for this repository's code
└── a_healthy_dns/        # application package root; all source modules live here
    ├── records/          # DNS record construction and domain value objects (Layer 3)
    ├── tools/            # low-level utilities with no DNS wire/message handling or record-construction dependencies (Layer 4)
    ├── dns_server_*.py   # server orchestration modules (Layers 1–2)
    └── main.py           # entry-point (Layer 0)
```

`indisoluble/` is a regular package with an `__init__.py`. The repository does not currently rely on PEP 420 namespace-package behavior.

`indisoluble/a_healthy_dns/` contains an `__init__.py` and is the package boundary for all imports, coverage measurement, and the CLI entry-point.

### 7.3 Subpackage: `records/`

Groups all files responsible for constructing or assembling DNS resource records and related immutable domain value objects.

| File pattern | Belongs here if… |
|---|---|
| DNS rdataset factory | it builds an `A`, `NS`, `SOA`, `DNSKEY`, `NSEC`, or `RRSIG` rdataset |
| Domain value object | it represents health state or record-level data (e.g. `AHealthyIp`, `AHealthyRecord`) |
| Timing helper | it derives TTL or signature timing from health-check parameters |
| Zone-origin value | it carries primary or alias zone names |

**Design invariant:** do not place network I/O, threading, or configuration-parsing logic inside `records/`.

### 7.4 Subpackage: `tools/`

Groups low-level utility functions that have **no DNS wire/message handling or record-construction dependencies** and no dependencies above Layer 4. Some helpers intentionally encode primitive DNS input rules, such as label syntax. Most helpers are pure validators or converters; the deliberate exception is the raw TCP connectivity probe used by the health-check loop.

| File pattern | Belongs here if… |
|---|---|
| Validation helper | it validates a primitive (IP, port, subdomain) without side effects |
| Conversion helper | it normalises or converts a primitive value |
| Time helper | it reads the system clock as a raw value (`uint32_current_time`) |
| Connectivity probe | it tests a raw TCP connection (`can_create_connection`) |

**Design invariant:** files in `tools/` must not import from `records/` or any higher layer.

### 7.5 Test tree: `tests/`

```
tests/
└── indisoluble/
    └── a_healthy_dns/      # mirrors indisoluble/a_healthy_dns/ by default
        ├── records/
        │   └── test_*.py
        ├── rfc_conformance/
        │   └── test_rfc_*.py
        ├── tools/
        │   └── test_*.py
        └── test_*.py
```

The test tree mirrors the source tree by default. Most source folders have a corresponding test folder, and most source modules `foo.py` should have a mirrored test file `test_foo.py`. The deliberate exception is `tests/indisoluble/a_healthy_dns/rfc_conformance/`, which groups executable protocol-conformance documentation by RFC number instead of by source module.

**Current pattern:** when adding a new source file `indisoluble/a_healthy_dns/X/foo.py`, default to placing its module-focused test under `tests/indisoluble/a_healthy_dns/X/`. Naming and broader test-convention rules are defined in [`docs/testing.md`](testing.md). Exceptions are allowed when a dedicated mirrored test would be redundant or when behavior is better covered by a higher-level or cross-cutting test, but the exception should be deliberate and justified in the change.

### 7.6 Placement rules for new files

| What you are adding | Where it goes |
|---|---|
| New DNS record factory or domain value object | `indisoluble/a_healthy_dns/records/` |
| New pure utility / primitive helper | `indisoluble/a_healthy_dns/tools/` |
| New server-level module (orchestration, config, handler) | `indisoluble/a_healthy_dns/` (package root) |
| Test for any of the above | mirrored path under `tests/indisoluble/a_healthy_dns/` |
| Level 1 RFC conformance test | `tests/indisoluble/a_healthy_dns/rfc_conformance/test_rfc_<number>.py` |
| New documentation file | `docs/` |
| New CI/CD workflow | `.github/workflows/` |
| New subpackage (new domain grouping) | inside `indisoluble/a_healthy_dns/`; justify in PR why existing folders are insufficient |

---

## 8. Multi-domain support via ZoneOrigins

`records/zone_origins.ZoneOrigins` holds the primary zone name plus any alias zones. The `DnsServerUdpHandler` relativizes every incoming query name against all known origins.

```python
relative_name = zone_origins.relativize(query_name)
# returns None when query_name matches no known origin
```

Origins are sorted by descending specificity (length) to ensure the most specific zone matches first. The zone itself is always stored under the primary origin; alias zones are lookup aliases only.

**Design invariant:** alias zones must never appear as a separate `dns.versioned.Zone`. They are handled purely at query-relativization time in `ZoneOrigins.relativize()`.

---

## 9. DNSSEC as an optional, isolated concern

DNSSEC artifact publication is an additive, opt-in behaviour controlled by the presence of `DnsServerConfig.ext_private_key`:

- `None` → no signing; the zone contains only the base A/NS/SOA records.
- set → `_sign_zone()` is called at the end of each zone-recreation transaction, and `dnspython.sign_zone()` adds DNSKEY, NSEC, and corresponding RRSIG datasets to the zone.

This architecture section covers signing inputs, artifact generation, and refresh timing only. Full DNSSEC authoritative-server protocol behavior, including EDNS(0)/DO handling, signed-answer augmentation, authenticated denial, and complete DNSSEC query semantics, remains outside the current product scope and is bounded by [`docs/RFC-conformance.md`](RFC-conformance.md).

RRSIG key rotation timing is managed by `records/dnssec.iter_rrsig_key()`, a stateful generator that yields a new `ExtendedRRSigKey` each time signing is invoked. The zone updater tracks `resign` time and forces a zone recreation before the current signature expires.

**Design invariant:** DNSSEC logic must remain isolated to `records/dnssec.py` and the `_sign_zone()` call in `DnsServerZoneUpdater`. Do not spread DNSSEC awareness into other layers.

---

## 10. Graceful shutdown pattern

`main()` registers `SIGINT` and `SIGTERM` handlers that:
1. Call `server.shutdown()` in a new thread (avoids deadlock with `serve_forever()`).
2. After `UDPServer` exits its loop, call `zone_updater.stop()`.

`stop()` sets a `threading.Event` to signal the background loop, then `join()`s the thread with a timeout.

**Design invariant:** any new background thread or resource must be cleanly stopped in the `main()` shutdown sequence. The current pattern is the existing `Event + join` shutdown flow.
