# Engineering Rules

Repository-specific engineering rules for **A Healthy DNS**.

This document is the canonical home for implementation-independent engineering principles, source-of-truth rules, maintainability expectations, and repository-wide code-shape constraints. Python implementation details live in [`docs/implementation-notes.md`](implementation-notes.md); test strategy and commands live in [`docs/testing.md`](testing.md); CI and release workflow live in [`docs/workflow.md`](workflow.md); architecture and file placement live in [`docs/architecture.md`](architecture.md).

This document uses the [`AGENTS.md`](../AGENTS.md#3-terminology-and-task-classification) distinction between design invariants, current patterns, and examples. Design invariants are repository contracts. Current patterns are the default shape for new and touched work, but may be improved when the task explicitly includes that change and the update remains scoped, tested, documented, and compatible with higher-level requirements.

## Default Engineering Posture

- Prefer simple, explicit implementations over clever abstractions.
- Fix root causes rather than symptoms.
- Keep public interfaces small and explicit.
- Preserve single sources of truth for domain rules, schemas, constants, configuration defaults, timing formulas, and shared logic.
- Reuse an existing definition or extract a shared definition before duplicating values or behavior.
- Keep side effects visible at boundaries.
- Favor immutability for domain state where practical.
- Use dependency injection when it improves separation, clarity, or testability.
- Avoid unnecessary configurability, indirection, and abstraction.

## Changing Established Patterns

Established implementation shapes should be preserved by default, but not treated as untouchable when they are the problem being solved.

- Identify whether the affected guidance is a design invariant, current pattern, or example before changing it.
- Change a design invariant only when the task explicitly changes that contract. Update the relevant implementation, tests, requirements, architecture, decisions, and operational docs in the same change as needed.
- Change a current pattern when the replacement is simpler, clearer, better tested, or better aligned with documented requirements. Keep the change scoped to the affected behavior.
- Do not use pattern changes as a vehicle for unrelated cleanup, formatting sweeps, dependency updates, or broad rewrites.
- Preserve observable behavior unless the requested change explicitly changes it.
- State the rationale and the affected canonical documentation when a pattern is intentionally changed.

## Source-Of-Truth Rules

The table below is a set of design invariants for shared project facts. When a change alters one of these surfaces, update the implementation and the canonical documentation in the same change.

| Concern | Source of truth |
|---|---|
| Package version | `pyproject.toml:project.version` |
| Runtime dependencies | `pyproject.toml:project.dependencies` |
| CLI argument names and defaults | `indisoluble/a_healthy_dns/main.py` |
| Docker entrypoint | `Dockerfile` |
| Docker base-image strategy | `Dockerfile` plus D006 in [`docs/decisions.md`](decisions.md) |
| Docker runtime uid and key mount contract | R24 and R25 in [`docs/requirements.md`](requirements.md) plus [`docs/docker.md`](docker.md) |
| Docker privileged-port strategy | R24 in [`docs/requirements.md`](requirements.md), D008 in [`docs/decisions.md`](decisions.md), and [`docs/docker.md`](docker.md) |
| Configuration validation and assembly | `indisoluble/a_healthy_dns/dns_server_config_factory.py` |
| DNS timing formulas | `indisoluble/a_healthy_dns/records/time.py` plus `dns_server_zone_updater.py:_calculate_max_interval()` |
| Architecture and file placement | [`docs/architecture.md`](architecture.md) |
| Protocol conformance target | [`docs/RFC-conformance.md`](RFC-conformance.md) |
| Parameter reference | [`docs/configuration-reference.md`](configuration-reference.md) |

## Boundary Rules

These rules are design invariants for the current architecture. Changing them is an architecture change and must update [`docs/architecture.md`](architecture.md), affected tests, and any affected decisions or requirements.

- Follow the layer direction documented in [`docs/architecture.md`](architecture.md); lower layers must not import higher layers.
- Add new code at the lowest layer that can own the behavior.
- Keep DNS-specific logic out of `tools/`.
- Keep network I/O, threading, and configuration parsing out of `records/`.
- Keep the zone updater component as the only zone write owner.
- Keep each zone update inside one `dns.versioned.Zone` writer transaction.
- Keep query handling read-only with respect to zone state.
- Keep DNSSEC artifact-generation and signing logic isolated to `records/dnssec.py` and the `_sign_zone()` call in `DnsServerZoneUpdater`.
- Keep DNSSEC wire-response semantics and conformance boundaries owned by [`docs/RFC-conformance.md`](RFC-conformance.md).

## Testing Expectations

- Behavior changes require focused automated tests at the lowest useful level.
- Tests should document the expected contract through behavior-focused names, explicit setup/action/assertion shape, and observable outcomes.
- Unit tests must not make real network calls; mock `can_create_connection` or `socket.create_connection` when exercising health logic.
- Unit tests must avoid real time dependencies; mock `time.time`, `datetime.datetime.now`, or `uint32_current_time` as needed.
- Component integration tests may use real UDP sockets with pre-populated in-memory zone state.
- Docker end-to-end tests own the fully packaged health-check lifecycle.
- Use [`docs/testing.md`](testing.md) for concrete commands, test taxonomy, naming, and coverage expectations.

## Documentation Synchronization

- Keep code and documentation synchronized in the same change when behavior, interfaces, architecture, configuration, operations, workflow, or constraints change.
- Update the canonical owner listed in [`docs/table-of-contents.md`](table-of-contents.md) first, then keep other mentions brief and navigational.
- Avoid duplicating long-form content across documents.
- When documentation and implementation disagree, inspect the implementation and tests, then apply the repository source precedence in [`AGENTS.md`](../AGENTS.md#5-repository-source-precedence-and-conflicts) before deciding which source is stale. State material conflicts instead of silently reconciling them.

## Container Build Rules

These rules apply to repository-side changes in `Dockerfile`, `docker-compose.example.yml`, and Docker-related CI workflows. They are design invariants for the current deployment contract unless the task explicitly changes that contract. Operator deployment guidance lives in [`docs/docker.md`](docker.md).

- The final image uses the accepted hardened Chainguard Python base-image strategy from D006 in [`docs/decisions.md`](decisions.md) and runs as the Chainguard default non-root user, uid `65532`, avoiding custom user creation in the distroless runtime.
- Changing the base-image strategy, runtime uid, key mount, or privileged-port approach is a security/deployment contract change; update implementation, [`docs/docker.md`](docker.md), [`docs/requirements.md`](requirements.md), [`docs/decisions.md`](decisions.md), and affected deployment examples in the same change.
- `/app/keys` remains the mount point for DNSSEC private keys, owned by uid `65532` with restrictive permissions.
- Keep repository Docker and Compose examples aligned with the deployment contract in [`docs/docker.md`](docker.md) and R24 in [`docs/requirements.md`](requirements.md).
- Prefer examples that publish host port `53` to a non-privileged container listener when the process does not need to bind container port `53`.
- If a repository Docker, Compose, or CI example binds container port `53`, use `net.ipv4.ip_unprivileged_port_start=53` (or `=0`) in the network namespace where the DNS process binds as the primary approach. `NET_BIND_SERVICE` is only a runtime-specific fallback when the sysctl cannot be set and the runtime grants the capability effectively to the non-root process. See D008 in [`docs/decisions.md`](decisions.md).
- The image entrypoint runs `a-healthy-dns` directly; container runtime configuration is passed as CLI command arguments.
- Docker end-to-end coverage continues to use an isolated bridge network with a real backend container so health checks exercise an actual TCP connection.
