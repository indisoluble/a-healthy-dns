# Tech Context

## Language & Runtime
- **Python ≥ 3.10** (uses `typing` features: `NamedTuple`, `Optional`, `FrozenSet`, `Iterator`).
- No `match` statements or `3.12+` features observed — compatible down to 3.10.

## Dependencies

### Runtime
| Package | Version Constraint | Purpose |
|---------|--------------------|---------|
| `dnspython` | `>=2.8.0, <3.0.0` | DNS message parsing, zone management (`dns.versioned.Zone`), record types, DNSSEC signing, name handling |
| `cryptography` | `>=46.0.5, <47.0.0` | Underlying crypto for DNSSEC key operations (used by dnspython's `dns.dnssecalgs`) |

### Development
| Package | Purpose |
|---------|---------|
| `pytest` | Test runner (not in `install_requires`, installed separately) |
| `unittest.mock` | Mocking (`patch`, `MagicMock`, `Mock`) — stdlib, no extra dependency |

### No Other Dependencies
- No linter config files found (no `ruff.toml`, `.flake8`, `pyproject.toml`).
- No type checker config (`mypy.ini`, `pyrightconfig.json`).
- No CI config files in the repo (no `.github/workflows/`).

## Build & Packaging
- **`setup.py`** with `setuptools` (`find_packages()`).
- Version: `0.1.26`.
- Entry point: `console_scripts` → `a-healthy-dns = indisoluble.a_healthy_dns.main:main`.
- Package namespace: `indisoluble.a_healthy_dns` (nested namespace under `indisoluble/`).
- `__init__.py` files are empty — no package-level exports.

## Docker
- **Multi-stage build**: `python:3-slim` builder → `python:3-slim` production.
- Builder installs `gcc`, `libffi-dev`, `libssl-dev`, `cargo`, `rustc` for cryptography wheel compilation.
- Production stage:
  - Non-root user `appuser` (UID/GID 10000).
  - `tini` as PID 1 init.
  - `cap_net_bind_service` on Python binary for port 53 binding.
  - All other capabilities dropped.
  - Environment variables (`DNS_*`) converted to CLI args in the entrypoint shell script.
- **Default port**: 53 (Docker) / 53053 (CLI).
- **Resource limits** (docker-compose example): 256M memory, 0.5 CPU.

## Key stdlib Usage
| Module | Usage |
|--------|-------|
| `argparse` | CLI argument parsing with groups and epilog |
| `socketserver.UDPServer` | DNS server socket management |
| `socketserver.BaseRequestHandler` | Request handling base class |
| `threading.Thread` | Background zone updater thread |
| `threading.Event` | Graceful shutdown coordination |
| `signal` | SIGINT/SIGTERM handling |
| `socket.create_connection` | TCP health checks |
| `logging` | Structured logging throughout |
| `json` | Parsing JSON CLI arguments (zone resolutions, name servers, alias zones) |
| `functools.partial` | Partial application for connection testing and signal handling |
| `time` | SOA serial generation, sleep timing |
| `datetime` | RRSIG timing management |
| `enum.Enum` | `RefreshARecordsResult` states |

## Key dnspython API Usage
| API | Usage |
|-----|-------|
| `dns.versioned.Zone` | Thread-safe versioned zone with reader/writer transactions |
| `dns.message.from_wire()` / `.make_response()` | UDP query parsing and response building |
| `dns.rdataset.from_text()` | Record construction from text representations |
| `dns.dnssec.sign_zone()` | Zone signing with RRSIG |
| `dns.dnssecalgs.get_algorithm_cls()` | Load DNSSEC algorithm from PEM key |
| `dns.dnssec.make_dnskey()` | Generate DNSKEY from public key |
| `dns.name.from_text()` / `.relativize()` | DNS name manipulation |
| `dns.flags.AA` | Authoritative Answer flag |

## Environment Variables (Docker)
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DNS_HOSTED_ZONE` | Yes | — | Primary hosted zone name |
| `DNS_ZONE_RESOLUTIONS` | Yes | — | JSON subdomain→IP/port mappings |
| `DNS_NAME_SERVERS` | Yes | — | JSON list of name servers |
| `DNS_PORT` | No | `53` | DNS server listen port |
| `DNS_LOG_LEVEL` | No | `info` | Logging verbosity |
| `DNS_ALIAS_ZONES` | No | `[]` | JSON list of alias zone names |
| `DNS_TEST_MIN_INTERVAL` | No | `30` | Health check interval (seconds) |
| `DNS_TEST_TIMEOUT` | No | `2` | Health check timeout (seconds) |
| `DNS_PRIV_KEY_PATH` | No | — | Path to DNSSEC private key PEM |
| `DNS_PRIV_KEY_ALG` | No | `RSASHA256` | DNSSEC algorithm |
