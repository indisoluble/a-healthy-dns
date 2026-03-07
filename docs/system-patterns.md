# System Patterns

## Scope

This document defines the runtime architecture, module boundaries, and extension patterns for `a-healthy-dns`.

It complements `docs/project-brief.md` by describing how the current codebase realizes the project goals.

## Architecture Overview

The system follows a small composition-root architecture with clear runtime boundaries:

1. **Composition root / process wiring**
   - `indisoluble/a_healthy_dns/main.py:62`
   - `indisoluble/a_healthy_dns/main.py:213`
2. **Configuration parsing and validation**
   - `indisoluble/a_healthy_dns/dns_server_config_factory.py:50`
   - `indisoluble/a_healthy_dns/dns_server_config_factory.py:218`
3. **Zone state management and health-driven updates**
   - `indisoluble/a_healthy_dns/dns_server_zone_updater.py:69`
   - `indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py:22`
4. **Request-time DNS query handling**
   - `indisoluble/a_healthy_dns/dns_server_udp_handler.py:24`
   - `indisoluble/a_healthy_dns/dns_server_udp_handler.py:65`
5. **Record builders and domain value objects**
   - `indisoluble/a_healthy_dns/records/a_record.py:21`
   - `indisoluble/a_healthy_dns/records/ns_record.py:20`
   - `indisoluble/a_healthy_dns/records/soa_record.py:43`
   - `indisoluble/a_healthy_dns/records/zone_origins.py:20`
   - `indisoluble/a_healthy_dns/records/a_healthy_ip.py:16`
   - `indisoluble/a_healthy_dns/records/a_healthy_record.py:16`

## Runtime Components

### 1) Composition Root (`main.py`)

Responsibilities:

1. Defines CLI contract and defaults.
2. Builds validated config.
3. Starts threaded updater.
4. Starts UDP DNS server and injects shared zone state.
5. Registers signal handlers for graceful shutdown.

Key anchors:

- `indisoluble/a_healthy_dns/main.py:62`
- `indisoluble/a_healthy_dns/main.py:221`
- `indisoluble/a_healthy_dns/main.py:233`
- `indisoluble/a_healthy_dns/main.py:244`

### 2) Config Factory (`dns_server_config_factory.py`)

Pattern: **Fail-fast validation + normalized immutable config tuple**

Responsibilities:

1. Parse and validate JSON inputs (`alias_zones`, `resolutions`, `name_servers`).
2. Normalize domains and IPs.
3. Build immutable runtime config (`DnsServerConfig`).
4. Optionally load and prepare DNSSEC key material.

Key anchors:

- `indisoluble/a_healthy_dns/dns_server_config_factory.py:31`
- `indisoluble/a_healthy_dns/dns_server_config_factory.py:129`
- `indisoluble/a_healthy_dns/dns_server_config_factory.py:161`
- `indisoluble/a_healthy_dns/dns_server_config_factory.py:201`

### 3) Zone Updater Core (`dns_server_zone_updater.py`)

Pattern: **Recompute zone from canonical in-memory model**

Responsibilities:

1. Computes effective timing (`_calculate_max_interval`).
2. Evaluates backend health through a pluggable connectivity function.
3. Rebuilds zone in a write transaction (NS, SOA, A, optional signatures).
4. Triggers rebuild on A-record health changes or DNSSEC re-sign threshold.

Key anchors:

- `indisoluble/a_healthy_dns/dns_server_zone_updater.py:52`
- `indisoluble/a_healthy_dns/dns_server_zone_updater.py:115`
- `indisoluble/a_healthy_dns/dns_server_zone_updater.py:148`
- `indisoluble/a_healthy_dns/dns_server_zone_updater.py:236`

### 4) Thread Wrapper (`dns_server_zone_updater_threated.py`)

Pattern: **Concurrency isolated from core zone logic**

Responsibilities:

1. Bootstrap initial zone state before serving traffic.
2. Run periodic update loop in daemon thread.
3. Coordinate stop requests with event-based abort checks.

Key anchors:

- `indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py:47`
- `indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py:64`
- `indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py:74`

### 5) UDP Handler (`dns_server_udp_handler.py`)

Pattern: **Read-only query path over shared zone snapshot**

Responsibilities:

1. Parse DNS wire queries.
2. Resolve names against hosted zone or alias zones.
3. Return authoritative responses with expected DNS status codes.

Status behavior:

1. Out-of-zone or unknown names -> `NXDOMAIN`.
2. Existing name without requested type -> `NOERROR` with empty answer.
3. Parse failure -> request dropped (no response payload built).
4. Empty question section -> `FORMERR`.

Key anchors:

- `indisoluble/a_healthy_dns/dns_server_udp_handler.py:31`
- `indisoluble/a_healthy_dns/dns_server_udp_handler.py:46`
- `indisoluble/a_healthy_dns/dns_server_udp_handler.py:72`
- `indisoluble/a_healthy_dns/dns_server_udp_handler.py:90`

## Core Data and Invariants

### Zone scope model

`ZoneOrigins` is the canonical model for primary + alias zones. It normalizes inputs to absolute names and chooses the most specific matching zone when relativizing.

Anchors:

- `indisoluble/a_healthy_dns/records/zone_origins.py:28`
- `indisoluble/a_healthy_dns/records/zone_origins.py:38`

### Health state model

`AHealthyIp` and `AHealthyRecord` are treated as immutable value objects. Updates return new instances when state changes.

Anchors:

- `indisoluble/a_healthy_dns/records/a_healthy_ip.py:48`
- `indisoluble/a_healthy_dns/records/a_healthy_record.py:34`

### Record construction model

Record factories encapsulate DNS rdataset creation and TTL calculation. A records include only healthy endpoints.

Anchors:

- `indisoluble/a_healthy_dns/records/a_record.py:25`
- `indisoluble/a_healthy_dns/records/ns_record.py:24`
- `indisoluble/a_healthy_dns/records/soa_record.py:47`
- `indisoluble/a_healthy_dns/records/dnssec.py:39`

## Execution Flows

### Startup flow

1. Parse CLI arguments.
2. Build `DnsServerConfig`.
3. Initialize zone updater and perform first zone build.
4. Start updater thread.
5. Start UDP server and serve requests.

Anchors:

- `indisoluble/a_healthy_dns/main.py:248`
- `indisoluble/a_healthy_dns/main.py:222`
- `indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py:65`
- `indisoluble/a_healthy_dns/main.py:234`

### Health/update flow

1. Iterate all configured A records and check backend connectivity.
2. Detect state change or re-sign threshold.
3. Recreate zone transactionally when needed.

Anchors:

- `indisoluble/a_healthy_dns/dns_server_zone_updater.py:183`
- `indisoluble/a_healthy_dns/dns_server_zone_updater.py:246`
- `indisoluble/a_healthy_dns/dns_server_zone_updater.py:168`

### Query flow

1. Decode DNS query.
2. Relativize query against zone origins.
3. Read matching node/rdataset from zone.
4. Build authoritative response and send.

Anchors:

- `indisoluble/a_healthy_dns/dns_server_udp_handler.py:73`
- `indisoluble/a_healthy_dns/dns_server_udp_handler.py:31`
- `indisoluble/a_healthy_dns/dns_server_udp_handler.py:39`
- `indisoluble/a_healthy_dns/dns_server_udp_handler.py:95`

### Shutdown flow

1. Signal handler triggers UDP server shutdown.
2. Server exits `serve_forever`.
3. Updater thread receives stop event and joins.

Anchors:

- `indisoluble/a_healthy_dns/main.py:206`
- `indisoluble/a_healthy_dns/main.py:242`
- `indisoluble/a_healthy_dns/main.py:245`
- `indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py:80`

## Extension Patterns

Use these extension points to avoid architectural drift.

### Add or change health-check behavior

Preferred path:

1. Add behavior in `indisoluble/a_healthy_dns/tools/`.
2. Inject/use it through updater construction logic (`DnsServerZoneUpdater`), preserving the current boundary where concurrency remains in `DnsServerZoneUpdaterThreated`.

Anchors:

- `indisoluble/a_healthy_dns/tools/can_create_connection.py:13`
- `indisoluble/a_healthy_dns/dns_server_zone_updater.py:108`
- `indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py:47`

### Add new record support

Preferred path:

1. Add record factory under `indisoluble/a_healthy_dns/records/`.
2. Integrate creation in updater transaction flow.
3. Keep request handler generic around `query_type` lookup where possible.

Anchors:

- `indisoluble/a_healthy_dns/dns_server_zone_updater.py:134`
- `indisoluble/a_healthy_dns/dns_server_udp_handler.py:46`

### Extend config surface

Preferred path:

1. Add CLI argument in `main.py`.
2. Add strict parsing/validation in config factory.
3. Keep runtime modules consuming validated values only.

Anchors:

- `indisoluble/a_healthy_dns/main.py:131`
- `indisoluble/a_healthy_dns/dns_server_config_factory.py:218`

## Architectural Guardrails

1. Keep parsing/validation in config factory, not in request/update runtime paths.
2. Keep zone mutation inside updater write transactions.
3. Keep thread/event logic inside `DnsServerZoneUpdaterThreated`, not in record builders.
4. Keep request path read-only and stateless except for response construction.
5. Prefer value-object updates (`updated_*`) over in-place mutation for health state.

## Test Anchors for Pattern Integrity

These tests encode expected architectural behavior and should remain aligned with future changes:

- Query status semantics: `tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py:152`
- Updater validation and zone rebuild behavior: `tests/indisoluble/a_healthy_dns/test_dns_server_zone_updater.py:131`
- Threaded lifecycle behavior: `tests/indisoluble/a_healthy_dns/test_dns_server_zone_updater_threated.py:138`
