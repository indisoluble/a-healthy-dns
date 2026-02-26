# Tech Context

## Language and Runtime
- Python package, `python_requires >=3.10`. Evidence: `setup.py:8`.
- Local test run observed on Python 3.13.12 with pytest 9.0.2.
- CLI entrypoint: `a-healthy-dns = indisoluble.a_healthy_dns.main:main`. Evidence: `setup.py:10-12`.

## Core Dependencies
- `dnspython>=2.8.0,<3.0.0` for DNS message parsing, zone transactions, and DNSSEC operations.
- `cryptography>=46.0.5,<47.0.0` for key material compatibility in DNSSEC flow.
- Evidence: `setup.py:9`.

## Networking Stack
- UDP server uses `socketserver.UDPServer`.
- Health checks use TCP `socket.create_connection`.
- Evidence: `indisoluble/a_healthy_dns/main.py:7`, `indisoluble/a_healthy_dns/main.py:234`, `indisoluble/a_healthy_dns/tools/can_create_connection.py:16`.

## Data and State
- In-memory zone object: `dns.versioned.Zone`.
- No repository code for external DB, cache, or message broker.
- Evidence: `indisoluble/a_healthy_dns/dns_server_zone_updater.py:112`.

## Containerization
- Multi-stage `python:3-slim` build.
- Non-root runtime user (`uid/gid 10000`) and `cap_net_bind_service` for privileged DNS ports.
- Tini used as init/entrypoint wrapper.
- Evidence: `Dockerfile:2-3`, `Dockerfile:39-55`, `Dockerfile:50-53`, `Dockerfile:84`.

## CI/CD Tooling
- Python tests + coverage: `.github/workflows/test-py-code.yml`.
- Docker build and functional DNS checks: `.github/workflows/test-docker.yml`.
- Version bump enforcement via `setup.py` diff: `.github/workflows/test-version.yml`.
- Release tagging and Docker publish gated by successful workflow aggregation.
- Evidence: `.github/workflows/validate-tests.yml:4-45`, `.github/workflows/release-version.yml:15-76`, `.github/workflows/release-docker.yml:15-57`.

## Coverage Configuration
- Coverage source is scoped to `indisoluble.a_healthy_dns`, tests and setup omitted.
- HTML report target directory: `coverage_html_report`.
- Evidence: `.coveragerc:1-17`.
