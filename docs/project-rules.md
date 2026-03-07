# Project Rules

## Purpose

This document captures the repository-specific development workflow, QA
commands, packaging conventions, release mechanics, and documentation
maintenance rules for A Healthy DNS.

## Baseline Environment

- Python `3.10` is the baseline runtime and CI version.
- Packaging is currently driven by `setup.py`.
- The console entrypoint is `a-healthy-dns`, mapped to
  `indisoluble.a_healthy_dns.main:main`.
- Application code lives under `indisoluble/a_healthy_dns/`.
- Tests mirror the source package under `tests/indisoluble/a_healthy_dns/`.

## Source-of-Truth Files

- `setup.py` is the current source of truth for package name, package version,
  dependencies, Python version floor, and console-script registration.
- `Dockerfile` is the source of truth for container packaging, runtime user, and
  environment-to-CLI translation.
- `docker-compose.example.yml` is the example deployment contract for Docker
  Compose users.
- `README.md` is the user-facing quick-start entrypoint.

## Development Workflow

### Setup

For local development, use the same baseline steps CI uses:

```bash
python -m pip install --upgrade pip
pip install pytest pytest-cov
pip install -e .
```

If editable install is not needed, `pip install .` is sufficient.

### Change Strategy

- Prefer small, reviewable changes that preserve the current module split.
- Keep CLI wiring in `main.py`.
- Keep startup parsing and validation in `dns_server_config_factory.py`.
- Keep health evaluation and zone rebuild logic in `dns_server_zone_updater.py`.
- Keep UDP request handling thin and read-only.
- Extend the existing `records/` value objects before introducing cross-cutting
  special cases in the server loop or request handler.

### Test Placement

- Put tests under `tests/indisoluble/a_healthy_dns/` following the source path.
- Prefer deterministic unit tests with mocks for sockets, time, and file reads.
- Use container-level checks only when validating Docker packaging or the
  runtime contract across process boundaries.

## QA Commands

### Minimum Python Verification

Run this after non-trivial Python changes:

```bash
pytest
```

### CI-Parity Python Verification

This matches the repository's Python test workflow most closely:

```bash
python -m pip install --upgrade pip
pip install pytest pytest-cov
pip install .
pytest --cov=indisoluble.a_healthy_dns --cov-report=term --cov-report=xml
```

### Docker Verification

Run this when changing the Docker image, environment variable contract, startup
behavior, or deployment docs:

```bash
docker build -t a-healthy-dns:test .
```

The CI workflow also performs a functional container test that validates:

- alias-zone behavior
- authoritative A and NS answers
- expected `NOERROR` and `NXDOMAIN` responses
- `docker-compose.example.yml` syntax

### Compose Verification

When changing `docker-compose.example.yml`, validate it with:

```bash
docker-compose -f docker-compose.example.yml config
```

### Coverage Notes

- Coverage is configured through `.coveragerc`.
- Coverage measurement targets `indisoluble.a_healthy_dns`.
- Tests and `setup.py` are excluded from coverage reporting.
- The HTML coverage output directory is `coverage_html_report/`.

## CI Rules

Current CI focuses on:

- Python tests with coverage upload
- Docker build and functional runtime validation
- version progression checks
- container vulnerability scanning

No formatter, linter, or type-checker workflow is currently wired into CI. When
adding one, document it here and add the corresponding command to the QA
section.

## Versioning and Release Rules

### Version Source of Truth

- The package version is stored in `setup.py`.
- The current release format is `v<setup.py version>` for tags and GitHub
  releases.

### Version Progression

The repository currently enforces a monotonically increasing `setup.py` version
through the `test version` workflow. If that workflow remains unchanged, any
change intended to merge to `master` should be evaluated against that rule
before opening or updating the PR.

### Release Automation

After the validation workflow succeeds on `master`:

- a Git tag `v<version>` is created
- a GitHub release is created from that tag
- Docker images are published to Docker Hub as `latest` and `<version>`

Because the Docker release workflow updates the Docker Hub description from
`README.md`, changes to `README.md` also affect the published container page.

## Packaging and Runtime Conventions

- Keep package metadata and dependency changes in `setup.py` until the project
  intentionally migrates to another packaging format.
- Preserve the console command name `a-healthy-dns` unless there is an explicit
  compatibility decision.
- Preserve the current environment variable names in the Docker image unless the
  change is deliberate and documented.
- Prefer backward-compatible configuration changes where practical, because both
  the CLI contract and the Docker environment contract are user-facing.

## Documentation Maintenance Rules

- Update `README.md` when the first-run path, install path, or project
  positioning changes.
- Update long-form docs under `docs/` when changing architecture, configuration,
  Docker behavior, runtime semantics, or contributor workflow.
- Update `docs/table-of-contents.md` whenever adding, removing, or materially
  repurposing a document.
- Add accepted architecture- or behavior-shaping docs to the minimum reading set
  in `docs/table-of-contents.md`.
- Keep `README.md` short and move detailed reference material into focused docs.

## When to Run Which Checks

- Python-only logic change: `pytest`, then CI-parity Python verification for
  higher confidence.
- Dockerfile or container entrypoint change: Docker verification plus compose
  validation.
- DNS query-path or zone-update behavior change: Python verification and, when
  practical, Docker verification.
- Version or release automation change: inspect the related GitHub workflows and
  confirm `setup.py` version handling still matches them.
