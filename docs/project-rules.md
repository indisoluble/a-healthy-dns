# Project Rules

## Language and runtime

- **Python 3.10+** — minimum version enforced in `setup.py` (`python_requires=">=3.10"`).
- **Package manager:** pip. No `pyproject.toml`, `poetry`, or `pipenv`.
- **Dependencies (runtime):**
  - `dnspython >=2.8.0, <3.0.0`
  - `cryptography >=46.0.5, <47.0.0`
- **Dependencies (test, CI-only):** `pytest`, `pytest-cov`. Installed at CI time, not pinned in a requirements file.
- **Entry point:** `a-healthy-dns` console script → `indisoluble.a_healthy_dns.main:main` (defined in `setup.py`).

## Conventions

### Code style

No automated linter or formatter is configured (no black, flake8, ruff, mypy, isort configs). Follow the existing code conventions:

- Module-level docstrings on every source file.
- `snake_case` for functions, methods, variables, and module names.
- `PascalCase` for classes and `NamedTuple` types.
- `UPPER_SNAKE_CASE` for module-level constants.
- Private names prefixed with `_` (single underscore).
- Validation functions return `(bool, str)` tuples — `(success, error_message)`.
- Immutable data: prefer `NamedTuple`, `FrozenSet`, and identity-returning update methods.

### Test conventions

- **Framework:** pytest (direct `assert` statements, not `unittest.TestCase`).
- **Location:** mirror tree under `tests/` — e.g. `indisoluble/a_healthy_dns/records/a_record.py` → `tests/indisoluble/a_healthy_dns/records/test_a_record.py`.
- **Naming:** `test_{function}_{condition}` (e.g. `test_make_config_success`, `test_make_zone_invalid_hosted_zone`).
- **Fixtures:** `@pytest.fixture` with chained dependencies for reusable setup.
- **Parametrize:** `@pytest.mark.parametrize` for multiple-input variations.
- **Mocking:** `unittest.mock` (`patch`, `Mock`, `MagicMock`). Patch at the import site, not the definition site.
- **Identity assertions:** use `assert obj is other` to verify immutable-return-self patterns.

### Version management

- Version is the single source of truth in `setup.py` (`version="X.Y.Z"`).
- Every merge to `master` **must** increment the version. CI enforces `current > previous` using `packaging.version`.
- Semantic versioning.

## QA commands

### Run unit tests locally

```bash
# From the repository root, with virtualenv activated:
pip install .          # or: pip install -e .
pytest
```

### Run unit tests with coverage

```bash
pytest --cov=indisoluble.a_healthy_dns --cov-report=term --cov-report=xml
```

Coverage configuration is in `.coveragerc`:
- Source: `indisoluble.a_healthy_dns`
- Omits: `*/tests/*`, `*/setup.py`
- Excludes: `__repr__`, `pragma: no cover`, `raise NotImplementedError`, `if __name__ == "__main__":`, `pass`, `raise ImportError`

### Build and test Docker image locally

```bash
docker build -t a-healthy-dns:test .
docker run --rm \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["192.168.1.100"],"health_port":8080}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  a-healthy-dns:test
```

### Validate Docker Compose file

```bash
docker compose -f docker-compose.example.yml config --quiet
```

### Query a running server

```bash
dig @localhost -p 53053 www.example.com
```

## CI/CD pipeline

### Overview

```
push / PR to master
    │
    ├──► test-py-code.yml ──────┐
    │                           │
    ├──► test-version.yml ──────┤
    │                           ├──► validate-tests.yml ──┬──► release-version.yml
    │                           │                         │
    └──► test-docker.yml ───────┘                         └──► release-docker.yml

push to master (independent)
    │
    └──► security-scan.yml
```

### Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `test-py-code.yml` | push / PR to `master` | Run pytest with coverage; upload to Codecov. |
| `test-version.yml` | push / PR to `master` | Verify `setup.py` version strictly increases. |
| `test-docker.yml` | push / PR to `master` | Build Docker image; run E2E DNS tests with `dig` against a live container. |
| `validate-tests.yml` | after the three test workflows complete | Quality gate — all three must pass before releases. |
| `release-version.yml` | after `validate-tests` succeeds on `master` | Create annotated git tag `v{VERSION}` + GitHub Release. |
| `release-docker.yml` | after `validate-tests` succeeds on `master` | Build multi-platform image (`amd64`, `arm64`); push to Docker Hub with `latest` + versioned tags. |
| `security-scan.yml` | push to `master` | Trivy vulnerability scan; results uploaded to GitHub Security tab (SARIF). |

### Secrets

| Secret | Used by |
|--------|---------|
| `CODECOV_TOKEN` | `test-py-code.yml` |
| `GH_TOKEN` | `validate-tests.yml` |
| `DOCKER_HUB_USERNAME` | `release-docker.yml` |
| `DOCKER_HUB_ACCESS_TOKEN` | `release-docker.yml` |

### Release checklist

1. Increment `version` in `setup.py`.
2. Run `pytest` locally to confirm tests pass.
3. Push / open PR to `master`.
4. CI runs tests → validate → release automatically.
