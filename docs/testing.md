# Testing

Test strategy and validation commands for **A Healthy DNS**.

This document is the canonical home for test taxonomy, local validation commands, test placement, naming, and coverage expectations. Engineering principles live in [`docs/engineering-rules.md`](engineering-rules.md); CI workflow behavior lives in [`docs/workflow.md`](workflow.md).

## Local Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[test]"
```

## QA Commands

Use the coverage command as the CI-equivalent local check before merge.

### Run All Tests

```bash
pytest
```

This runs the configured test suite and default coverage reports from `pyproject.toml`.

### Run Tests With Coverage

```bash
pytest --cov=indisoluble.a_healthy_dns --cov-report=term --cov-report=xml
```

Coverage is measured over `indisoluble.a_healthy_dns` only. `tests/` is excluded. Coverage and pytest settings are centralized in `pyproject.toml`.

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
- Prefer one behavior per test. Multiple assertions are acceptable when together they document one observable outcome or contract.
- Coverage excludes `tests/` at run time and extends report exclusions with `__repr__`, `raise NotImplementedError`, `raise ImportError`, `if __name__ == '__main__'`, and `pass` via `pyproject.toml`.

Cross-cutting behavior tests that do not map to a single source module may live at `tests/indisoluble/a_healthy_dns/`. Small, justified exceptions are allowed when a dedicated mirrored test would add noise without improving coverage.

## Tests As Documentation

Automated tests are part of the repository's executable documentation. They must verify behavior and make the expected contract clear through their name, setup, action, and assertions.

- Prefer test names that state the behavior or contract being protected, not the implementation step being exercised.
- Structure unit tests around a clear Given/When/Then flow: set up the relevant state, execute one public behavior, and assert observable results. Literal Given/When/Then comments are optional; use them only when they improve readability.
- Assert public behavior and boundary effects: return values, raised exceptions, DNS response codes, DNS response sections and flags, log messages, or calls to injected dependencies when that dependency is the boundary under test.
- Keep fixtures and helper functions descriptive enough that the test body can be read as the behavior contract.
- For regression coverage, name the contract being preserved rather than the bug mechanism or internal implementation detail.

## Test Maintainability

Test code is production code for the repository quality gate. Keep it organized, explicit, and reviewable with the same discipline as runtime code.

- Group tests by behavior or responsibility using pytest-compatible classes when a module has several distinct concerns.
- Prefer class names that describe the purpose under test, such as `TestInitializationValidation`, `TestUpdateRefresh`, or `TestRejectedQueries`.
- Keep shared setup in fixtures or small helper functions when it removes meaningful repetition.
- Keep helper functions local to the test module unless several modules need the same behavior.
- Avoid adding edge cases as an unstructured list of top-level tests. Put the new case in the behavior group it belongs to, or create a new group when the behavior is distinct.
- Do not introduce broad abstractions in tests just to reduce a few lines of setup. Readability at the assertion site matters more than minimizing line count.

## Parametrized Tests

Use parametrization when the same behavior should hold for several inputs. Do not use parametrization when separate test names would make materially different behavior easier to understand.

Default rules:

- Use plain parameter values by default.
- Treat `ids` as reporting-only labels. They must not carry behavior, expectations, or hidden test meaning.
- Omit `ids` when pytest's generated case name is already clear from the raw parameter values.
- Use `ids=[...]` only when failure output would otherwise be noisy, opaque, unstable, or less meaningful than the scenario name.
- Do not use `pytest.param(...)` just to attach IDs to ordinary cases.
- Use `pytest.param(...)` only when an individual case needs per-case metadata, such as `marks=pytest.mark.xfail`, `marks=pytest.mark.skip`, or another case-specific pytest option.

Good reasons to use `ids` include:

- long JSON strings or DNS wire payloads
- lambdas, function objects, or generated objects whose `repr` does not explain the case
- dense multi-field matrices where the business scenario is clearer than the raw tuple
- booleans or integers whose domain meaning is not obvious from the test name

Do not add `ids` only to restate simple values such as `None`, `False`, `0`, short strings, IP address strings, or small tuples that pytest already renders clearly.

When every case needs a readable scenario name, prefer `ids=[...]` on `@pytest.mark.parametrize` instead of wrapping every case in `pytest.param(..., id=...)`.

## Component Integration Tests

Component integration tests exercise a production component end-to-end over real I/O, such as real UDP sockets, but with pre-populated in-memory state rather than the live health-check lifecycle.

- Test file location: same directory as the corresponding unit tests, mirroring the source tree.
- Test file naming: `test_<scope>_integration.py`.
- No real health-check lifecycle; zone state is pre-populated via `DnsServerZoneUpdater.initialize_zone()`.
- Tests that verify dynamic A-record changes driven by TCP health checks belong in Docker end-to-end coverage.

## Docker End-To-End Tests

Docker end-to-end tests validate the fully packaged application, including health-check-driven DNS state transitions. They live in `.github/workflows/test-integration.yml` and use an isolated Docker network with a real nginx backend.

Use this level when the behavior requires the built image, Docker entrypoint, container command argument handling, real container networking, or real TCP health checks.
