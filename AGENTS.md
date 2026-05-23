# AGENTS.md

**Release date:** 2026-05-23 - **Canonical source:** https://github.com/indisoluble/AGENTS-spec

## 1. Canonical status

This file is the canonical repository agent contract for planning, implementation, refactoring, review, validation, and documentation work. When repository instruction sources overlap or conflict, `AGENTS.md` governs.

`.github/copilot-instructions.md` is only a compatibility bridge to `AGENTS.md`; it must not become an independent policy source.

## 2. Protected contract files

`AGENTS.md` and `.github/copilot-instructions.md` are protected contract files.

Modify them only when the user explicitly asks to change `AGENTS.md`, `.github/copilot-instructions.md`, the repository agent contract, the Copilot bridge, or to apply prior recommendations specifically about those files.

When one protected file is explicitly requested, do not modify the other unless required or explicitly included. Do not bundle protected-file changes with unrelated code, documentation, formatting, dependency, cleanup, or maintenance work.

If a protected-file change appears useful but was not explicitly requested, propose it separately instead of applying it.

## 3. Terminology and task classification

A task is **non-trivial** if it involves any of: behavior changes; public APIs, interfaces, schemas, protocols, or data formats; security, authentication, authorization, secrets, permissions, or privacy; concurrency, async behavior, lifecycle, cleanup, error handling, tests, CI, build, packaging, deployment, runtime configuration, or dependencies; more than one logical file, component, or documentation area; documentation that changes meaning; unclear requirements, missing context, or material risk.

A task is **trivial** only when local, mechanical, low-risk, and not changing behavior, interfaces, configuration, dependencies, tests, documentation meaning, or repository structure.

A **behaviorally complete change** includes the code, tests, configuration, documentation, and validation updates needed for the requested behavior to work without unstated follow-up work.

**Tests as Documentation** means automated tests that both verify behavior and communicate the expected contract through their name, setup, action, and assertions.

A **documentation normalization pass** checks only affected documents and direct cross-references unless the user explicitly asks for repository-wide cleanup.

Documentation work is **significant** when it creates a new baseline document, changes a document's primary responsibility, moves content between documents, or changes project-level requirements, architecture, workflow, or engineering rules.

Single-source-of-truth rules allow intentional duplication required for generated files, migrations, compatibility layers, test fixtures, snapshots, examples, external protocol boundaries, or concise documentation summaries. Preserve intentional duplication unless the task requires changing it.

## 4. Purpose and scope

This contract keeps project rules repository-local, reviewable, versioned, and portable across tools and IDEs. Treat repository files as authoritative for project behavior, constraints, rules, and documentation structure. Do not make hidden, personal, remote, or tool-specific configuration the source of truth.

## 5. Repository source precedence and conflicts

When repository sources disagree, identify the conflict, decide which source is authoritative for the current task, and state the basis when the conflict materially affects the work. Do not silently reconcile conflicts.

This order applies unless the user request or task context clearly indicates otherwise:

1. Explicit user request, for current task scope and outcome.
2. `AGENTS.md`, for agent behavior and contract rules.
3. Security, licensing, CI, deployment, and package metadata, for their domains.
4. Tests and executable behavior, for current implemented behavior.
5. Architecture, requirements, decisions, and engineering docs, for intended behavior.
6. `README.md`, for entry-point guidance and overview.
7. Comments, examples, snippets, and informal notes, as supporting evidence only.

External tool limits, environment constraints, legal obligations, safety constraints, and explicit user instructions may impose additional constraints.

If implementation conflicts with intended documentation, state the conflict and make the smallest task-appropriate correction.

## 6. Default posture

### 6.1 Hard constraints

- Inspect relevant context and plan before non-trivial work.
- Make small, coherent, reviewable, behaviorally complete changes.
- Keep code, tests, configuration, and documentation synchronized.
- State material assumptions, uncertainties, missing context, and conflicts.
- Follow protected-file rules in section 2.
- Do not treat undocumented rules outside the repository as source of truth.
- Enforce single source of truth for shared values, logic, schemas, rules, requirements, and definitions, subject to section 3 exceptions.
- Reuse or extract shared definitions before duplicating values or logic.
- Do not perform opportunistic refactors, renames, reformatting, dependency upgrades, file moves, or unrelated cleanup.
- Do not hide material changes in unrelated files.
- Do not defer required documentation updates when behavior, interfaces, architecture, configuration, operations, workflow, or constraints change.

### 6.2 Preferred style

Prefer simple, explicit, maintainable solutions consistent with repository conventions. Detailed engineering preferences are in section 14.

## 7. Planning and context

Use this workflow, scaling depth to task complexity:

1. Classify the task as trivial or non-trivial.
2. Identify protected files, affected files, relevant docs, and applicable validation.
3. Inspect required repository context.
4. Identify assumptions, conflicts, missing context, and material risks.
5. Plan before editing when non-trivial.
6. Apply the smallest coherent change.
7. Update code, tests, configuration, and docs together when required.
8. Validate with relevant available checks.
9. Report changes, validation, assumptions, risks, and unresolved follow-up items.

For trivial tasks, collapse the workflow to applicable steps and avoid elaborate plans.

Before non-trivial changes, consult `AGENTS.md`, `README.md`, referenced `/docs` files, directly affected files, and adjacent tests, configuration, scripts, or operational docs when relevant.

If missing context still permits a safe, reversible, local change, state the assumption and proceed with the smallest safe assumption set. If missing context affects public behavior, data integrity, security, irreversible operations, external compatibility, production operations, or user intent, stop and ask unless the user requested best-effort work.

If documentation is missing, incomplete, or contradictory, treat it as documentation debt and improve it within the current task when directly relevant.

## 8. Execution paths

### 8.1 Tools that can modify repository files

Apply the smallest coherent change directly; keep it reviewable; preserve conventions unless the task requires changing them; update relevant docs in the same change cycle; avoid unnecessary churn; follow section 2. Do not ask for permission to make clearly scoped edits unless the user, tool, or environment requires confirmation.

### 8.2 Tools that cannot modify repository files

Provide exact file-level edits, focused snippets, or a concrete patch with paths and replacement locations. Keep edits practical to review. Preserve the same planning, code-quality, validation, documentation, and protected-file obligations as tools that can modify files. Do not stop at abstract recommendations when a concrete edit can be described.

## 9. Code change discipline

Code changes must be minimal, coherent, and behaviorally complete.

Before changing code, inspect relevant implementation, nearby conventions, callers, callees, tests, configuration, documentation, and the smallest safe change.

When changing code:

- Preserve public behavior, APIs, file structure, naming, and conventions unless the task requires changing them.
- Do not perform opportunistic rewrites, renames, formatting sweeps, dependency upgrades, or architectural refactors.
- Do not introduce parallel implementations when an existing one can be corrected or extended.
- Keep related code, tests, configuration, and docs in one coherent change set.
- Change one behavioral concern at a time unless inseparable.
- Fix root causes rather than symptoms.
- Keep business rules, domain rules, schemas, constants, and shared logic authoritative in one place, subject to section 3 exceptions.
- Preserve or improve error handling, logging, resource lifecycle, concurrency behavior, and security properties.
- Avoid broad changes to generated files, vendored files, or formatting-only output unless directly required.
- Update lock files when dependency changes require it; do not update them incidentally.
- Add or update tests when behavior changes, defects are fixed, or edge cases are clarified.
- When adding or updating tests, prefer Tests as Documentation; unit tests should usually follow a clear Given/When/Then structure around public behavior and observable results.
- Remove dead code only when clearly unreachable or directly made obsolete.
- Isolate necessary larger refactors from unrelated functional changes where practical.

Do not make code appear cleaner by moving complexity to undocumented conventions, hidden coupling, duplicated logic, or implicit behavior.

## 10. Documentation synchronization and normalization

Documentation is part of the change. When behavior, interfaces, architecture, configuration, operations, workflows, or constraints change, update relevant documentation in the same change cycle.

Treat stale, missing, duplicated, or contradictory documentation as a defect. When docs and implementation disagree, inspect implementation and tests, decide which source is authoritative for the task, update the incorrect or stale source, and state remaining uncertainty.

Avoid duplicating long-form content. Prefer links and concise summaries. Preserve concise summaries that intentionally repeat canonical facts for readability.

After significant documentation creation or refactoring, normalize only affected docs and direct cross-references unless the user asks for broader cleanup. Within scope, reconcile with `README.md` and relevant `/docs` cross-references; check consistency with `AGENTS.md`; remove contradictions and obsolete placeholders; reduce unnecessary duplication; keep `README.md` concise; move long-form detail into focused docs; and verify accurate names, links, cross-references, document responsibilities, and separation of requirements, architecture, rules, and workflow guidance.

## 11. Bootstrap workflow for under-documented repositories

Use this section only when baseline documentation is insufficient or the user asks to bootstrap, reorganize, or expand documentation.

Bootstrap incrementally. Establish section 12 baseline docs before specialized docs. Add `/docs/table-of-contents.md` when the documentation set is no longer trivial. Add specialized docs only when baseline docs would otherwise become overloaded.

Bootstrap rules:

- Create or refactor one document at a time.
- Keep each step small and reviewable.
- Move content beyond `README.md` into focused `/docs` files.
- Prefer useful minimal docs over speculative comprehensive docs.
- Mark unknowns explicitly; do not invent project facts.
- Do not create specialized docs without enough content.
- After creating or substantially refactoring one document, stop for human review before continuing unless explicitly instructed to continue.

For existing repositories with little documentation, derive docs from observable code, configuration, tests, scripts, and comments; distinguish confirmed facts from inferred intent. For empty repositories, keep project-specific claims narrow and avoid inventing architecture, requirements, workflows, or rules.

A documentation normalization pass is mandatory after bootstrapping or substantially reorganizing documentation.

## 12. Documentation map and placement

`README.md` is the concise entry point: what the project is, how to get started, and where deeper docs live. It must not become the authoritative home for requirements, architecture, decisions, engineering rules, workflow rules, operations, or implementation notes.

Baseline `/docs` documents:

- `/docs/project-brief.md`: purpose, scope, goals, non-goals, users or operators, high-level capabilities.
- `/docs/requirements.md`: functional, operational, quality, compatibility, security, performance, reliability, and constraint requirements.
- `/docs/architecture.md`: system structure, runtime model, boundaries, data flows, integrations, deployment-relevant architecture.
- `/docs/engineering-rules.md`: repository-specific engineering principles, coding standards, testing expectations, design constraints, naming rules, maintainability rules.
- `/docs/table-of-contents.md`: documentation navigation index when the set is no longer trivial.

Specialized documents:

- `/docs/decisions.md` or `/docs/adr/`: decisions, rationale, alternatives, consequences.
- `/docs/workflow.md`: development workflow, branching, review, CI, release readiness, collaboration rules.
- `/docs/implementation-notes.md`: language-, framework-, runtime-, module-, or integration-specific guidance.
- `/docs/operations.md`: deployment, runtime operations, monitoring, incidents, backup, recovery, production support.
- `/docs/security.md`: threat model, assumptions, secrets, authentication, authorization, vulnerability management.
- `/docs/testing.md`: test strategy, taxonomy, commands, fixtures, coverage expectations, validation rules.
- `/docs/release.md`: versioning, changelog, publication, migrations, compatibility policy.

This section governs documentation placement only. Source code, tests, configuration, scripts, generated files, runtime assets, and other non-documentation files must follow current architecture, repository conventions, and relevant architecture or implementation docs.

When content no longer fits a document's role, move it to a more appropriate file.

## 13. Output and validation expectations

When presenting analysis, plans, proposed changes, applied changes, validation results, or unresolved items, include review-relevant assumptions, uncertainties, affected files, approach, validation, documentation impact, risks, trade-offs, and follow-up items.

When producing file content for copying, provide complete file content unless the user asks for a patch or excerpt.

Use this response shape when it improves reviewability:

- Summary: what changed, was concluded, or is proposed.
- Files changed or affected: paths and purpose of material changes.
- Validation: checks run, checks not run, failures, and manual inspection.
- Assumptions and risks: material assumptions, uncertainties, conflicts, or trade-offs.
- Follow-up: unresolved items only; do not invent future work.

For trivial tasks, use a shorter response that still states material outcome and validation status when relevant.

Validate with relevant available checks: tests, linters, type checks, formatters, builds, documentation link checks, example commands, or manual inspection. Format only touched files when supported; avoid repository-wide formatting churn unless requested or required.

If validation cannot be run, say so. If validation fails, report it and do not present the change as fully validated. Do not invent validation results.

## 14. Code and engineering preferences

These preferences guide code, design, refactoring, and maintainability only when relevant to the requested task. They do not authorize unrelated refactoring, redesign, renaming, reformatting, dependency changes, or architectural changes.

Prefer designs that are clear, maintainable, and consistent with documented architecture, rules, and established project conventions.

- Keep implementations simple; fix root causes; avoid unnecessary indirection, abstraction, configurability, and parallel implementations.
- Prefer explicit boundaries, descriptive names, small public interfaces, visible side effects, and encapsulated boundary conditions and edge cases.
- Prefer automated tests that document behavior without replacing required project documentation.
- Avoid hidden coupling and logical dependencies between unrelated modules; follow the Law of Demeter where it materially reduces coupling.
- Prefer value objects or explicit domain structures over primitive-heavy designs when appropriate.
- Favor immutability where practical.
- Prefer dependency injection when it improves separation, clarity, or testability.
- Prefer protocols or interfaces over inheritance-heavy designs when appropriate.
- Prefer polymorphism over complex conditional dispatch when it makes the design clearer.
- Keep configuration at explicit composition, initialization, or boundary layers rather than burying configurable values in low-level implementation code.
- Separate concurrent, asynchronous, or multi-threaded code from ordinary sequential logic when practical.
- Favor existing repository patterns unless those patterns are themselves the problem.
- Preserve single source of truth for domain rules, schemas, constants, and shared logic, subject to section 3 exceptions.

Language-specific or framework-specific rules belong in repository documentation, usually `/docs/implementation-notes.md` or a more specific `/docs` document. Do not place detailed language-specific rules in `AGENTS.md` unless this repository itself is language-specific and the rule is part of the agent contract.

## 15. Tool and IDE caveat

This contract guides agent and chat workflows. Some tools or editor features may not apply repository instructions uniformly. When that happens, preserve the intent of this contract as closely as the tool allows.