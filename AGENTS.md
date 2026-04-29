# AGENTS.md

**Release date:** 2026-04-30 - **Canonical source:** https://github.com/indisoluble/AGENTS-spec

## 1. Canonical status

This file is the canonical repository agent contract.

It applies to planning, implementation, refactoring, review, and documentation work in this repository.

When repository instruction sources overlap or conflict, `AGENTS.md` governs.

`.github/copilot-instructions.md` is a compatibility bridge only. It must point to `AGENTS.md` and must not become an independent policy source.

## 2. Purpose and scope

This repository carries its own agent-operating contract so project rules remain repository-local, reviewable, versioned, and portable across tools and IDEs.

This contract supports normal development workflows without making hidden, personal, remote, or tool-specific configuration the source of truth.

Agents must treat repository files as the authoritative source for project behavior, constraints, rules, and documentation structure.

## 3. Default posture

### 3.1 Hard constraints

- Inspect the relevant repository context before acting on non-trivial work.
- Plan before editing for non-trivial work.
- Keep code and documentation synchronized.
- Make small, coherent, reviewable changes.
- State assumptions, uncertainties, and missing context explicitly.
- Do not treat undocumented project rules outside the repository as the source of truth.
- Enforce single source of truth for shared values, logic, schemas, rules, requirements, and definitions.
- Reuse an existing definition or extract a shared definition before duplicating values or logic.
- Prefer the smallest viable refactor that preserves or restores single source of truth.
- Do not hide material changes in unrelated files.
- Do not defer required documentation updates when the current change alters behavior, interfaces, architecture, configuration, operations, workflow, or constraints.

### 3.2 Preferred style

- Prefer simple solutions over clever ones.
- Fix root causes rather than symptoms.
- Prefer clear names and explicit boundaries.
- Favor immutability where practical.
- Prefer protocols or interfaces over inheritance-heavy designs when appropriate.
- Use dependency injection where it improves separation, clarity, or testability.
- Avoid unnecessary configurability.
- Avoid unnecessary abstraction.
- Keep behavior discoverable in repository files.
- Keep documents concise, focused, and internally consistent.

## 4. Planning requirements

For non-trivial tasks:

- understand the request and its constraints
- inspect the relevant repository context
- identify assumptions, unknowns, and risks
- produce a plan before making changes
- separate investigation, implementation, validation, and documentation work
- identify the files or areas likely to change
- keep the plan reviewable

Scale planning depth to task complexity.

Do not produce elaborate plans for trivial tasks.

Do not use planning as a substitute for making a concrete change when the change is clear and safe.

## 5. Required context consultation

Before proposing or applying non-trivial changes, consult:

- `AGENTS.md`
- `README.md`
- explicitly referenced documents under `/docs`
- files directly affected by the task
- adjacent tests, configuration, scripts, or operational documents when relevant

If essential context is missing, state that explicitly and proceed using the smallest safe assumption set.

If repository documentation is missing, incomplete, or contradictory, treat that as documentation debt and improve it within the current task when doing so is directly relevant.

## 6. Execution paths

### 6.1 Tools that can modify repository files

- Apply the smallest coherent change directly.
- Keep the change set reviewable.
- Update relevant documentation in the same change cycle when needed.
- Avoid unnecessary churn outside the scope of the task.
- Preserve existing conventions unless the task requires changing them.
- Do not ask for permission to make clearly scoped repository edits unless the user, tool, or environment requires confirmation.

### 6.2 Tools that cannot modify repository files

- Provide exact file-level edits, focused snippets, or a concrete patch.
- Do not stop at abstract recommendations when a concrete edit can be described.
- Preserve the same planning and documentation obligations as tools that can modify files directly.
- Make the intended file paths and replacement locations explicit.
- Keep proposed edits small enough for practical review.

## 7. Documentation synchronization

Documentation is part of the change, not an optional follow-up.

When a change affects behavior, interfaces, architecture, configuration, operations, workflows, or constraints, update the relevant documentation in the same change cycle.

Treat stale, missing, duplicated, or contradictory documentation as a defect.

When documentation and implementation disagree:

- inspect the relevant implementation and tests
- determine whether the implementation or documentation is authoritative for the current task
- update the incorrect or stale source
- state any remaining uncertainty

Avoid duplicating long-form content across documents. Prefer links and concise summaries.

## 8. Bootstrap workflow for under-documented repositories

When the repository lacks sufficient documentation, bootstrap it incrementally.

Establish at minimum:

- `README.md`
- `AGENTS.md`
- `/docs/project-brief.md`
- `/docs/requirements.md`
- `/docs/architecture.md`
- `/docs/engineering-rules.md`

Add `/docs/table-of-contents.md` when the documentation set is no longer trivial.

Add specialized documents only when the baseline documents would otherwise become overloaded.

Common specialized documents include:

- `/docs/decisions.md`
- `/docs/adr/`
- `/docs/workflow.md`
- `/docs/implementation-notes.md`
- `/docs/operations.md`
- `/docs/security.md`
- `/docs/testing.md`
- `/docs/release.md`

Bootstrap documentation incrementally.

- Create or refactor one document at a time.
- Keep each step small and reviewable.
- Prioritize the minimum baseline documents before specialized documents.
- Avoid generating many broad documents at once.
- Move content beyond the role of `README.md` into focused documents under `/docs`.
- Prefer a useful minimal document over a speculative comprehensive document.
- Mark unknowns explicitly instead of inventing project facts.
- Do not create a specialized document unless there is enough content to justify its existence.
- After creating or substantially refactoring one document, stop and let the human review the diff before continuing to the next bootstrap document, unless explicitly instructed to continue.

For existing repositories with code but little or no documentation:

- inspect the repository before writing documentation
- derive documentation from observable code, configuration, tests, scripts, and existing comments
- distinguish confirmed facts from inferred intent
- avoid presenting guesses as project rules
- create the baseline documents sequentially
- perform a normalization pass after the baseline exists

For empty or nearly empty repositories:

- create minimal starter documentation
- keep project-specific claims narrow
- use placeholders only when they are useful and clearly marked
- avoid inventing architecture, requirements, workflows, or implementation rules that the repository does not yet support

## 9. Document roles

Use each repository document for a distinct purpose.

Give each document one primary responsibility.

### 9.1 Root documents

- `AGENTS.md`: canonical repository agent contract.
- `README.md`: concise project orientation and quick-start. It should explain what the project is, how to get started, and where deeper documentation lives. It must not become the authoritative home for requirements, architecture, design decisions, engineering rules, workflow rules, operations, or implementation notes.
- `.github/copilot-instructions.md`: minimal bridge for compatible IDEs and tools; not an independent policy source.

### 9.2 Baseline `/docs` documents

- `/docs/project-brief.md`: project purpose, scope, goals, non-goals, target users or operators, and high-level capabilities. It may summarize capabilities, but it must not become a requirements list.
- `/docs/requirements.md`: functional, operational, quality, compatibility, security, performance, reliability, and constraint requirements the system must satisfy.
- `/docs/architecture.md`: current system structure, runtime model, component boundaries, data flows, control flows, integration points, deployment-relevant architecture, and major architectural relationships.
- `/docs/engineering-rules.md`: repository-specific engineering principles, coding standards, general testing expectations, design constraints, naming rules, maintainability rules, and implementation-independent technical preferences.
- `/docs/table-of-contents.md`: navigation index for repository documentation when the documentation set is no longer trivial; it links to documents but does not duplicate their content.

### 9.3 Specialized `/docs` documents

Create specialized documents only when they improve clarity and prevent baseline documents from becoming overloaded.

- `/docs/decisions.md`: major architectural and design decisions, including rationale, alternatives considered, and consequences.
- `/docs/adr/`: individual architecture decision records when decisions are numerous or require lifecycle tracking.
- `/docs/workflow.md`: development workflow, branching, review expectations, CI validation, release readiness, documentation update process, and human or agent collaboration rules.
- `/docs/implementation-notes.md`: language-specific, framework-specific, runtime-specific, module-specific, or integration-specific implementation guidance.
- `/docs/operations.md`: deployment, runtime operations, monitoring, incident response, backup, recovery, and production support procedures.
- `/docs/security.md`: threat model, security assumptions, secrets handling, authentication, authorization, vulnerability management, and secure development rules.
- `/docs/testing.md`: test strategy, test taxonomy, required test commands, fixtures, coverage expectations, and validation rules.
- `/docs/release.md`: versioning, changelog, release publication process, artifact publication, migration notes, and compatibility policy.

### 9.4 Responsibility boundaries

Use these boundaries:

- `project-brief.md` explains why the project exists and what is in or out of scope.
- `requirements.md` defines what must be true.
- `architecture.md` explains how the system is structured.
- `decisions.md` or `adr/` explains why important choices were made.
- `engineering-rules.md` defines how code should be written and maintained.
- `workflow.md` defines how repository changes are made, validated, reviewed, merged, and prepared for release.
- `implementation-notes.md` captures technology-specific implementation detail.
- `operations.md` captures how the system is run after it exists.
- `security.md` captures security-specific constraints and procedures.
- `testing.md` captures validation strategy and commands.
- `release.md` captures versioning, compatibility, migration, changelog, and release publication rules.

Do not mix unrelated responsibilities when separating them improves clarity and maintainability.

When a document accumulates multiple responsibilities, split it into focused documents instead of expanding it indefinitely.

When content no longer fits a document’s intended role, move it to a more appropriate file instead of overloading the original document.

## 10. Placement rules

Use these placement rules:

- Put requirements in `/docs/requirements.md`. Requirements include functional, operational, quality, compatibility, security, performance, reliability, observability, configuration, and external-system constraints.
- Let `/docs/project-brief.md` summarize purpose, scope, goals, and high-level capabilities, but not own requirements.
- Put current system structure in `/docs/architecture.md`. It may reference requirements and decision outcomes, but it must not own requirements or major decision rationale.
- Put significant decision rationale in `/docs/decisions.md` or `/docs/adr/`.
- Put implementation-independent engineering rules in `/docs/engineering-rules.md`.
- Put substantial change-process, review, validation, merge, release readiness, and collaboration workflow in `/docs/workflow.md`.
- Put versioning, changelog, release publication, artifact publication, migration, and compatibility policy in `/docs/release.md`.
- Put language-specific, framework-specific, runtime-specific, module-specific, or integration-specific guidance in `/docs/implementation-notes.md`.

For small repositories, `/docs/decisions.md` is sufficient.

For larger repositories or projects with many durable decisions, prefer `/docs/adr/`.

## 11. Engineering preferences

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

## 12. Normalization pass

After significant documentation creation or refactoring, perform a normalization pass.

The normalization pass must:

- reconcile `README.md`, `AGENTS.md`, and `/docs`
- remove contradictions
- reduce unnecessary duplication
- keep `README.md` concise and entry-point oriented
- move long-form detail into focused documentation files
- verify that each document has one primary responsibility
- verify that document names still match document contents
- verify that links between documents are accurate
- verify that requirements, architecture, rules, and workflow guidance are not mixed unnecessarily
- remove obsolete placeholders
- preserve useful cross-references

A normalization pass is mandatory after bootstrapping or substantially reorganizing repository documentation.

## 13. Output expectations

When presenting analysis, plans, or proposed changes, include the information needed for review.

When relevant, include:

- assumptions and uncertainties
- affected files or areas
- implementation approach
- validation approach
- documentation impact
- risks or trade-offs
- follow-up items that remain unresolved

When producing file content for a user to copy, provide complete file content unless the user asks for a patch or excerpt.

Prefer clear, direct, review-friendly outputs over rigid response templates.

## 14. Validation expectations

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

## 15. Tool and IDE caveat

This contract is intended to guide agent and chat workflows.

Some tools or editor features may not apply repository instructions uniformly.

When that happens, preserve the intent of this contract as closely as the tool allows.