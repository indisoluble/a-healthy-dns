# Documentation Table of Contents

This index defines the canonical documentation set and reading order for `a-healthy-dns`.

## Minimum Reading Set (Current)

Read these first for any implementation or documentation task:

1. [`README.md`](../README.md) - high-signal quick start and first successful run path.
2. [`docs/table-of-contents.md`](./table-of-contents.md) - canonical docs index and reading order.
3. [`docs/project-brief.md`](./project-brief.md) - goals, constraints, and system scope.
4. [`docs/system-patterns.md`](./system-patterns.md) - architecture and extension patterns.
5. [`docs/project-rules.md`](./project-rules.md) - development workflow and QA rules.
6. [`docs/configuration-reference.md`](./configuration-reference.md) - full configuration schema and validation.
7. [`docs/operations-and-troubleshooting.md`](./operations-and-troubleshooting.md) - runtime runbook and diagnostics.
8. [`AGENTS.md`](../AGENTS.md) - repository constraints and workflow for coding agents.

## Core Docs Registry

| Document | Status | Purpose |
| --- | --- | --- |
| [`README.md`](../README.md) | Available | High-signal entrypoint and first successful run path. |
| [`docs/table-of-contents.md`](./table-of-contents.md) | Available | Index, minimum reading set, and documentation sequencing. |
| [`docs/project-brief.md`](./project-brief.md) | Available | Goals, non-goals, constraints, and requirements. |
| [`docs/system-patterns.md`](./system-patterns.md) | Available | Architecture patterns, runtime flow, and extension points. |
| [`docs/project-rules.md`](./project-rules.md) | Available | QA commands, development workflow, and release/testing rules. |
| [`docs/configuration-reference.md`](./configuration-reference.md) | Available | CLI parameters, JSON schema expectations, Docker env mapping. |
| [`docs/operations-and-troubleshooting.md`](./operations-and-troubleshooting.md) | Available | Runbook, DNS checks, failure modes, and diagnostics. |

## Bootstrap Status

Documentation bootstrap baseline and normalization pass are complete.

## Implementation Source Anchors

These implementation anchors are used across the current documentation set:

- CLI definition and runtime startup: `indisoluble/a_healthy_dns/main.py`
- Config parsing and validation: `indisoluble/a_healthy_dns/dns_server_config_factory.py`
- DNS query handling behavior: `indisoluble/a_healthy_dns/dns_server_udp_handler.py`
- Health-check update lifecycle: `indisoluble/a_healthy_dns/dns_server_zone_updater.py`
- Threaded updater lifecycle: `indisoluble/a_healthy_dns/dns_server_zone_updater_threated.py`
- Container runtime contract: `Dockerfile`, `docker-compose.example.yml`
- Test and CI workflow: `.github/workflows/test-py-code.yml`, `.github/workflows/test-docker.yml`, `.github/workflows/test-version.yml`
