# Testing Patterns

## Framework and Scope
- Test framework: pytest.
- Suite location: `tests/indisoluble/a_healthy_dns/**`.
- Coverage config source target: `indisoluble.a_healthy_dns`.
- Evidence: `.github/workflows/test-py-code.yml:27-33`, `.coveragerc:1-5`.

## Current Baseline
- Session run (2026-02-26): `236 passed in 1.01s`.

## Test Design Patterns
- Parameterized validation matrices for input edge cases.
  - Evidence: `tests/indisoluble/a_healthy_dns/test_dns_server_config_factory.py:130-289`, `tests/indisoluble/a_healthy_dns/tools/test_is_valid_port.py:15-32`.
- Extensive mocking for side effects:
  - Network I/O: `tests/indisoluble/a_healthy_dns/tools/test_can_create_connection.py:9-26`.
  - Time functions: `tests/indisoluble/a_healthy_dns/records/test_soa_record.py:66-81`.
  - DNSSEC datetime/key behavior: `tests/indisoluble/a_healthy_dns/records/test_dnssec.py:12-66`.
  - Server wiring: `tests/indisoluble/a_healthy_dns/test_main.py:40-100`.
- Integration-style zone state assertions using real dnspython zone objects.
  - Evidence: `tests/indisoluble/a_healthy_dns/test_dns_server_zone_updater.py:212-313`.
- Docker-level functional checks for hosted+alias zones and DNS status codes.
  - Evidence: `.github/workflows/test-docker.yml:68-148`.

## Recommended Test Commands
```bash
pytest
pytest --cov=indisoluble.a_healthy_dns --cov-report=term --cov-report=xml
```

## Quality Guardrails
- Maintain deterministic tests by patching time/network boundaries.
- Keep constructor validation tests synchronized with validator helper behavior.
- Preserve alias-zone and DNSSEC paths when modifying updater or handler logic.
