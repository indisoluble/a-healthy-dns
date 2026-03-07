# Project Rules

## Scope

This document defines the repository-specific development and QA workflow for `a-healthy-dns`.

It focuses on executable local commands, CI alignment, and change guardrails for contributors.

## Runtime and Tooling Baseline

1. Python version: `>=3.10`.
2. Package entrypoint: `a-healthy-dns`.
3. Core runtime dependencies:
   - `cryptography>=46.0.5,<47.0.0`
   - `dnspython>=2.8.0,<3.0.0`
4. Primary local test framework: `pytest`.
5. Container runtime: Docker (with optional docker-compose for config validation).

Reference anchors:

- `setup.py:8`
- `setup.py:9`
- `setup.py:11`
- `.github/workflows/test-py-code.yml:24`
- `.github/workflows/test-docker.yml:23`

## Local Development Workflow

### 1) Install dependencies

Run from repository root:

```bash
python -m pip install --upgrade pip
pip install pytest pytest-cov
pip install .
```

For editable development:

```bash
pip install -e .
```

Reference anchors:

- `.github/workflows/test-py-code.yml:24`
- `.github/workflows/test-py-code.yml:28`
- `README.md:43`
- `README.md:45`

### 2) Run unit/integration tests

```bash
pytest
```

Coverage command (CI-aligned):

```bash
pytest --cov=indisoluble.a_healthy_dns --cov-report=term --cov-report=xml
```

Reference anchors:

- `.github/workflows/test-py-code.yml:30`

### 3) Basic runtime smoke test (CLI)

```bash
a-healthy-dns \
  --hosted-zone example.com \
  --zone-resolutions '{"www":{"ips":["127.0.0.1"],"health_port":80}}' \
  --ns '["ns1.example.com"]' \
  --port 53053
```

Reference anchors:

- `README.md:49`
- `indisoluble/a_healthy_dns/main.py:62`

### 4) Docker build and run smoke test

Build:

```bash
docker build -t a-healthy-dns:test .
```

Run:

```bash
docker run --rm \
  -p 53053:53/udp \
  -e DNS_HOSTED_ZONE="example.com" \
  -e DNS_ZONE_RESOLUTIONS='{"www":{"ips":["127.0.0.1"],"health_port":80}}' \
  -e DNS_NAME_SERVERS='["ns1.example.com"]' \
  a-healthy-dns:test
```

Reference anchors:

- `.github/workflows/test-docker.yml:23`
- `.github/workflows/test-docker.yml:45`
- `Dockerfile:84`
- `docker-compose.example.yml:11`

### 5) Optional docker-compose config validation

```bash
docker-compose -f docker-compose.example.yml config
```

Reference anchors:

- `.github/workflows/test-docker.yml:149`

## Mandatory Pre-PR Checks

Before opening or updating a PR, run:

1. `pytest`
2. `pytest --cov=indisoluble.a_healthy_dns --cov-report=term --cov-report=xml`
3. `docker build -t a-healthy-dns:test .`

If changes touch Docker/env wiring, also run:

4. `docker-compose -f docker-compose.example.yml config`

If changes touch DNS behavior, additionally validate representative queries:

5. `dig` checks for:
   - expected A responses on configured names,
   - `NXDOMAIN` on missing names,
   - `NOERROR`/empty answer for unsupported type on existing names.

Reference anchors:

- `.github/workflows/test-py-code.yml:30`
- `.github/workflows/test-docker.yml:68`
- `.github/workflows/test-docker.yml:145`
- `.github/workflows/test-docker.yml:146`
- `.github/workflows/test-docker.yml:147`

## Versioning and Release Rules

1. Any change merged to `master` must increment `setup.py` version.
2. CI checks current version against `HEAD~1` and fails if not increased.
3. Successful validated builds trigger:
   - Git tag and GitHub release creation (`v<version>`),
   - Docker Hub publish for `latest` and `<version>` tags.

Reference anchors:

- `setup.py:5`
- `.github/workflows/test-version.yml:30`
- `.github/workflows/release-version.yml:23`
- `.github/workflows/release-version.yml:55`
- `.github/workflows/release-docker.yml:39`

## Security and Runtime Guardrails

1. Keep container hardening behavior intact unless explicitly changing security posture:
   - non-root runtime user,
   - dropped capabilities with `NET_BIND_SERVICE` add-back,
   - `no-new-privileges`.
2. Preserve required environment-variable checks in Docker entrypoint.
3. If Dockerfile changes, run local image build and vulnerability scan if available.

Reference anchors:

- `Dockerfile:39`
- `Dockerfile:52`
- `Dockerfile:86`
- `docker-compose.example.yml:35`
- `docker-compose.example.yml:39`
- `.github/workflows/security-scan.yml:19`

## Test Design Rules

1. Prefer deterministic tests (no real network dependencies unless explicitly integration-scoped).
2. Use mocks for external I/O boundaries in unit tests.
3. Keep behavior coverage for:
   - config validation failure paths,
   - zone update state transitions,
   - DNS response status semantics.

Reference anchors:

- `tests/indisoluble/a_healthy_dns/test_dns_server_config_factory.py:130`
- `tests/indisoluble/a_healthy_dns/test_dns_server_zone_updater.py:131`
- `tests/indisoluble/a_healthy_dns/test_dns_server_udp_handler.py:152`

## Documentation and Change Discipline

1. When behavior/config/workflow changes, update documentation in the same PR.
2. Keep `README.md` as quick-start oriented; keep detailed guidance in `docs/`.
3. Update `docs/table-of-contents.md` whenever adding or removing docs.

Reference anchors:

- `AGENTS.md:347`
- `AGENTS.md:350`
- `AGENTS.md:357`
- `AGENTS.md:377`

## Quick Command Reference

```bash
# install
python -m pip install --upgrade pip
pip install pytest pytest-cov
pip install -e .

# test
pytest
pytest --cov=indisoluble.a_healthy_dns --cov-report=term --cov-report=xml

# docker
docker build -t a-healthy-dns:test .
docker-compose -f docker-compose.example.yml config

# run
a-healthy-dns --help
```
