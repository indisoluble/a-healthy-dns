# Table of Contents

Documentation index for **A Healthy DNS**.

This file is the navigation entry point for the documentation set. It defines the minimum reading set, the canonical owner for each major topic, and the shortest path to the right document for a given task.

When a topic appears in multiple documents, the canonical owner listed here is the source of truth. Other documents should keep that topic brief and link back to the canonical owner.

## How to Use This Index

1. Start with the minimum reading set before proposing or applying non-trivial changes.
2. Use canonical topic owners to find the single source of truth for a topic.
3. Use docs by change type to identify additional task-specific reading.
4. If you find duplicated substantive content, update the canonical owner first and reduce the other location to a short summary or link.

## Minimum Reading Set

These documents must be read before proposing or applying non-trivial changes to this repository.

| Document | Purpose |
|---|---|
| [`AGENTS.md`](../AGENTS.md) | Canonical repository agent contract |
| [`README.md`](../README.md) | Quick-start entry point: what the project is and how to run it for the first time |
| [`docs/project-brief.md`](project-brief.md) | Purpose, scope, goals, non-goals, target operators, and high-level capabilities |
| [`docs/requirements.md`](requirements.md) | Functional, operational, protocol, quality, reliability, security, deployment, and constraint requirements |
| [`docs/architecture.md`](architecture.md) | Runtime model, component boundaries, data flow, module layers, and file placement rules |
| [`docs/engineering-rules.md`](engineering-rules.md) | Repository-wide engineering principles, source-of-truth rules, and maintainability constraints |

## Canonical Topic Owners

Use this map when updating documentation: extend the canonical owner for the topic first, and keep mentions elsewhere brief and navigational.

| Topic | Canonical document | Scope boundary |
|---|---|---|
| Agent contract and repository-local agent behavior | [`AGENTS.md`](../AGENTS.md) | Agent workflow only; project behavior belongs in repository docs |
| Quick start, first successful run, and high-level orientation | [`README.md`](../README.md) | Keep short; long-form setup and reference content belongs in `docs/` |
| Purpose, goals, non-goals, target operators, and high-level capabilities | [`docs/project-brief.md`](project-brief.md) | Scope and positioning only; requirements live separately |
| Functional, operational, protocol, quality, reliability, security, deployment, and constraint requirements | [`docs/requirements.md`](requirements.md) | What must be true; avoid implementation rationale |
| Runtime model, concurrency model, data flow, folder hierarchy, and file placement rules | [`docs/architecture.md`](architecture.md) | Current structure and relationships; detailed process rules live elsewhere |
| Major design decisions, rationale, alternatives, and consequences | [`docs/decisions.md`](decisions.md) | Why durable choices were made; current structure remains in architecture |
| Repository-wide engineering principles and source-of-truth rules | [`docs/engineering-rules.md`](engineering-rules.md) | Implementation-independent maintainability rules |
| Python-specific implementation conventions | [`docs/implementation-notes.md`](implementation-notes.md) | Runtime, dependency, import, typing, logging, and module-level code conventions |
| Test strategy, QA commands, coverage, and test placement | [`docs/testing.md`](testing.md) | Validation expectations and local test commands |
| CI validation, release readiness, and documentation workflow | [`docs/workflow.md`](workflow.md) | How repository changes are validated, merged, and prepared for release |
| Versioning, release publication, artifacts, changelog, and compatibility | [`docs/release.md`](release.md) | Release publication rules; not development workflow |
| Authoritative UDP scope, wire-level behavior, and RFC conformance | [`docs/RFC-conformance.md`](RFC-conformance.md) | Protocol correctness and conformance status |
| CLI flags, defaults, and configuration examples | [`docs/configuration-reference.md`](configuration-reference.md) | Parameter definitions only |
| Docker runtime contract, Compose usage, deployment patterns, security hardening, and orchestrator notes | [`docs/docker.md`](docker.md) | Deployment guidance, not general troubleshooting |
| Troubleshooting, diagnostics, log interpretation, live debugging, monitoring, and incident handoff | [`docs/troubleshooting.md`](troubleshooting.md) | Diagnosis and runtime operations, not deployment setup |

## All Documents

### Project Foundation

- [`AGENTS.md`](../AGENTS.md) - canonical repository agent contract.
- [`README.md`](../README.md) - quick-start entry point.
- [`docs/project-brief.md`](project-brief.md) - purpose, scope, goals, non-goals, and capabilities.
- [`docs/requirements.md`](requirements.md) - system requirements and constraints.
- [`docs/architecture.md`](architecture.md) - current system structure and placement rules.
- [`docs/decisions.md`](decisions.md) - major design decisions and consequences.
- [`docs/engineering-rules.md`](engineering-rules.md) - engineering principles and source-of-truth rules.

### Engineering And Workflow

- [`docs/implementation-notes.md`](implementation-notes.md) - Python-specific implementation guidance.
- [`docs/testing.md`](testing.md) - test strategy, QA commands, and coverage expectations.
- [`docs/workflow.md`](workflow.md) - CI validation, release readiness, and documentation workflow.
- [`docs/release.md`](release.md) - versioning, release publication, artifacts, changelog, and compatibility.

### Reference And Operations

- [`docs/RFC-conformance.md`](RFC-conformance.md) - RFC conformance reference for the Level 1 authoritative UDP subset.
- [`docs/configuration-reference.md`](configuration-reference.md) - full CLI flag reference.
- [`docs/docker.md`](docker.md) - Docker deployment guide.
- [`docs/troubleshooting.md`](troubleshooting.md) - runtime diagnosis, log interpretation, live debugging, monitoring, and incident handoff.

## Docs by Change Type

| Change type | Additional docs to read |
|---|---|
| Quick-start path, first-run instructions, or project positioning | [`README.md`](../README.md), [`docs/project-brief.md`](project-brief.md) |
| Product scope, supported behavior, or non-goal decisions | [`docs/project-brief.md`](project-brief.md), [`docs/requirements.md`](requirements.md), [`docs/decisions.md`](decisions.md) when rationale changes, [`docs/RFC-conformance.md`](RFC-conformance.md) when DNS behavior is involved |
| Requirement, constraint, compatibility, reliability, security, or operational expectation | [`docs/requirements.md`](requirements.md) |
| New source file, new folder, architecture change, data flow, or module placement | [`docs/architecture.md`](architecture.md), [`docs/decisions.md`](decisions.md) when rationale changes, [`docs/engineering-rules.md`](engineering-rules.md) |
| Major design decision, alternative evaluation, or durable rationale | [`docs/decisions.md`](decisions.md) |
| Python runtime, dependencies, imports, module headers, logging, typing, validators, or class layout | [`docs/implementation-notes.md`](implementation-notes.md) |
| Health-check timing, alias-zone behavior, or DNSSEC design | [`docs/architecture.md`](architecture.md), [`docs/configuration-reference.md`](configuration-reference.md) when configuration surfaces change |
| CLI flag, default value, or configuration example | [`docs/configuration-reference.md`](configuration-reference.md), [`docs/requirements.md`](requirements.md) when behavior changes |
| Docker image, runtime contract, Compose, hardening, or upgrades | [`docs/docker.md`](docker.md), [`docs/engineering-rules.md`](engineering-rules.md) for repository-side build invariants |
| Operational issue, runtime diagnosis, log analysis, incident response, or monitoring | [`docs/troubleshooting.md`](troubleshooting.md) |
| DNS wire behavior, response codes, negative responses, or RFC scope | [`docs/RFC-conformance.md`](RFC-conformance.md), [`docs/requirements.md`](requirements.md) |
| Test additions, QA commands, test taxonomy, fixtures, or coverage expectations | [`docs/testing.md`](testing.md) |
| CI workflows, release readiness gates, or documentation workflow | [`docs/workflow.md`](workflow.md) |
| Versioning policy, release publication steps, artifacts, changelog, or compatibility | [`docs/release.md`](release.md) |
| Documentation restructuring or duplicate-topic cleanup | This file plus the canonical owner for the topic being cleaned up |
