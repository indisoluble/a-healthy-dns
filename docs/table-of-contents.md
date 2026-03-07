# Documentation Table of Contents

This file is the index for the project documentation set. The minimum reading
set below is the current baseline for implementation and documentation changes.
`README.md` is the quick-start entrypoint, and the long-form docs under `docs/`
are the source of truth for configuration, operations, architecture, and
workflow detail.

## Minimum Reading Set

Read these first before changing implementation or documentation:

- [`README.md`](../README.md) - Current product entrypoint and fastest first-run
  path.
- [`docs/table-of-contents.md`](./table-of-contents.md) - Documentation index,
  reading order, and current baseline.
- [`docs/project-brief.md`](./project-brief.md) - Accepted product scope,
  constraints, and intended use cases.
- [`docs/system-patterns.md`](./system-patterns.md) - Accepted runtime
  architecture, component boundaries, and request/update flow.
- [`docs/project-rules.md`](./project-rules.md) - Accepted development
  workflow, QA commands, and packaging conventions.
- [`docs/configuration-reference.md`](./configuration-reference.md) - Accepted
  CLI and Docker configuration contract, defaults, and validation rules.
- [`docs/deployment-and-operations.md`](./deployment-and-operations.md) -
  Accepted deployment modes, runtime operations, and troubleshooting workflow.

## Current Docs

### Available Now

- [`README.md`](../README.md) - Project overview, fastest first-run path, and
  links to long-form docs.
- [`docs/project-brief.md`](./project-brief.md) - Product scope, goals,
  non-goals, operational constraints, and intended users.
- [`docs/system-patterns.md`](./system-patterns.md) - Runtime architecture,
  component responsibilities, and request/update flow.
- [`docs/project-rules.md`](./project-rules.md) - Development workflow, QA
  commands, packaging/runtime conventions, and documentation maintenance rules.
- [`docs/configuration-reference.md`](./configuration-reference.md) - CLI
  arguments, Docker environment variables, JSON payload shapes, defaults, and
  validation rules.
- [`docs/deployment-and-operations.md`](./deployment-and-operations.md) - Docker
  deployment, runtime behavior, logging, smoke tests, and troubleshooting.
- [`AGENTS.md`](../AGENTS.md) - Repository workflow and documentation bootstrap
  rules for coding agents.

## Core Docs

These are the baseline long-form docs for this repository.

- [`docs/project-brief.md`](./project-brief.md) - Product goals, non-goals,
  constraints, supported use cases, and scope boundaries.
- [`docs/system-patterns.md`](./system-patterns.md) - Runtime architecture,
  major components, and the request/update flow from CLI input to DNS answers.
- [`docs/project-rules.md`](./project-rules.md) - Development workflow, QA
  commands, packaging/runtime conventions, and documentation maintenance rules.

## Focused Docs

These are expected to be useful based on the current implementation surface.

- [`docs/configuration-reference.md`](./configuration-reference.md) - CLI
  arguments, JSON payload schema, Docker environment variables, defaults,
  validation rules, and examples.
- [`docs/deployment-and-operations.md`](./deployment-and-operations.md) - Docker
  deployment, privileged port binding, DNSSEC key mounting, logging, runtime
  behavior, and troubleshooting.

## Task-Oriented Reading

- First run or local install: [`README.md`](../README.md)
- Configuration changes: [`docs/configuration-reference.md`](./configuration-reference.md)
- Deployment and troubleshooting: [`docs/deployment-and-operations.md`](./deployment-and-operations.md)
- Product scope and constraints: [`docs/project-brief.md`](./project-brief.md)
- Runtime or architecture changes: [`docs/project-brief.md`](./project-brief.md)
  plus [`docs/system-patterns.md`](./system-patterns.md)
- Agent workflow: [`AGENTS.md`](../AGENTS.md) plus
  [`docs/project-rules.md`](./project-rules.md)

## Bootstrap Order

This sequence is complete and kept as a record of the bootstrap order.

1. `docs/table-of-contents.md`
2. `docs/project-brief.md`
3. `docs/system-patterns.md`
4. `docs/project-rules.md`
5. `docs/configuration-reference.md`
6. `docs/deployment-and-operations.md`
7. `README.md`
8. Final cross-document normalization pass

## Maintenance Notes

- Keep `README.md` short once the long-form docs above exist.
- The baseline bootstrap document set is complete; future docs changes should be
  incremental updates to this structure.
- When a planned document is created and accepted, register it here and add it
  to the minimum reading set if it affects implementation decisions.
