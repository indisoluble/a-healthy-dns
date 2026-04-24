# Table of Contents

Documentation index for **A Healthy DNS**.

This file is the navigation entrypoint for the documentation set. It defines:
- the minimum reading set required before making changes,
- the canonical owner for each major topic,
- and the shortest path to the right document for a given task.

When a topic appears in multiple documents, the canonical owner listed here is the source of truth. Other documents should keep that topic brief and link back to the canonical owner.

---

## How to use this index

1. Start with the **Minimum Reading Set** before proposing or applying changes.
2. Use **Canonical Topic Owners** to find the single source of truth for a topic.
3. Use **Docs by Change Type** to identify any additional reading for the task at hand.
4. If you find duplicated substantive content, update the canonical owner first and reduce the other location to a short summary or link.

---

## Minimum Reading Set

These documents must be read before proposing or applying changes to this repository.

| Document | Purpose |
|---|---|
| [`README.md`](../README.md) | Quick-start entrypoint: what the project is and how to run it for the first time |
| [`docs/project-brief.md`](project-brief.md) | Goals, non-goals, constraints, and requirements |
| [`docs/system-patterns.md`](system-patterns.md) | Architecture patterns, structural conventions, and folder hierarchy / codebase layout rules |
| [`docs/project-rules.md`](project-rules.md) | Language/tool specifics, QA workflow, CI/release rules, and code conventions |
| [`docs/RFC-conformance.md`](RFC-conformance.md) | Level 1 authoritative UDP conformance target: scope, minimum RFC set, current coverage per RFC, and broader-than-Level-1 scope limits |

---

## Canonical Topic Owners

Use this map when updating documentation: extend the canonical owner for the topic first, and keep mentions elsewhere brief and navigational.

| Topic | Canonical document | Scope boundary |
|---|---|---|
| Quick start, first successful run, and high-level orientation | [`README.md`](../README.md) | Keep short; long-form setup and reference content belong in `docs/` |
| Goals, non-goals, constraints, and requirements | [`docs/project-brief.md`](project-brief.md) | Scope and acceptance boundaries only |
| Architecture patterns, concurrency model, folder hierarchy, and file placement rules | [`docs/system-patterns.md`](system-patterns.md) | Structural and architectural decisions only |
| Toolchain, local setup, QA workflow, test conventions, CI/release policy, and repository-specific code conventions | [`docs/project-rules.md`](project-rules.md) | Repository workflow and code-shape rules only |
| Authoritative UDP scope, wire-level behavior, and RFC conformance | [`docs/RFC-conformance.md`](RFC-conformance.md) | Protocol correctness and conformance status only |
| CLI flags, Docker environment variables, defaults, and configuration examples | [`docs/configuration-reference.md`](configuration-reference.md) | Parameter definitions only |
| Docker runtime contract, Compose usage, deployment patterns, security hardening, and orchestrator notes | [`docs/docker.md`](docker.md) | Deployment guidance, not troubleshooting or general configuration reference |
| Troubleshooting, diagnostics, log interpretation, live debugging, monitoring, and incident handoff | [`docs/troubleshooting.md`](troubleshooting.md) | Diagnosis and runtime operations, not deployment setup |

---

## All Documents

### Project foundation

- [`README.md`](../README.md) — Quick-start entrypoint
- [`docs/project-brief.md`](project-brief.md) — Goals, non-goals, constraints, requirements
- [`docs/system-patterns.md`](system-patterns.md) — Architecture patterns, structural conventions, and folder hierarchy / codebase layout rules
- [`docs/project-rules.md`](project-rules.md) — Toolchain, QA workflow, CI/release rules, and code conventions

### Reference and operations

- [`docs/RFC-conformance.md`](RFC-conformance.md) — RFC conformance reference: minimum RFC set, current coverage per RFC, and broader-than-Level-1 scope limits for the Level 1 authoritative UDP subset
- [`docs/configuration-reference.md`](configuration-reference.md) — Full CLI and Docker environment variable reference
- [`docs/docker.md`](docker.md) — Docker deployment guide: runtime contract, quick start, Compose, hardening, and upgrades
- [`docs/troubleshooting.md`](troubleshooting.md) — Runtime diagnosis, log interpretation, live debugging, monitoring, and incident handoff

---

## Docs by Change Type

Use this table to identify which docs beyond the minimum reading set are relevant for a given task.

| Change type | Additional docs to read |
|---|---|
| Quick-start path, first-run instructions, or project positioning | [`README.md`](../README.md) |
| Product scope, supported behavior, or non-goal decisions | [`docs/project-brief.md`](project-brief.md), [`docs/RFC-conformance.md`](RFC-conformance.md) when DNS behavior is involved |
| New source file, new folder, architecture change, or module placement | [`docs/system-patterns.md`](system-patterns.md) |
| Health-check timing, alias-zone behavior, or DNSSEC design | [`docs/system-patterns.md`](system-patterns.md), [`docs/configuration-reference.md`](configuration-reference.md) when configuration surfaces change |
| CLI flag, Docker environment variable, default value, or configuration example | [`docs/configuration-reference.md`](configuration-reference.md) |
| Docker image, runtime contract, Compose, hardening, or upgrades | [`docs/docker.md`](docker.md) |
| Operational issue, runtime diagnosis, log analysis, incident response, or monitoring | [`docs/troubleshooting.md`](troubleshooting.md) |
| DNS wire behavior, response codes, negative responses, or RFC scope | [`docs/RFC-conformance.md`](RFC-conformance.md) |
| Test additions, QA workflow, naming rules, CI workflows, or release workflow | [`docs/project-rules.md`](project-rules.md) |
| Documentation restructuring or duplicate-topic cleanup | This file plus the canonical owner for the topic being cleaned up |

---

## Agent Contract

- [`AGENTS.md`](../AGENTS.md) — Canonical repository agent contract; applies to planning, implementation, refactoring, review, and documentation work
