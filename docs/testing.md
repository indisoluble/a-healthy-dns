# Testing

Test strategy and validation commands for **A Healthy DNS**.

This document is the canonical home for test taxonomy, local validation commands, test placement, naming, and coverage expectations. Engineering principles live in [`docs/engineering-rules.md`](engineering-rules.md); CI workflow behavior lives in [`docs/workflow.md`](workflow.md).

## Local Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
pip install pytest pytest-cov
```

## QA Commands

Use the coverage command as the CI-equivalent local check before merge.

### Run All Tests

```bash
pytest
```

This is useful for a fast local pass when coverage output is not needed.

### Run Tests With Coverage

```bash
pytest --cov=indisoluble.a_healthy_dns --cov-report=term --cov-report=xml
```

Coverage is measured over `indisoluble.a_healthy_dns` only. `setup.py` and `tests/` are excluded. See `.coveragerc` for the full exclusion list.

Other local helpers:

- `pytest tests/.../test_foo.py` for a single file.
- `pytest -v` for verbose output.
- `pytest --cov=indisoluble.a_healthy_dns --cov-report=html` for local HTML output in `coverage_html_report/`.

## Unit Tests

- Framework: `pytest` with standard fixtures and `unittest.mock`.
- Test file location: mirror the source path by default. Example: `indisoluble/a_healthy_dns/records/a_healthy_ip.py` -> `tests/indisoluble/a_healthy_dns/records/test_a_healthy_ip.py`.
- Test file naming: `test_<module_name>.py`.
- No real network calls in unit tests.
- No real time dependencies in unit tests.
- Prefer one assert per test when practical.
- Coverage exclusions (`.coveragerc`) include: `__repr__`, `raise NotImplementedError`, `raise ImportError`, `if __name__ == '__main__'`, `pass`, and `pragma: no cover` markers.

Cross-cutting behavior tests that do not map to a single source module may live at `tests/indisoluble/a_healthy_dns/`. Small, justified exceptions are allowed when a dedicated mirrored test would add noise without improving coverage.

## Component Integration Tests

Component integration tests exercise a production component end-to-end over real I/O, such as real UDP sockets, but with pre-populated in-memory state rather than the live health-check lifecycle.

- Test file location: same directory as the corresponding unit tests, mirroring the source tree.
- Test file naming: `test_<scope>_integration.py`.
- No real health-check lifecycle; zone state is pre-populated via `DnsServerZoneUpdater.initialize_zone()`.
- Tests that verify dynamic A-record changes driven by TCP health checks belong in Docker end-to-end coverage.

## Docker End-To-End Tests

Docker end-to-end tests validate the fully packaged application, including health-check-driven DNS state transitions. They live in `.github/workflows/test-integration.yml` and use an isolated Docker network with a real nginx backend.

Use this level when the behavior requires the built image, Docker entrypoint, container command argument handling, real container networking, or real TCP health checks.
