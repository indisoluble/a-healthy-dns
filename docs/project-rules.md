# Project Rules

## Language and runtime

| Rule | Value |
|---|---|
| Language | Python 3 |
| Minimum version | Python 3.10 |
| Package definition | `setup.py` (no `pyproject.toml`) |
| Entry point | `a-healthy-dns` → `indisoluble.a_healthy_dns.main:main` |
| Source root | `indisoluble/` |
| Test root | `tests/` |

### Dependencies

Declared in `setup.py:install_requires`. Pin exact major versions:

| Package | Range | Purpose |
|---|---|---|
| `cryptography` | `>=46.0.5,<47.0.0` | DNSSEC cryptographic operations |
| `dnspython` | `>=2.8.0,<3.0.0` | DNS protocol handling |

Dev dependencies (install separately, not in `setup.py`):

| Package | Purpose |
|---|---|
| `pytest` | Test runner |
| `pytest-cov` | Coverage reporting |

---

## Local setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate      # macOS / Linux
# venv\Scripts\activate       # Windows

# 2. Install the package in development mode
pip install -e .

# 3. Install dev dependencies
pip install pytest pytest-cov
```

> The virtual environment at `venv/` is already present in this workspace.

---

## QA commands

### Run all tests

```bash
pytest
```

### Run tests with coverage (matches CI exactly)

```bash
pytest --cov=indisoluble.a_healthy_dns --cov-report=term --cov-report=xml
```

Coverage is reported to the terminal and written to `coverage.xml`.  
The CI gate uploads `coverage.xml` to [Codecov](https://codecov.io/gh/indisoluble/a-healthy-dns).

### Run a single test file

```bash
pytest tests/indisoluble/a_healthy_dns/records/test_a_healthy_ip.py
```

### Run tests matching a keyword

```bash
pytest -k "zone_updater"
```

---

## Test conventions

- Tests mirror the source tree under `tests/`:  
  `indisoluble/a_healthy_dns/foo.py` → `tests/indisoluble/a_healthy_dns/test_foo.py`
- One `test_*.py` file per source module.
- Use `unittest.mock` for patching I/O boundaries (`can_create_connection`, `socket`, time).
- Prefer one assert per test.
- Tests must not open real network connections or depend on wall-clock time.

---

## Code style

No linter configuration file is present (no `.flake8`, `pyproject.toml`, or `setup.cfg`).  
Follow PEP 8. The codebase uses:

- 4-space indentation.
- Double-quoted strings.
- Type annotations on all public function signatures and class properties.
- Module-level docstrings on every source file.

---

## Versioning

- Version is declared in `setup.py:version`.
- Every push to `master` **must** increment the version. The `test version` CI workflow enforces this by comparing `setup.py` version against the previous commit.
- Versioning follows [PEP 440](https://peps.python.org/pep-0440/) / [Semantic Versioning](https://semver.org/) (current series: `0.1.x`).

---

## CI workflows

All workflows trigger on push/PR to `master`.

| Workflow file | Name | What it does |
|---|---|---|
| `.github/workflows/test-py-code.yml` | test python code | Runs `pytest --cov` on Python 3.10, uploads coverage to Codecov |
| `.github/workflows/test-docker.yml` | test docker | Builds Docker image, runs integration test with `dig` against a live container |
| `.github/workflows/test-version.yml` | test version | Validates that `setup.py` version was incremented vs. previous commit |
| `.github/workflows/validate-tests.yml` | validate tests | Gate: passes only when all three test workflows pass on the same commit |
| `.github/workflows/release-version.yml` | release version | Triggered after `validate tests` passes; creates Git tag + GitHub release |
| `.github/workflows/release-docker.yml` | release docker | Publishes Docker image to Docker Hub on release |
| `.github/workflows/security-scan.yml` | security scan | Runs Trivy container vulnerability scan; uploads SARIF to GitHub Security tab (push to master only) |

### Gate model

```
test-py-code ──┐
test-docker  ──┤──► validate-tests ──► release-version ──► release-docker
test-version ──┘
```

A release is only created when all three test workflows pass on the same commit SHA.

---

## Docker build

Multi-stage build defined in `Dockerfile`:

1. **builder** stage — installs build deps (gcc, libffi-dev, libssl-dev, cargo, rustc), runs `pip install .`
2. **production** stage — copies only `~/.local` from builder; installs runtime-only system libs (`libffi8`, `libssl3`, `libcap2-bin`, `tini`)

Security hardening in the Docker image:
- Runs as non-root user `appuser` (UID/GID 10000).
- `tini` is used as PID 1 to handle signal forwarding.
- `setcap` grants `cap_net_bind_service` to the Python interpreter so port 53 can be bound.
- `--security-opt no-new-privileges` and `cap_drop: ALL` with `cap_add: NET_BIND_SERVICE` in the example compose file.

Build the image locally:

```bash
docker build -t a-healthy-dns .
```

Run a quick smoke test:

```bash
docker run --rm \
  -p 53053:53053/udp \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  a-healthy-dns
```
