# AGENTS.md

**Release date:** 2026-04-23 - **Canonical source:** https://github.com/indisoluble/AGENTS-spec

## 1. Canonical status

This file is the canonical repository agent contract.

It applies to planning, implementation, refactoring, review, and documentation work in this repository.

When repository instruction sources overlap or conflict, `AGENTS.md` governs.

## 2. Purpose and scope

This repository carries its own agent-operating contract so project rules remain repository-local, reviewable, versioned, and portable across tools and IDEs.

This contract supports normal development workflows without making hidden or tool-specific configuration the source of truth.

## 3. Default posture

### 3.1 Hard constraints

- Inspect the relevant repository context before acting on non-trivial work.
- Plan before editing for non-trivial work.
- Keep code and documentation synchronized.
- Make small, reviewable changes.
- State assumptions, uncertainties, and missing context explicitly.
- Do not treat undocumented project rules outside the repository as the source of truth.
- Enforce single source of truth for shared values, logic, schemas, rules, and definitions.
- Reuse an existing definition or extract a shared definition before duplicating values or logic.
- Prefer the smallest viable refactor that preserves or restores single source of truth.

### 3.2 Preferred style

- Prefer simple solutions over clever ones.
- Fix root causes rather than symptoms.
- Prefer clear names and explicit boundaries.
- Favor immutability where practical.
- Prefer protocols or interfaces over inheritance-heavy designs when appropriate.
- Use dependency injection where it improves separation, clarity, or testability.
- Avoid unnecessary configurability.

## 4. Planning requirements

For non-trivial tasks:
- understand the request and its constraints
- inspect the relevant repository context
- identify assumptions, unknowns, and risks
- produce a plan before making changes
- separate investigation, implementation, validation, and documentation work
- identify the files or areas likely to change
- keep the plan reviewable

Scale planning depth to task complexity. Do not produce elaborate plans for trivial tasks.

## 5. Required context consultation

Before proposing or applying non-trivial changes, consult:
- `AGENTS.md`
- `README.md`
- explicitly referenced documents under `/docs`
- files directly affected by the task
- adjacent tests, configuration, or operational documents when relevant

If essential context is missing, state that explicitly and proceed using the smallest safe assumption set.

## 6. Execution paths

### 6.1 Tools that can modify repository files

- Apply the smallest coherent change directly.
- Keep the change set reviewable.
- Update relevant documentation in the same change cycle when needed.
- Avoid unnecessary churn outside the scope of the task.

### 6.2 Tools that cannot modify repository files

- Provide exact file-level edits, focused snippets, or a concrete patch.
- Do not stop at abstract recommendations when a concrete edit can be described.
- Preserve the same planning and documentation obligations as tools that can modify files directly.

## 7. Documentation synchronization

Documentation is part of the change, not an optional follow-up.

When a change affects behavior, interfaces, architecture, configuration, operations, workflows, or constraints, update the relevant documentation in the same change cycle.

Treat stale or contradictory documentation as a defect.

## 8. Bootstrap workflow for under-documented repositories

When the repository lacks sufficient documentation, bootstrap it incrementally.

Establish at minimum:
- `README.md`
- `AGENTS.md`
- `/docs/project-brief.md`
- `/docs/system-patterns.md`
- `/docs/project-rules.md`

Add `/docs/table-of-contents.md` when the documentation set is no longer trivial.

Bootstrap documentation one document at a time.

- Create or refactor one document at a time.
- Keep each step small and reviewable.
- Prioritize the minimum baseline documents before specialized documents.
- Avoid generating many broad documents at once.
- Move content beyond the role of `README.md` into focused documents under `/docs`.

## 9. Normalization pass

After significant documentation creation or refactoring:
- reconcile `README.md` and `/docs`
- remove contradictions
- reduce unnecessary duplication
- keep `README.md` concise and entry-point oriented
- move long-form detail into focused documentation files

## 10. Document roles

Use each repository document for a distinct purpose.

Give each document one primary responsibility.

- `AGENTS.md`: canonical repository agent contract
- `README.md`: concise project orientation and quick-start
- `/docs/project-brief.md`: project purpose, scope, and goals
- `/docs/system-patterns.md`: architecture, major design decisions, and system structure
- `/docs/project-rules.md`: repository-specific engineering, workflow, and implementation rules
- `/docs/table-of-contents.md`: index of repository documentation when the documentation set is no longer trivial
- `.github/copilot-instructions.md`: minimal bridge for compatible IDEs and tools, not an independent policy source

Do not mix unrelated responsibilities when separating them improves clarity and maintainability.

When a document accumulates multiple responsibilities, split it into focused documents instead of expanding it indefinitely.

When content no longer fits a document’s intended role, move it to a more appropriate file instead of overloading the original document.

## 11. Engineering preferences

Prefer designs that are clear, maintainable, and consistent with the documented architecture and rules.

- Prefer explicit boundaries over hidden coupling.
- Prefer descriptive, unambiguous names.
- Encapsulate boundary conditions and edge cases.
- Prefer value objects or explicit domain structures over primitive-heavy designs when appropriate.
- Favor existing repository patterns unless those patterns are themselves the problem.
- Avoid unnecessary configurability, indirection, and abstraction.

Keep language-specific or framework-specific rules in repository documentation such as `/docs/project-rules.md`, not in `AGENTS.md`.

## 12. Output expectations

When presenting analysis, plans, or proposed changes, include the information needed for review.

When relevant, include:
- assumptions and uncertainties
- affected files or areas
- implementation approach
- validation approach
- documentation impact

When duplication pressure exists, reuse an existing definition or extract a shared definition before duplicating values or logic. Prefer the smallest viable refactor.

If duplication must remain, include:

`Single source of truth: reused <existing definition> / extracted <shared definition>; could not consolidate <specific constraint>.`

Prefer clear, direct, review-friendly outputs over rigid response templates.

## 13. Tool and IDE caveat

This contract is intended to guide agent and chat workflows.

Some tools or editor features may not apply repository instructions uniformly. When that happens, preserve the intent of this contract as closely as the tool allows.