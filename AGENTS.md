# AGENTS.md

**Release date:** 2026-05-01 - **Canonical source:** https://github.com/indisoluble/AGENTS-spec

## 1. Canonical status

This file is the canonical repository agent contract.

It applies to planning, implementation, refactoring, review, validation, and documentation work in this repository.

When repository instruction sources overlap or conflict, `AGENTS.md` governs.

`.github/copilot-instructions.md` is a compatibility bridge only. It must point to `AGENTS.md` and must not become an independent policy source.

## 2. Protected contract files

`AGENTS.md` and `.github/copilot-instructions.md` are protected repository contract files.

Do not modify them unless the user explicitly asks to change the repository agent contract or Copilot bridge.

Do not bundle protected contract-file changes with unrelated code, documentation, formatting, dependency, cleanup, or repository-maintenance work.

When a protected contract-file change appears useful but was not explicitly requested, describe the proposed change separately instead of applying it.

## 3. Purpose and scope

This repository carries its own agent-operating contract so project rules remain repository-local, reviewable, versioned, and portable across tools and IDEs.

This contract supports normal development workflows without making hidden, personal, remote, or tool-specific configuration the source of truth.

Agents must treat repository files as the authoritative source for project behavior, constraints, rules, and documentation structure.

## 4. Default posture

### 4.1 Hard constraints

- Inspect the relevant repository context before acting on non-trivial work.
- Plan before editing for non-trivial work.
- Make small, coherent, reviewable changes.
- Keep code, tests, configuration, and documentation synchronized.
- State assumptions, uncertainties, and missing context explicitly.
- Treat `AGENTS.md` and `.github/copilot-instructions.md` as protected contract files.
- Do not modify protected contract files unless explicitly requested.
- Do not treat undocumented rules outside the repository as the source of truth.
- Enforce single source of truth for shared values, logic, schemas, rules, requirements, and definitions.
- Reuse an existing definition or extract a shared definition before duplicating values or logic.
- Prefer minimal, behaviorally complete code changes over broad rewrites.
- Do not perform opportunistic refactors, renames, reformatting, dependency upgrades, or file moves outside the task scope.
- Do not hide material changes in unrelated files.
- Do not defer required documentation updates when the current change alters behavior, interfaces, architecture, configuration, operations, workflow, or constraints.

### 4.2 Preferred style

- Prefer simple solutions over clever ones.
- Fix root causes rather than symptoms.
- Prefer clear names and explicit boundaries.
- Favor immutability where practical.
- Prefer protocols or interfaces over inheritance-heavy designs when appropriate.
- Use dependency injection where it improves separation, clarity, or testability.
- Avoid unnecessary configurability and unnecessary abstraction.
- Keep behavior discoverable in repository files.
- Keep documents concise, focused, and internally consistent.

## 5. Planning and context

For non-trivial tasks:

- understand the request and constraints
- inspect relevant repository context
- identify assumptions, unknowns, and risks
- produce a plan before making changes
- separate investigation, implementation, validation, and documentation work
- identify the files or areas likely to change
- keep the plan reviewable

Before proposing or applying non-trivial changes, consult:

- `AGENTS.md`
- `README.md`
- explicitly referenced documents under `/docs`
- files directly affected by the task
- adjacent tests, configuration, scripts, or operational documents when relevant

Scale planning depth to task complexity.

Do not produce elaborate plans for trivial tasks.

Do not use planning as a substitute for making a concrete change when the change is clear and safe.

If essential context is missing, state that explicitly and proceed using the smallest safe assumption set.

If repository documentation is missing, incomplete, or contradictory, treat that as documentation debt and improve it within the current task when doing so is directly relevant.

## 6. Execution paths

### 6.1 Tools that can modify repository files

- Apply the smallest coherent change directly.
- Keep the change set reviewable.
- Update relevant documentation in the same change cycle when needed.
- Avoid unnecessary churn outside the task scope.
- Preserve existing conventions unless the task requires changing them.
- Do not modify protected contract files unless explicitly requested.
- Do not ask for permission to make clearly scoped repository edits unless the user, tool, or environment requires confirmation.

### 6.2 Tools that cannot modify repository files

- Provide exact file-level edits, focused snippets, or a concrete patch.
- Make intended file paths and replacement locations explicit.
- Keep proposed edits small enough for practical review.
- Preserve the same planning, code-quality, validation, and documentation obligations as tools that can modify files directly.
- Do not stop at abstract recommendations when a concrete edit can be described.
- Do not propose protected contract-file edits unless explicitly requested.

## 7. Code change discipline

Code changes must be minimal, coherent, and behaviorally complete.

Before changing code:

- inspect the relevant implementation
- inspect nearby code that establishes local conventions
- inspect callers, callees, tests, configuration, and documentation when relevant
- identify the smallest safe change that satisfies the task

When changing code:

- Preserve existing public behavior, APIs, file structure, naming, and conventions unless the task requires changing them.
- Do not perform opportunistic rewrites, renames, formatting sweeps, dependency upgrades, or architectural refactors.
- Do not introduce parallel implementations when an existing implementation can be corrected or extended.
- Keep related code, tests, configuration, and documentation changes in the same coherent change set.
- Change one behavioral concern at a time unless the concerns are inseparable.
- Prefer fixing the root cause over adding compensating logic around the symptom.
- Keep business rules, domain rules, schemas, constants, and shared logic in one authoritative place.
- Preserve or improve error handling, logging, resource lifecycle, concurrency behavior, and security properties.
- Avoid broad changes to generated files, vendored files, lock files, or formatting-only output unless directly required.
- Add or update tests when behavior changes, defects are fixed, or edge cases are clarified.
- Remove dead code only when it is clearly unreachable or directly made obsolete by the current change.
- If a larger refactor is necessary, isolate it from unrelated functional changes where practical.

Do not make code appear cleaner by moving complexity to undocumented conventions, hidden coupling, duplicated logic, or implicit behavior.

## 8. Documentation synchronization and normalization

Documentation is part of the change, not an optional follow-up.

When a change affects behavior, interfaces, architecture, configuration, operations, workflows, or constraints, update the relevant documentation in the same change cycle.

Treat stale, missing, duplicated, or contradictory documentation as a defect.

When documentation and implementation disagree:

- inspect the relevant implementation and tests
- determine whether the implementation or documentation is authoritative for the current task
- update the incorrect or stale source
- state any remaining uncertainty

Avoid duplicating long-form content across documents. Prefer links and concise summaries.

After significant documentation creation or refactoring, perform a documentation normalization pass.

Do not perform broad documentation reorganization during ordinary code changes. Normalize only the documents affected by the current task unless the user explicitly asks for broader documentation cleanup.

A documentation normalization pass must:

- reconcile `README.md` and `/docs`
- check consistency with `AGENTS.md`
- remove contradictions and obsolete placeholders
- reduce unnecessary duplication
- keep `README.md` concise and entry-point oriented
- move long-form detail into focused documentation files
- verify that each document has one primary responsibility
- verify that document names, links, and cross-references are accurate
- verify that requirements, architecture, rules, and workflow guidance are not mixed unnecessarily

## 9. Bootstrap workflow for under-documented repositories

Use this section only when the repository lacks sufficient baseline documentation or when the user explicitly asks to bootstrap, reorganize, or expand repository documentation.

Bootstrap documentation incrementally.

Establish at minimum:

- `README.md`
- `/docs/project-brief.md`
- `/docs/requirements.md`
- `/docs/architecture.md`
- `/docs/engineering-rules.md`

Add `/docs/table-of-contents.md` when the documentation set is no longer trivial.

Add specialized documents only when the baseline documents would otherwise become overloaded.

Common specialized documents include:

- `/docs/decisions.md` or `/docs/adr/`
- `/docs/workflow.md`
- `/docs/implementation-notes.md`
- `/docs/operations.md`
- `/docs/security.md`
- `/docs/testing.md`
- `/docs/release.md`

Bootstrap rules:

- Create or refactor one document at a time.
- Keep each step small and reviewable.
- Prioritize baseline documents before specialized documents.
- Move content beyond the role of `README.md` into focused documents under `/docs`.
- Prefer a useful minimal document over a speculative comprehensive document.
- Mark unknowns explicitly instead of inventing project facts.
- Do not create a specialized document unless there is enough content to justify its existence.
- After creating or substantially refactoring one document, stop and let the human review the diff before continuing to the next bootstrap document, unless explicitly instructed to continue.

For existing repositories with code but little or no documentation, derive documentation from observable code, configuration, tests, scripts, and comments. Distinguish confirmed facts from inferred intent.

For empty or nearly empty repositories, keep project-specific claims narrow and avoid inventing architecture, requirements, workflows, or implementation rules that the repository does not yet support.

A documentation normalization pass is mandatory after bootstrapping or substantially reorganizing repository documentation.

## 10. Documentation map and placement

Use each repository document for a distinct purpose.

`README.md` is the concise project entry point. It should explain what the project is, how to get started, and where deeper documentation lives. It must not become the authoritative home for requirements, architecture, design decisions, engineering rules, workflow rules, operations, or implementation notes.

Baseline `/docs` documents:

- `/docs/project-brief.md`: purpose, scope, goals, non-goals, users or operators, and high-level capabilities.
- `/docs/requirements.md`: functional, operational, quality, compatibility, security, performance, reliability, and constraint requirements.
- `/docs/architecture.md`: current system structure, runtime model, component boundaries, data flows, integrations, and deployment-relevant architecture.
- `/docs/engineering-rules.md`: repository-specific engineering principles, coding standards, testing expectations, design constraints, naming rules, and maintainability rules.
- `/docs/table-of-contents.md`: documentation navigation index when the documentation set is no longer trivial.

Specialized documents:

- `/docs/decisions.md` or `/docs/adr/`: major architectural and design decisions, rationale, alternatives, and consequences.
- `/docs/workflow.md`: development workflow, branching, review, CI, release readiness, and collaboration rules.
- `/docs/implementation-notes.md`: language-specific, framework-specific, runtime-specific, module-specific, or integration-specific guidance.
- `/docs/operations.md`: deployment, runtime operations, monitoring, incident response, backup, recovery, and production support.
- `/docs/security.md`: threat model, security assumptions, secrets handling, authentication, authorization, and vulnerability management.
- `/docs/testing.md`: test strategy, test taxonomy, required commands, fixtures, coverage expectations, and validation rules.
- `/docs/release.md`: versioning, changelog, release publication, artifact publication, migration notes, and compatibility policy.

This section governs documentation placement only.

Placement of source code, tests, configuration, scripts, generated files, runtime assets, and other non-documentation files must follow the current architecture, repository conventions, and relevant architecture or implementation documentation.

Documentation placement rules:

- Put requirements in `/docs/requirements.md`.
- Put current system structure in `/docs/architecture.md`.
- Put decision rationale in `/docs/decisions.md` or `/docs/adr/`.
- Put implementation-independent engineering rules in `/docs/engineering-rules.md`.
- Put process, review, validation, collaboration, and release-readiness workflow in `/docs/workflow.md`.
- Put versioning, changelog, release publication, artifact publication, migration, and compatibility policy in `/docs/release.md`.
- Put language-specific, framework-specific, runtime-specific, module-specific, or integration-specific guidance in `/docs/implementation-notes.md`.

When content no longer fits a document’s intended role, move it to a more appropriate file instead of overloading the original document.

## 11. Output and validation expectations

When presenting analysis, plans, proposed changes, applied changes, validation results, or unresolved follow-up items, include the information needed for review.

When relevant, include:

- assumptions and uncertainties
- affected files or areas
- implementation approach
- validation approach
- documentation impact
- risks or trade-offs
- unresolved follow-up items

When producing file content for a user to copy, provide complete file content unless the user asks for a patch or excerpt.

Validate changes using the most relevant available checks.

Depending on the repository, validation may include:

- tests
- linters
- type checks
- formatters
- build commands
- documentation link checks
- example commands
- manual inspection

If validation cannot be run, state that explicitly.

If validation fails, report the failure and avoid presenting the change as fully validated.

Do not invent validation results.

## 12. Code and engineering preferences

These preferences guide code, design, refactoring, and maintainability decisions when they are relevant to the requested task.

They do not authorize unrelated refactoring, redesign, renaming, reformatting, dependency changes, or architectural changes outside the task scope.

Prefer designs that are clear, maintainable, and consistent with the documented architecture and rules.

- Follow established project conventions.
- Keep implementations simple.
- Fix root causes.
- Prefer explicit boundaries over hidden coupling.
- Prefer descriptive, unambiguous names.
- Encapsulate boundary conditions and edge cases.
- Prefer value objects or explicit domain structures over primitive-heavy designs when appropriate.
- Favor immutability where practical.
- Prefer dependency injection when it improves separation, clarity, or testability.
- Prefer protocols or interfaces over inheritance-heavy designs when appropriate.
- Prefer polymorphism over complex conditional dispatch when it makes the design clearer.
- Keep configurable data high in the system when practical.
- Avoid unnecessary configurability.
- Avoid logical dependencies between unrelated modules.
- Separate concurrent, asynchronous, or multi-threaded code from ordinary sequential logic when practical.
- Follow the Law of Demeter where doing so reduces coupling.
- Favor existing repository patterns unless those patterns are themselves the problem.
- Avoid unnecessary indirection and abstraction.
- Keep public interfaces small and explicit.
- Keep side effects visible at boundaries.
- Preserve single source of truth for domain rules, schemas, constants, and shared logic.

Language-specific or framework-specific rules belong in repository documentation, usually `/docs/implementation-notes.md` or a more specific document under `/docs`.

Do not place detailed language-specific rules in `AGENTS.md` unless this repository itself is language-specific and the rule is part of the agent contract.

## 13. Tool and IDE caveat

This contract is intended to guide agent and chat workflows.

Some tools or editor features may not apply repository instructions uniformly.

When that happens, preserve the intent of this contract as closely as the tool allows.