# Project Rules

Language/tool specifics, conventions, and QA workflow for **A Healthy DNS**.

---

## 1. Language and runtime

| Item | Rule |
|---|---|
| Python version | **3.10 minimum** (`setup.py:python_requires=">=3.10"`) |
| Entry-point | `a-healthy-dns` CLI → `indisoluble.a_healthy_dns.main:main` (`setup.py:entry_points`) |
| Package root | `indisoluble/a_healthy_dns/` |
| Test root | `tests/indisoluble/a_healthy_dns/` — mirrors the source tree exactly |

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

Run these before merging any change. All must pass.

### 5.1 Run all tests

```bash
pytest
```

### 5.2 Run tests with coverage (matches CI exactly)

```bash
pytest --cov=indisoluble.a_healthy_dns --cov-report=term --cov-report=xml
```

Coverage is measured over `indisoluble.a_healthy_dns` only (`setup.py` and `tests/` are excluded). See `.coveragerc` for the full exclusion list.

### 5.3 Run a single test file

```bash
pytest tests/indisoluble/a_healthy_dns/records/test_a_healthy_ip.py
```

### 5.4 Run tests with verbose output

```bash
pytest -v
```

### 5.5 Generate an HTML coverage report (optional, local only)

```bash
pytest --cov=indisoluble.a_healthy_dns --cov-report=html
# Report written to coverage_html_report/
```

---

## 6. Test conventions

### 6.1 Unit tests

- **Framework:** `pytest` with standard fixtures and `unittest.mock`.
- **Test file location:** must mirror the source path. Example: `indisoluble/a_healthy_dns/records/a_healthy_ip.py` → `tests/indisoluble/a_healthy_dns/records/test_a_healthy_ip.py`.
- **Test file naming:** `test_<module_name>.py`.
- **No real network calls in unit tests.** Mock `can_create_connection` or `socket.create_connection` for any test that exercises health logic.
- **No real time dependencies.** Mock `time.time`, `datetime.datetime.now`, or `uint32_current_time` as needed to keep tests deterministic.
- **One assert per test when practical** (AGENTS.md §5.9).
- **Coverage exclusions** (`.coveragerc`) include: `__repr__`, `raise NotImplementedError`, `if __name__ == '__main__'`, `pass`, and `pragma: no cover` markers.

### 6.2 Component integration tests

Component integration tests exercise a production component end-to-end over real I/O (e.g. real UDP sockets), but with pre-populated in-memory state rather than the live health-check lifecycle.

- **Test file location:** same directory as the corresponding unit tests, mirroring the source tree.
- **Test file naming:** `test_<scope>_integration.py` — the `_integration` suffix distinguishes them from unit tests. Example: `tests/indisoluble/a_healthy_dns/test_dns_server_udp_integration.py`.
- **No real health-check lifecycle.** Zone state is pre-populated via `DnsServerZoneUpdater.update(check_ips=False)`. Tests that verify dynamic A-record changes driven by TCP health checks belong in `test-integration.yml`.
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
| `validate tests` | `validate-tests.yml` | after above three complete | Gate: all three must pass for the same commit |
| `release version` | `release-version.yml` | after `validate tests` succeeds | Creates git tag + GitHub release from `setup.py` version |
| `release docker` | `release-docker.yml` | after `release version` succeeds | Pushes Docker image to Docker Hub |
| `security scan` | `security-scan.yml` | push → master | Trivy vulnerability scan on Docker image, uploads SARIF to GitHub Security tab |

**Rule:** never push directly to `master` from a branch that hasn't passed all three gate workflows.

---

## 8. Docker conventions

The `Dockerfile` uses a **multi-stage build**:

1. **Builder stage** (`python:3-slim`) — installs `gcc`, `libffi-dev`, `libssl-dev`, `cargo`, `rustc`; builds the package into `/root/.local`.
2. **Production stage** (`python:3-slim`) — copies only `/root/.local` from builder; installs runtime libs (`libffi8`, `libssl3`); creates a non-root user `appuser` (uid/gid `10000`); uses `tini` as PID 1.

**Rules:**
- The container runs as non-root (`appuser`). Do not change this.
- DNSSEC keys are mounted into `/app/keys` (mode `700`, owned by `appuser`).
- The Python binary is granted `CAP_NET_BIND_SERVICE` via `setcap` to allow binding to port 53 without root.
- Entrypoint variables are the `DNS_*` environment variables (see [docs/configuration-reference.md](configuration-reference.md)).

Docker end-to-end tests in CI use an isolated `172.28.0.0/24` bridge network with a real `nginx:alpine` backend so health checks exercise an actual TCP connection.

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
