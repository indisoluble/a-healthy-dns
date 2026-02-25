# Progress

## Current Status: Stable — v0.1.26

### What Works
- **Health-aware DNS resolution**: A records served with only healthy IPs (TCP health-check based).
- **Authoritative UDP DNS server**: Responds with `AA` flag, handles A/NS/SOA queries.
- **Background health checking**: Threaded zone updater with configurable interval and timeout.
- **DNSSEC zone signing**: Optional RRSIG/DNSKEY support with automatic resign scheduling.
- **Multi-domain support**: Alias zones resolve identically to the primary hosted zone.
- **Docker deployment**: Multi-stage build, non-root, minimal capabilities, env-var configuration.
- **CLI configuration**: Full argparse with grouped arguments and detailed help.
- **Comprehensive test suite**: 236 tests, all passing.

### What's Not Built Yet
- **TCP DNS transport**: Only UDP is supported.
- **AAAA records**: Only IPv4 A records.
- **Dynamic record management API**: No HTTP/REST API to add/remove records at runtime.
- **Persistent state**: Zone and health status are in-memory only; restart loses state.
- **CI/CD pipeline**: No GitHub Actions or other CI configuration.
- **Linting / formatting**: No configured linter (ruff, flake8, black, etc.).
- **Type checking**: No mypy/pyright configuration.
- **Metrics / monitoring**: No Prometheus or health endpoints.
- **Clustering / replication**: Single-instance only.

### Release History (from git tags)
| Version | Commit | Summary |
|---------|--------|---------|
| v0.1.26 | `13de8fd` | Multi-domain support via alias zones |
| v0.1.25 | `caa6766` | Revert Docker Hardened Image |
| v0.1.21 | `e2f6c71` | Increase cryptography version |
| v0.1.20 | `1b8b2d4` | Force update |
| v0.1.19 | `2f15eac` | Add .vscode to .gitignore |
| v0.1.18 | `29f71c3` | Set app version to 0.1.18 |

### Known Issues
- None tracked in the repository.

### Blockers
- None.
