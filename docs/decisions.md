# Decisions

Durable design decisions for **A Healthy DNS**.

This document is the canonical home for major decision rationale, alternatives, and consequences. It records why durable choices exist; current rules and detailed behavior remain with their topic owners. Current system structure lives in [`docs/architecture.md`](architecture.md); product scope lives in [`docs/project-brief.md`](project-brief.md); requirements live in [`docs/requirements.md`](requirements.md); workflow and release rules live in [`docs/workflow.md`](workflow.md) and [`docs/release.md`](release.md).

Only decisions supported by repository code, documentation, or commit history are recorded here. When earlier alternatives are not documented, this file says so instead of reconstructing intent.

## D001 - Serve An Authoritative UDP-Only DNS Scope

**Status:** accepted.

**Decision:** A Healthy DNS is an authoritative DNS server for one hosted zone plus optional alias zones, served over UDP. It does not implement recursive resolution, caching-resolver behavior, zone transfers, replication, traffic-shaping policy, or IPv6 answers.

**Rationale:** The project brief defines operational simplicity as a goal and explicitly limits scope to a single-process authoritative server. The RFC conformance document owns the Level 1 authoritative UDP behavior target.

**Alternatives considered:** not documented.

**Consequences:**

- This keeps protocol conformance focused on the authoritative UDP subset.
- Expanding beyond this scope requires an explicit decision update before implementation.
- Product scope remains in [`docs/project-brief.md`](project-brief.md), while wire-level behavior remains in [`docs/RFC-conformance.md`](RFC-conformance.md).

## D002 - Treat Static And Health-Checked A Records As First-Class Modes

**Status:** accepted.

**Decision:** Each configured subdomain uses one of two A-record modes in the same hosted zone: standard static records or health-checked records. Standard static entries use a bare IP list. Health-checked entries use an object with `ips` and `health_port`.

**Rationale:** The current product documentation says the project exists to preserve standard authoritative DNS behavior where desired while adding health-aware answers where automatic failover is needed.

**Alternatives considered:** not documented.

**Consequences:**

- Product-facing documentation distinguishes the two modes even if internal implementation shares machinery.
- Configuration syntax for both JSON shapes remains owned by [`docs/configuration-reference.md`](configuration-reference.md).
- Behavioral requirements for both modes remain owned by [`docs/requirements.md`](requirements.md).

## D003 - Represent Alias Zones As Lookup Aliases, Not Separate Zone State

**Status:** accepted.

**Decision:** Alias zones reuse the primary zone's records through `records/zone_origins.ZoneOrigins` and query-name relativization. Alias zones must not be represented as separate `dns.versioned.Zone` instances.

**Rationale:** Current documentation states alias zones should share the same records without duplicated health-check or record state.

**Alternatives considered:** separate zone state per alias is implicitly rejected by the current architecture rule. Other alternatives are not documented.

**Consequences:**

- Alias behavior stays tied to the primary zone's state instead of duplicating zone state.
- Current implementation structure remains owned by [`docs/architecture.md`](architecture.md).
- Behavioral requirements remain owned by [`docs/requirements.md`](requirements.md).

## D004 - Use Atomic `dns.versioned.Zone` Transactions For Zone State

**Status:** accepted.

**Decision:** Runtime DNS state is held in a shared `dns.versioned.Zone`. The zone updater owns writes through a single writer transaction, while UDP query handling remains read-only through zone readers.

**Rationale:** Current architecture documents the two-thread model and delegates concurrency safety to `dns.versioned.Zone` reader/writer semantics.

**Alternatives considered:** not documented.

**Consequences:**

- The implementation must preserve a single write path and read-only query handling.
- Current concurrency structure remains owned by [`docs/architecture.md`](architecture.md).
- Engineering rules for zone writes remain owned by [`docs/engineering-rules.md`](engineering-rules.md).

## D005 - Keep DNSSEC Optional And Isolated

**Status:** accepted.

**Decision:** DNSSEC signing is opt-in and treated as an isolated concern rather than a cross-cutting requirement for ordinary authoritative answers.

**Rationale:** Current architecture treats DNSSEC as additive behavior on top of base A, NS, and SOA records, avoiding DNSSEC awareness across unrelated layers.

**Alternatives considered:** not documented.

**Consequences:**

- Unsigned operation remains the default product posture.
- DNSSEC configuration details remain owned by [`docs/configuration-reference.md`](configuration-reference.md).
- Docker key-mount guidance remains owned by [`docs/docker.md`](docker.md).

## D006 - Use Docker As A First-Class Runtime Target

**Status:** accepted.

**Decision:** The project supports both direct Python CLI execution and Docker container deployment, with Docker treated as a first-class runtime target.

**Rationale:** Current requirements and Docker documentation define Docker as a supported deployment mode and document the runtime security contract.

**Alternatives considered:** Past history includes a Docker Hardened Image experiment that was reverted. Other alternatives are not documented.

**Consequences:**

- Docker remains a supported runtime rather than a convenience example only.
- Docker configuration uses the same CLI flags as direct process execution instead of a separate environment-variable mapping.
- Operator deployment guidance remains owned by [`docs/docker.md`](docker.md).
- Repository-side container invariants remain owned by [`docs/engineering-rules.md`](engineering-rules.md).

## D007 - Automate Versioned Release Publication

**Status:** accepted.

**Decision:** Versioned release publication is automated through the repository CI chain rather than performed manually.

**Rationale:** Current workflow and release documentation define an automated release chain and avoid manual tagging or Docker Hub pushes.

**Alternatives considered:** manual tagging and manual Docker Hub pushes are explicitly rejected by current release documentation. Other alternatives are not documented.

**Consequences:**

- Release publication remains automation-owned rather than operator-owned.
- Versioning and publication rules remain owned by [`docs/release.md`](release.md).
- CI validation behavior remains owned by [`docs/workflow.md`](workflow.md).

## D008 - Use Network-Namespace Sysctl As The Canonical Privileged-Port Binding Strategy

**Status:** accepted.

**Decision:** The image must not gain privileged-port binding mechanics: no `setcap`, no `libcap`, no additional build stage, and no root runtime user. Standard DNS exposure should avoid process-level privileged binding when runtime port publishing can map host port `53` to a non-privileged listener port. When the DNS process itself must bind port `53`, `net.ipv4.ip_unprivileged_port_start=53` (or `=0`) set in the network namespace where the process binds is the canonical strategy. `NET_BIND_SERVICE` remains a runtime-specific fallback only when the runtime grants it effectively to the non-root process. Exact Docker, Compose, Kubernetes, and ECS deployment procedures live in [`docs/docker.md`](docker.md).

**Rationale:** `net.ipv4.ip_unprivileged_port_start` is a network-namespace sysctl. Applying it to the namespace where the process binds requires no image modification, is fully compatible with `no-new-privileges: true`, is the standard mechanism in Kubernetes for non-hostNetwork pods (`securityContext.sysctls`), and eliminates the need for any Linux capability inside the container when the sysctl can be set. When bridge-mode port publishing can map host port `53` to container port `53053`, the process never performs a privileged bind and no privileged-port mechanism is needed inside the container. The capability path is more fragile: Linux checks the effective capability set, and a non-root exec path does not automatically make `NET_BIND_SERVICE` effective merely because a container manifest names it. Some runtimes can deliver an effective capability to a non-root process; others may leave it only in bounding/permitted state, especially across older Docker or Kubernetes combinations. Baked-in file capabilities (`setcap cap_net_bind_service=+ep`) would make that promotion explicit but require an extra build stage and a non-distroless base layer, complicating the build and supply-chain properties of the image.

**Alternatives considered:**

- `setcap cap_net_bind_service=+ep` on the binary (file capability): rejected because it requires an extra Alpine or similar build stage and changes the image, breaking the clean two-stage Chainguard build.
- `NET_BIND_SERVICE` at runtime only: accepted only as a runtime-specific fallback for shared or restricted environments where the sysctl cannot be set and the runtime is known to grant `CAP_NET_BIND_SERVICE` effectively to the non-root process.

**Consequences:**

- The Dockerfile is not modified for privileged-port binding.
- `no-new-privileges: true` remains a baseline hardening requirement in all deployment examples.
- Repository Docker and Compose examples prefer publishing host port `53` to a non-privileged container listener when the process does not need to bind container port `53`.
- `net.ipv4.ip_unprivileged_port_start=53` becomes the documented primary prerequisite for port-53 binding without capabilities in the network namespace where the process binds.
- `NET_BIND_SERVICE` is documented only as a runtime-specific fallback when the sysctl cannot be set and the runtime makes the capability effective for the non-root process.
- Operators who use the capability fallback must verify the running process has `CAP_NET_BIND_SERVICE` in its effective capability set; this image does not include a file capability on the Python interpreter or console-script entry point.
- Operator deployment guidance and updated examples live in [`docs/docker.md`](docker.md).
- The security requirement is owned by [`docs/requirements.md`](requirements.md) (R23); repository-side container rules are owned by [`docs/engineering-rules.md`](engineering-rules.md).
