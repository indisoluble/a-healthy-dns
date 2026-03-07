# System Patterns

## Overview

A Healthy DNS is organized around a small runtime pipeline:

1. Parse CLI arguments and configure logging.
2. Validate and normalize startup configuration into immutable runtime inputs.
3. Build and maintain an in-memory authoritative DNS zone.
4. Run background TCP health checks that can trigger full zone regeneration.
5. Answer UDP DNS queries from the current zone snapshot.

The design keeps configuration parsing, health-check orchestration, record
generation, and query serving in separate modules with a narrow set of shared
objects.

## Architectural Drivers

- Keep the runtime easy to reason about: one entrypoint, one config builder, one
  background updater, one request handler.
- Prefer rebuilding the zone from current state over performing fine-grained
  record mutation logic across many code paths.
- Keep mutable runtime state local to the zone updater; keep configuration and
  record descriptions immutable or effectively immutable.
- Fail early on invalid input instead of trying to run with partial
  configuration.

## Module Roles

### Composition Root

`indisoluble/a_healthy_dns/main.py` is the composition root. It defines the CLI,
creates the runtime configuration, starts the threaded updater, injects the
shared zone and zone origins into `socketserver.UDPServer`, and coordinates
graceful shutdown on `SIGINT` and `SIGTERM`.

### Configuration Boundary

`indisoluble/a_healthy_dns/dns_server_config_factory.py` is the input-validation
and normalization layer. It converts raw CLI JSON strings into a
`DnsServerConfig` that contains:

- `ZoneOrigins` for the primary zone and alias zones
- normalized name servers
- validated `AHealthyRecord` instances
- optional DNSSEC key material

This module is the main boundary between untrusted input and the rest of the
runtime.

### Background Update Loop

`indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py` wraps the core
zone updater in a daemon thread. It performs one initial zone build without
health checks, then repeats update cycles until shutdown is requested.

### Zone Rebuild Engine

`indisoluble/a_healthy_dns/dns_server_zone_updater.py` owns the mutable runtime
state:

- the current `dns.versioned.Zone`
- the latest set of healthy/unhealthy backend states
- the signing schedule when DNSSEC is enabled

Its main responsibility is to decide when the zone must be recreated and then
rebuild NS, SOA, A, and optional DNSSEC records from current state.

### Query Path

`indisoluble/a_healthy_dns/dns_server_udp_handler.py` is deliberately thin. It
parses the incoming DNS packet, creates an authoritative response, maps the
query name to the configured zone origins, reads the current zone, and returns
either:

- `NXDOMAIN` when the name is outside the hosted or alias zones
- `NXDOMAIN` when the subdomain does not exist
- `NOERROR` with an empty answer when the name exists but the queried type does
  not
- an answer section populated from the current zone snapshot

### Domain Value Objects

The `records/` layer contains small domain-focused helpers:

- `ZoneOrigins` normalizes the primary zone plus aliases and resolves incoming
  names against the most specific matching origin.
- `AHealthyRecord` models one subdomain and its backend set.
- `AHealthyIp` models one backend IP, its shared health port, and its current
  health flag.
- `time.py` centralizes TTL and DNSSEC lifetime calculations derived from the
  effective update interval.

## Runtime Topology

### Shared Objects

- `server.zone`: the current in-memory authoritative zone
- `server.zone_origins`: origin matcher used by the request handler
- `DnsServerZoneUpdater._a_recs`: the updater's mutable health-state source of
  truth

### State Ownership

- Configuration objects are created once at startup and treated as immutable.
- Health state evolves only inside the zone updater.
- Query handling reads from the zone but does not mutate it.
- Alias-zone mapping is stable after startup.

This keeps write responsibility concentrated in one component and read
responsibility in another.

## Startup Flow

1. `main()` parses CLI arguments.
2. `_main()` configures logging and calls `make_config(...)`.
3. `make_config(...)` validates hosted zone, alias zones, name servers,
   resolution payloads, IP addresses, ports, and optional DNSSEC inputs.
4. The process creates `DnsServerZoneUpdaterThreated`.
5. `start()` performs an initial `update(check_ips=False)` to build the first
   zone snapshot.
6. The UDP server is created and receives the updater's zone plus the validated
   `ZoneOrigins`.
7. The process begins `serve_forever()` while the background updater loop runs.

## Query Handling Pattern

The request path is intentionally read-only and short:

1. Parse wire data into a DNS query.
2. Build an authoritative response object.
3. Use `ZoneOrigins.relativize(...)` to map absolute names under the primary
   zone or alias zones into the relative names stored in the zone.
4. Open a zone reader transaction and fetch the node and rdataset.
5. Copy the rdataset into an answer RRset for the original query name.
6. Serialize and send the response.

Important behavior:

- Queries outside configured origins are rejected before touching the zone.
- The handler does not perform health checks or record synthesis inline.
- Record-type absence is distinct from name absence.

## Zone Update Pattern

The updater follows a rebuild-on-change model instead of mutating individual DNS
records in place across many branches.

### Update Decision

Each cycle:

1. Iterate through each configured backend IP.
2. Run a TCP connectivity probe with the configured timeout.
3. Produce updated `AHealthyIp` and `AHealthyRecord` values.
4. Determine whether backend health changed.
5. Trigger a zone rebuild when:
   - health state changed,
   - DNSSEC resign time has been reached, or
   - the zone has not been created yet.

### Rebuild Process

When rebuilding:

1. Open a zone writer transaction.
2. Clear existing nodes from the zone.
3. Re-add NS and SOA records at the zone apex.
4. Re-add A records for subdomains that currently have healthy backends.
5. Optionally sign the zone.

This pattern keeps the published zone as a deterministic projection of current
state instead of a long-lived mutable structure updated by many small deltas.

## Timing Model

The runtime uses one derived timing model rather than separate unrelated TTL and
polling knobs.

### Effective Update Interval

The updater calculates `max_interval` from:

- requested minimum interval
- connection timeout
- number of backend IPs
- extra per-record work for record management and DNSSEC signing

This prevents a loop iteration from being scheduled faster than it can
realistically complete.

### TTL and DNSSEC Lifetimes

`records/time.py` derives:

- A TTL from the effective update interval
- NS and SOA TTLs from the A TTL
- SOA refresh/retry/expire values from the same base timing
- DNSKEY TTL and RRSIG resign/expiration values from the same model

The intended pattern is: cache behavior and signing behavior should move with
the health-check cadence rather than drift independently.

## Concurrency Model

- One main thread owns process startup, signal handling, and the UDP server.
- One daemon thread runs the periodic update loop.
- The updater supports cooperative shutdown via `should_abort`.
- The first zone build happens synchronously before the background thread starts
  its repeating loop.

This separates concurrency from the domain model: record objects and config
objects do not manage threads or sockets directly.

## Boundary and Validation Patterns

- All external input is validated at the configuration boundary before the
  server begins serving.
- Name normalization and alias matching are centralized in `ZoneOrigins`.
- IP normalization and port validation live in `AHealthyIp`.
- TCP connectivity is isolated behind `can_create_connection(...)`.
- DNSSEC private-key loading is isolated to config creation.

The preferred extension style is to add or tighten behavior at these boundaries
instead of spreading validation logic across request handling and update logic.

## Invariants

- The zone origin is always the primary hosted zone.
- Alias zones reuse the same relative subdomain names and backend targets.
- Unhealthy backends do not appear in A answers.
- If a subdomain has no healthy backends, its A rdataset is omitted.
- Query handling never mutates the zone.
- Invalid startup configuration prevents the runtime from starting.

## Extension Guidance

When changing the system, preserve these patterns:

- Keep `main.py` as the composition root rather than moving domain logic into
  CLI wiring.
- Keep config parsing and validation in the config factory.
- Keep health evaluation separate from request handling.
- Prefer deriving published DNS state from current health state through a full
  rebuild over ad hoc incremental mutation, unless there is a measured reason to
  change that pattern.
- Extend domain helpers (`ZoneOrigins`, `AHealthyRecord`, `AHealthyIp`, timing
  helpers) before adding cross-cutting special cases in the server loop or
  handler.
