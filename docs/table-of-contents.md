# Documentation — Table of Contents

## Minimum Reading Set

These documents are required reading before proposing or applying any changes to this repository.

| Document | Purpose |
|---|---|
| [`README.md`](../README.md) | Quick-start entrypoint: what it is, why it exists, fastest path to first result |
| [`docs/project-brief.md`](project-brief.md) | Goals, non-goals, constraints, requirements — **read first for scope and constraints** |
| [`docs/system-patterns.md`](system-patterns.md) | Architecture patterns and conventions |
| [`docs/project-rules.md`](project-rules.md) | Language/tool specifics and QA commands |

## Full Document Index

### Core docs

| Document | Description |
|---|---|
| [`README.md`](../README.md) | Quick-start: installation, minimal usage example, links to details |
| [`docs/project-brief.md`](project-brief.md) | Goals, non-goals, constraints, requirements, out-of-scope items |
| [`docs/system-patterns.md`](system-patterns.md) | Component map, health-check loop, zone update flow, DNSSEC signing, multi-domain aliasing |
| [`docs/project-rules.md`](project-rules.md) | Python version, dependencies, test runner, coverage, linting, CI workflow |

### Reference docs

| Document | Description |
|---|---|
| [`docs/configuration.md`](configuration.md) | Full CLI argument and Docker environment variable reference with examples |

### Project files (non-docs)

| File | Purpose |
|---|---|
| [`AGENTS.md`](../AGENTS.md) | Agent contract: rules for AI coding agents working in this repository |
| [`Dockerfile`](../Dockerfile) | Multi-stage Docker build |
| [`docker-compose.example.yml`](../docker-compose.example.yml) | Example Docker Compose deployment |
| [`setup.py`](../setup.py) | Python package definition and entry point |
