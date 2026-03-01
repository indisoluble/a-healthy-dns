# AGENTS.md

This file defines **non-negotiable** engineering and collaboration rules for any AI coding agent (IDE agents, PR agents, chat agents) working in this repository.

**Inspiration:**
- Robert C. Martin (“Uncle Bob”) *Clean Code* principles.
- msitarzewski/AGENT-ZERO (https://github.com/msitarzewski/AGENT-ZERO)

## Goals
- Produce changes that are **easy to review** and **consistent** with this repo’s style.
- Prevent churn (rewrites, unnecessary files) and reduce architectural drift.
- Ensure changes are **verifiable** and **documented**.

---

## 0) Definitions (used throughout)
- **Agent**: any AI tool producing analysis, plans, diffs, or file edits for this repo.
- **Apply changes**: modify repository files (directly or via an automated action).
- **Proposal**: plan + rationale + diff/snippets, not yet applied.
- **Docs**: files under `docs/`.
- **Citations**: references to existing artifacts using one of:
  - `path/to/file.ext:123` (preferred), or
  - `path/to/file.ext#AnchorName` (if line numbers are unavailable)

---

## 1) Documentation-first (mandatory)

### 1.1 Read docs before analysis
Before proposing changes, agents must **consult and use** `docs/` as primary inputs to analysis and recommendations.

Minimum required reading **when present**:
- `docs/toc.md` — documentation index / navigation map.
- `docs/project-brief.md` — goals, non-goals, constraints, high-level requirements.
- `docs/system-patterns.md` — architecture patterns and conventions to follow.
- `docs/project-rules.md` — language/tool specifics and QA commands.

### 1.2 Validation (must appear in responses)
Every response that proposes a change must include a short **Docs consulted** list with citations, e.g.:

- **Docs consulted:** `docs/project-brief.md#Constraints`, `docs/system-patterns.md#DependencyInjection`

If a required doc is missing, state it explicitly under **Missing docs** and proceed with best effort:
- **Missing docs:** `docs/system-patterns.md` (not found)

---

## 2) Default posture

### 2.1 Hard constraints (must follow)
If you cannot comply, you must say so and explain why.

1) **No new files without reuse analysis** (code/config/etc).  
   - Requirement: search the repo for an existing place to extend; new files require justification.  
   - Validation (must appear *before* proposing/creating a new file):  
     **Reuse analysis:** checked `A`, `B`, `C`. Cannot extend because `<technical reason>`.

2) **No rewrites when refactoring is possible**.  
   - Requirement: prefer incremental refactors over wholesale rewrites.  
   - Validation (must appear *before* proposing/doing a rewrite):  
     **Refactor not viable because:** `<specific constraint>`.

3) **No generic advice**.  
   - Requirement: provide concrete integration points.  
   - Validation: recommendations include citations to existing code/docs. If line numbers are unavailable, use `#Anchor` and state why.

4) **Do not ignore existing architecture**.  
   - Requirement: identify existing patterns/components first; extend them; consolidate duplicates.  
   - Validation (must appear when changing architecture or adding a new component/pattern):  
     **Extends existing pattern:** `path/to/file.ext:line` (or `#Anchor`).

5) **Docs-first analysis is mandatory**.  
   - Requirement: changes must be consistent with the docs (section 1).  
   - Validation: include **Docs consulted** citations in the response.

### 2.2 Preferred style (strong defaults)
- Prefer **small, reversible, reviewable** changes.
- Prefer **extending existing code** over introducing new abstractions.
- Prefer **explicitness** over cleverness.
- Prefer **composition** over inheritance.

---

## 3) How to collaborate (workflow)

### 3.1 Interaction protocol (default structure)
Use this structure for any non-trivial task:

1. **Understanding** (1–3 bullets): what you think the task is + constraints.  
2. **Docs consulted** (required; see 1.2).  
3. **Plan** (short, numbered). Include reuse analysis if relevant.  
4. **Proposed changes**:
   - Minimal diff (patch-style preferred) or focused snippets.
   - Cite the existing code you are changing/extending.
   - Cite the docs that justify key decisions.
5. **QA** (required; see section 6).  
6. **Docs impact** (required when relevant; see section 7).  
7. **Approval request** (required if you can apply changes; see 3.2).

### 3.2 Approval gate (single-contributor friendly)
If the tool can modify repo files:
- Do **not** apply changes immediately.
- Provide a proposal first and wait for explicit approval.

Acceptable approval signals (examples): “apply”, “go ahead”, “implement”, “yes”.

If the tool cannot edit files directly:
- You may provide patches/snippets without waiting, but still follow all rules above.

---

## 4) Engineering rules (language-agnostic)

### 4.1 General
1. Follow standard conventions (language/ecosystem idioms).
2. Keep it simple: reduce complexity aggressively.
3. Always look for the root cause (not symptoms).

### 4.2 Design
1. Keep configurable data at high levels (composition roots / wiring layers).
2. Prefer polymorphism to `if/else` or `switch/case` for behavior selection.
3. Separate concurrency/multi-threading from core domain logic.
4. Prevent over-configurability (avoid adding knobs without strong need).
5. Use dependency injection for external dependencies (I/O, time, randomness, network, persistence).
6. Follow the Law of Demeter (know only direct dependencies).

### 4.3 Understandability
1. Be consistent.
2. Use explanatory variables.
3. Encapsulate boundary conditions.
4. Prefer dedicated value objects to primitive types.
5. Avoid logical dependency (hidden ordering/state requirements).
6. Avoid negative conditionals when a positive form is clearer.

### 4.4 Naming
1. Descriptive and unambiguous.
2. Meaningful distinctions.
3. Pronounceable.
4. Searchable.
5. Replace magic numbers with named constants.
6. Avoid encodings (no prefixes/type info in names).

### 4.5 Functions / methods
1. Small.
2. Do one thing.
3. Descriptive names.
4. Fewer arguments.
5. No side effects (or isolate at boundaries explicitly).
6. No flag arguments; split into separate operations.

### 4.6 Comments
1. Explain intent in code first.
2. No redundancy/noise.
3. Don’t comment out code; remove it.
4. Use comments for intent, tricky clarifications, and warnings of consequences.

### 4.7 Source structure
1. Separate concepts vertically; keep related code dense.
2. Declare variables close to usage.
3. Keep dependent and similar functions close.
4. Downward direction: high-level → details.
5. Keep lines short; avoid horizontal alignment.
6. Use whitespace to communicate structure; don’t break indentation.

### 4.8 Objects and data structures
1. Hide internal structure.
2. Prefer simple data carriers when appropriate; objects when behavior is central.
3. Avoid hybrids (half object / half data).
4. Keep objects small; do one thing; few instance variables.
5. Base types know nothing about derivatives.
6. Prefer many functions over passing code into a selector function.
7. Prefer non-static methods unless strongly idiomatic otherwise.

### 4.9 Tests
1. One assert per test (prefer focused tests).
2. Readable, fast, independent, repeatable.
3. Prefer deterministic tests; avoid real network/time unless explicitly testing integration.

### 4.10 Code smells (avoid)
- Rigidity, fragility, immobility.
- Needless complexity, needless repetition.
- Opacity.

---

## 5) Traceability (citations)

### 5.1 What to cite
Use citations for:
- places you will change,
- patterns you are extending,
- files inspected for reuse analysis,
- things you propose to delete/refactor,
- docs rules/patterns you are applying.

### 5.2 Citation format
- Prefer: `relative/path/to/file.ext:123`
- If line numbers unavailable: `relative/path/to/file.ext#AnchorName` + state why.

---

## 6) Verification (QA) — always include

For any non-trivial change, include a **QA** section:
- Prefer the repo’s documented workflow in `docs/projectRules.md`.
- If the repo does not define QA commands yet, propose a minimal set appropriate to the stack.
- If you cannot run commands, say so; still list what should be run.

---

## 7) Documentation rules (`docs/` is the shared source of truth)

### 7.1 Use docs for analysis, not only updates
Agents must:
- read relevant docs before proposing changes (section 1),
- align proposals with documented patterns/rules,
- include doc citations in the rationale.

### 7.2 Update docs when behavior changes
Update docs when you:
- add/change a public API, CLI, configuration, or externally visible behavior,
- introduce/modify architecture patterns,
- change development workflow (tools, commands, environment),
- add constraints or conventions that affect contributors/agents.

### 7.3 Adding new docs is allowed (sometimes required)
If new content does **not fit** any document in the minimum reading set:
- Add a new focused doc under `docs/` (single topic).
- Update `docs/toc.md` to include it.
- In the proposal, justify why it does not belong in the existing docs.

This rule does **not** override “No new files without reuse analysis”: it **satisfies** it when the reuse analysis concludes existing docs are not an appropriate home.

---

## 8) Conflicts
If any instruction here conflicts with a user request:
- Ask which requirement wins **before** applying changes.
- If forced to proceed without clarity, prefer:
  1) correctness and safety,
  2) minimal diff,
  3) preserving existing architecture and patterns.