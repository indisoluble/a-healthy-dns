# Project Rules

Language/tool specifics, conventions, and QA workflow for **A Healthy DNS**.

This document is the canonical home for:
- runtime and dependency rules tied to the repository,
- local setup and QA workflow,
- CI and release workflow rules,
- and repository-specific code conventions that future changes should follow.

It does not own architecture and file-placement guidance, parameter reference material, deployment procedures, or troubleshooting playbooks. Those topics live in [`docs/system-patterns.md`](system-patterns.md), [`docs/configuration-reference.md`](configuration-reference.md), [`docs/docker.md`](docker.md), and [`docs/troubleshooting.md`](troubleshooting.md).

---

## 1. Language and runtime

| Item | Rule |
|---|---|
| Python version | **3.10 minimum** (`setup.py:python_requires=">=3.10"`) |
| Entry-point | `a-healthy-dns` CLI → `indisoluble.a_healthy_dns.main:main` (`setup.py:entry_points`) |
| Package root | `indisoluble/a_healthy_dns/` |
| Test root | `tests/indisoluble/a_healthy_dns/` — mirrors the source tree by default |

---

## 2. Dependencies

Managed in `setup.py`. Do not introduce a `requirements.txt` or `pyproject.toml` in parallel.

| Package | Constraint | Purpose |
|---|---|---|
| `dnspython` | `>=2.8.0,<3.0.0` | DNS protocol (zones, records, DNSSEC signing) |
| `cryptography` | `>=46.0.5,<47.0.0` | DNSSEC key loading and crypto operations |

Dev/test packages (`pytest`, `pytest-cov`) are installed directly in CI and are not declared in `setup.py`.

**Rule:** keep upper-bound pins tight (minor version only). Both libraries have historically introduced breaking API changes across minor versions.

---

## 3. Versioning

The single source of truth for the version is the `version` field in `setup.py:version`.

**Rules:**
- Every commit merged to `master` **must** increase the version.
- This is enforced automatically by the `test version` CI workflow (`.github/workflows/test-version.yml`), which compares the current version against `HEAD~1` using `packaging.version`.
- Use [PEP 440](https://peps.python.org/pep-0440/) version strings (e.g. `0.1.26`).
- Do not create git tags or GitHub releases manually — the `release version` workflow handles this automatically after all checks pass on `master`.

---

## 4. Local development setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install the package in editable mode with test tooling
pip install -e .
pip install pytest pytest-cov
```

---

## 5. QA commands

Use **5.2** as the CI-equivalent local check before merge. The other commands in this section are narrower or optional helpers for local iteration.

### 5.1 Run all tests

```bash
pytest
```

Useful for a fast local pass when you do not need coverage output.

### 5.2 Run tests with coverage (matches CI exactly)

```bash
pytest --cov=indisoluble.a_healthy_dns --cov-report=term --cov-report=xml
```

Coverage is measured over `indisoluble.a_healthy_dns` only (`setup.py` and `tests/` are excluded). See `.coveragerc` for the full exclusion list.

This is the primary pre-merge local QA command because it matches the `test python code` workflow.

Other helpers: `pytest tests/.../test_foo.py` (single file), `pytest -v` (verbose), `pytest --cov=indisoluble.a_healthy_dns --cov-report=html` (local HTML report in `coverage_html_report/`).

---

## 6. Test conventions

### 6.1 Unit tests

- **Framework:** `pytest` with standard fixtures and `unittest.mock`.
- **Test file location:** for module-focused tests, mirror the source path by default. Example: `indisoluble/a_healthy_dns/records/a_healthy_ip.py` → `tests/indisoluble/a_healthy_dns/records/test_a_healthy_ip.py`. Cross-cutting behavior tests that do not map to a single source module may live at `tests/indisoluble/a_healthy_dns/`. Small, justified exceptions are allowed when a dedicated mirrored test would add noise without improving coverage.
- **Test file naming:** `test_<module_name>.py`.
- **No real network calls in unit tests.** Mock `can_create_connection` or `socket.create_connection` for any test that exercises health logic.
- **No real time dependencies.** Mock `time.time`, `datetime.datetime.now`, or `uint32_current_time` as needed to keep tests deterministic.
- **One assert per test when practical.**
- **Coverage exclusions** (`.coveragerc`) include: `__repr__`, `raise NotImplementedError`, `raise ImportError`, `if __name__ == '__main__'`, `pass`, and `pragma: no cover` markers.

### 6.2 Component integration tests

Component integration tests exercise a production component end-to-end over real I/O (e.g. real UDP sockets), but with pre-populated in-memory state rather than the live health-check lifecycle.

- **Test file location:** same directory as the corresponding unit tests, mirroring the source tree.
- **Test file naming:** `test_<scope>_integration.py` — the `_integration` suffix distinguishes them from unit tests. Example: `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py`.
- **No real health-check lifecycle.** Zone state is pre-populated via `DnsServerZoneUpdater.initialize_zone()`. Tests that verify dynamic A-record changes driven by TCP health checks belong in `test-integration.yml`.
- **One assert per test when practical** (same as unit tests).

### 6.3 Docker end-to-end tests

Docker end-to-end tests validate the fully packaged application, including health-check-driven DNS state transitions. They live in `.github/workflows/test-integration.yml` and use an isolated Docker network with a real nginx backend. See §7 below.

---

## 7. CI workflows

All workflows target the `master` branch.

| Workflow | File | Trigger | Purpose |
|---|---|---|---|
| `test python code` | `test-py-code.yml` | push/PR → master | Runs pytest (unit + component integration tests) with coverage, uploads to Codecov |
| `test integration` | `test-integration.yml` | push/PR → master | Builds Docker image; runs end-to-end tests including health-check-driven DNS state transitions |
| `test version` | `test-version.yml` | push/PR → master | Verifies version in `setup.py` was increased |
| `validate tests` | `validate-tests.yml` | `workflow_run` on any of the three above | Gate: all three must pass for the same commit |
| `release version` | `release-version.yml` | after `validate tests` succeeds | Creates git tag + GitHub release from `setup.py` version |
| `release docker` | `release-docker.yml` | after `release version` succeeds | Pushes Docker image to Docker Hub |
| `security scan` | `security-scan.yml` | push → master | Trivy vulnerability scan on Docker image, uploads SARIF to GitHub Security tab |

**Rule:** never push directly to `master` from a branch that hasn't passed all three gate workflows.

**Rule:** workflow names are part of the automation contract. If you rename a workflow's `name:`, update every dependent `workflow_run` reference in the repository.

**Gate scope:** `security scan` is important, but it is not part of the three-workflow `validate tests` gate. The release chain depends on `test python code`, `test integration`, and `test version` only.

**`validate tests` trigger model:** GitHub Actions `workflow_run` fires each time *any one* of the listed upstream workflows completes — not once after all three are done. This means `validate tests` may run before the other two upstream workflows have finished; early runs that fail because a sibling workflow hasn't completed yet are expected and not the final picture. The meaningful result is the run that executes after all three required workflows for the same commit SHA have completed. This is an implementation detail of the current `workflow_run` model; the intended policy (all three must pass) is unchanged.

---

## 8. Repository-owned container conventions

See [docs/docker.md](docker.md) for deployment procedures, Compose usage, runtime hardening, and orchestrator notes.

This section owns only the repository-side rules for changes to `Dockerfile`, `docker-compose.example.yml`, and Docker-related CI workflows.

**Rules for container-build changes:**
- The final image runs as the non-root `appuser` user. Do not change this casually.
- `/app/keys` remains the mount point for DNSSEC private keys, owned by `appuser` with restrictive permissions.
- The Python interpreter keeps `CAP_NET_BIND_SERVICE` via `setcap` so the process can bind port `53` without running as root.
- The image entrypoint continues to translate `DNS_*` environment variables into CLI flags. Parameter semantics belong in [docs/configuration-reference.md](configuration-reference.md), not here.
- Docker end-to-end coverage continues to use an isolated bridge network with a real backend container so health checks exercise an actual TCP connection.

---

## 9. Release process (automated)

1. Update `version` in `setup.py` to a new PEP 440 value higher than the current one.
2. Merge to `master`.
3. CI automatically:
   - runs `test python code`, `test integration`, `test version`,
   - if all three pass: `validate tests` succeeds,
   - `release version` creates the git tag and GitHub release,
   - `release docker` pushes the tagged image to Docker Hub.

No manual tagging or Docker Hub pushes are required.

---

## 10. File and module naming

| Context | Convention |
|---|---|
| Source modules | `snake_case.py` |
| Test modules | `test_<source_module>.py` |
| Class names | `PascalCase` |
| Function / method names | `snake_case` |
| Constants (module-level) | `UPPER_SNAKE_CASE` |
| Private helpers | prefix `_` (single underscore) |
| CLI argument names | `kebab-case` (e.g. `--hosted-zone`) |
| `argparse` dest / internal keys | `snake_case` (matches `ARG_*` constants in `dns_server_config_factory.py`) |
| Docker environment variables | `DNS_` prefix + `UPPER_SNAKE_CASE` |

---

## 11. Code conventions

The repository is consistent on import grouping, validator signatures, class member layout, `NamedTuple` usage for immutable data bags, `%s`-style logging, and type annotations on all function signatures. Module headers are normalized for executable modules; package `__init__.py` files remain empty when they exist only to mark package boundaries.

### 11.1 Import ordering

Each source module organizes imports into five groups, each separated by a blank line:

1. Standard-library direct imports (`import X`)
2. Third-party direct imports (`import X`)
3. Standard-library from-imports (`from X import Y`)
4. Third-party from-imports (`from X import Y`)
5. Local imports (`from indisoluble.a_healthy_dns... import Y`)

```python
# test_dns_server_config_factory.py (representative example)
import json

import dns.dnssectypes
import dns.name
import pytest

from unittest.mock import patch

from dns.dnssecalgs.rsa import PrivateRSASHA256

from indisoluble.a_healthy_dns import dns_server_config_factory as dscf
from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp
```

Skip groups that are not needed; do not collapse remaining groups together. Local imports normally use `from ... import ...`; aliasing the imported symbol or submodule is acceptable when repeated constant access would otherwise add noise. Test files follow the same rule.

### 11.2 Module headers

Executable source modules start with the shebang line and, unless the file is an intentionally empty package `__init__.py`, immediately follow it with a module-level docstring:

```python
#!/usr/bin/env python3

"""Short description of what this module provides.

Optional longer explanation of scope and design intent.
"""
```

Test files include the shebang (`#!/usr/bin/env python3`) but omit the module docstring. Empty `__init__.py` files are the deliberate exception on the source side.

### 11.3 Validation function signature

Utility functions in `tools/` that validate a primitive value return `Tuple[bool, str]`: `(True, "")` on success and `(False, error_message)` on failure. Input type is `Any` to safely handle unvalidated external input.

```python
from typing import Any, Tuple

def is_valid_ip(ip: Any) -> Tuple[bool, str]:
    if not isinstance(ip, str):
        return (False, "It must be a string")
    ...
    return (True, "")
```

### 11.4 Class member layout

Class members are declared in this order: `@property` accessors → `__init__` → public methods → dunder methods (`__eq__`, `__hash__`, `__repr__`).

```python
class AHealthyIp:
    @property
    def ip(self) -> str: ...

    @property
    def health_port(self) -> int: ...

    def __init__(self, ip: Any, health_port: Any, is_healthy: bool): ...

    def updated_status(self, is_healthy: bool) -> "AHealthyIp": ...

    def __eq__(self, other): ...
    def __hash__(self): ...
    def __repr__(self): ...
```

### 11.5 NamedTuple for immutable data bags

`NamedTuple` is used for immutable containers that hold related fields with no behavior beyond construction (e.g. config, key container, signature timing). Classes are used when objects carry behavior (`AHealthyIp`, `AHealthyRecord`, `ZoneOrigins`).

```python
class DnsServerConfig(NamedTuple):
    zone_origins: ZoneOrigins
    primary_name_server: str
    name_servers: FrozenSet[str]
    a_records: FrozenSet[AHealthyRecord]
    ext_private_key: Optional[ExtendedPrivateKey]
```

### 11.6 Logging format

Use `%s`-style format strings with `logging` calls — not f-strings or `str.format()`:

```python
logging.error("Invalid IP address '%s': %s", ip, error)
logging.debug("Created A record with ttl: %d, and IPs: %s", ttl, ips)
```

### 11.7 Type annotations

All function and method signatures include parameter type annotations and return type annotations. Use `Any` only where the function intentionally accepts unvalidated external input (e.g. validator parameters).

```python
def is_valid_ip(ip: Any) -> Tuple[bool, str]:
    ...

def make_a_record(max_interval: int, ips: FrozenSet[str]) -> Optional[dns.rdataset.Rdataset]:
    ...

def updated_status(self, is_healthy: bool) -> "AHealthyIp":
    ...
```
