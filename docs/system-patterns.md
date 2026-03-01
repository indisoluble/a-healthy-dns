# System Patterns

Architecture patterns and conventions observed in the codebase.
Agents **must** follow these when extending the project.

---

## Composition root

All wiring lives in `main._main()` (`indisoluble/a_healthy_dns/main.py`).
Components receive their dependencies at construction time — no service locator
or global state.

```
_main(args)
  ├─ config = make_config(args)
  ├─ zone_updater = DnsServerZoneUpdaterThreated(…, config)
  │     └─ .start()  →  init zone, spawn background thread
  ├─ UDPServer(address, DnsServerUdpHandler)
  │     ├─ server.zone = zone_updater.zone
  │     └─ server.zone_origins = config.zone_origins
  │     └─ server.serve_forever()
  └─ zone_updater.stop()
```

---

## Factory functions for construction

Complex or validated construction is encapsulated in factory functions, not
spread across callers.

| Factory | Location |
|---|---|
| `make_config(args)` | `dns_server_config_factory.py` |
| `make_a_record(max_interval, healthy_record)` | `records/a_record.py` |
| `make_ns_record(max_interval, name_servers)` | `records/ns_record.py` |
| `iter_soa_record(max_interval, …)` | `records/soa_record.py` |
| `iter_rrsig_key(max_interval, …)` | `records/dnssec.py` |

> **Convention:** invariant checks run inside factories / constructors — never
> scattered across call sites.

---

## Immutable value objects

Two styles coexist:

| Style | Examples |
|---|---|
| `NamedTuple` | `DnsServerConfig`, `ExtendedPrivateKey`, `RRSigKey`, `ExtendedRRSigKey`, `RRSigLifetime` |
| Manual immutable class (private attrs + properties) | `AHealthyIp`, `AHealthyRecord`, `ZoneOrigins` |

**Functional update pattern:** `AHealthyIp.updated_status(is_healthy)` and
`AHealthyRecord.updated_ips(ips)` return the **same instance** when nothing
changed, or a **new instance** when state differs.

---

## Infinite generators for stateful iteration

SOA serials and DNSSEC signing keys are produced by infinite generators that
encapsulate auto-incrementing state:

- `soa_record.iter_soa_record()` / `_iter_soa_serial()`
- `dnssec.iter_rrsig_key()`

---

## Dependency injection via `functools.partial`

`DnsServerZoneUpdater.__init__` curries external dependencies with
`functools.partial`:

```python
self._make_a_record     = partial(make_a_record, max_interval)
self._can_create_connection = partial(can_create_connection, timeout=…)
```

This avoids global state and makes dependencies explicit.

---

## Cooperative cancellation

Long-running operations accept a `ShouldAbortOp = Callable[[], bool]` callback.
The threaded updater passes `lambda: self._stop_event.is_set()`.

---

## Versioned Zone (concurrent reads)

`dns.versioned.Zone` provides lock-free concurrent reads: the UDP handler sees a
consistent snapshot while the updater rebuilds the zone in a writer transaction.

The zone is **fully rebuilt** (clear → add all records) on each update cycle —
no incremental patches.

---

## Tools layer — pure utility functions

All `tools/*.py` files export **standalone functions** (no classes).

Validation functions follow a consistent signature:
```python
def is_valid_*(value) -> Tuple[bool, str]:
```
Returns `(True, "")` on success or `(False, "reason")` on failure.

---

## Request handling

`DnsServerUdpHandler` (extends `socketserver.BaseRequestHandler`) delegates to a
module-level `_update_response()` function. This extraction makes the core
response logic testable without socket/server machinery.

---

## Concurrency separation

Domain logic (`DnsServerZoneUpdater`) is single-threaded and knows nothing about
threads. Threading is confined to `DnsServerZoneUpdaterThreated`, which wraps the
updater with a `threading.Thread` and `threading.Event`.

---

## Testing conventions

- `pytest` as runner; `unittest.mock.patch` / `MagicMock` for isolation.
- Test file structure mirrors source: `tests/indisoluble/a_healthy_dns/…`.
- Domain objects are tested without mocks; infrastructure boundaries are mocked.
- Fixtures are defined per-file (`@pytest.fixture`); no shared fixture modules.
