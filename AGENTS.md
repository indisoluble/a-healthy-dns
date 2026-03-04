# AGENTS.md (lite)

Non-negotiable rules for any AI coding agent (IDE agents, PR agents, chat agents) working in this repository.

**Inspiration / lineage (non-normative):**
- Robert C. Martin (“Uncle Bob”) *Clean Code* principles.
- msitarzewski/AGENT-ZERO (https://github.com/msitarzewski/AGENT-ZERO)

## Goals
- Produce changes that are **easy to review** and **consistent** with this repo’s style.
- Prevent churn (rewrites, unnecessary files) and reduce architectural drift.
- Ensure changes are **verifiable** and **documented**.

---

## 0) Definitions

- **Agent**: any AI tool producing analysis, plans, patches, or file edits for this repo.
- **Path A**: tool **can** modify repository files.
- **Path B**: tool **cannot** modify repository files (chat-only suggestions/patches).
- **Implementation changes**: repo changes **outside** `README.md` and `docs/` (code/config/tests/build/CI/etc).
- **Docs changes**: changes to `README.md` and/or files under `docs/`.
- **Citation**:
  - `path/to/file.ext:123` (preferred), or
  - `path/to/file.ext#AnchorName` (if line numbers are unavailable; state why).

---

## 1) Docs-first (mandatory)

### 1.1 Required reading (when present)

Before proposing or applying changes, consult project documentation as primary inputs.

#### Base required reading
- `README.md` — project entrypoint (what it is, why it exists, fastest first successful result / usage path).
- `docs/toc.md` — documentation index and minimum/core reading registry.
- `docs/projectbrief.md` — goals, non-goals, constraints, requirements.
- `docs/systemPatterns.md` — architecture patterns and conventions.
- `docs/projectRules.md` — language/tool specifics and QA commands.

#### Extended required reading (dynamic)
Read all items that apply to the task from:
- the **Minimum Reading Set / Core Docs / Primary Docs** section in `docs/toc.md` (project naming may vary), and
- documents explicitly linked from `README.md` as the primary path for setup, usage, configuration, architecture, troubleshooting, or operations.

If `docs/toc.md` exists but has no minimum/core reading section:
1. read the Base required reading, and
2. use best effort to identify the most relevant docs linked from `README.md` and `docs/toc.md`.

### 1.2 Response requirement

Every response that proposes or applies changes must include:

- **Docs consulted:** citations to the specific sections used (including dynamic docs when applicable).

If any required docs are missing:
- **Missing docs:** list missing items, then proceed with best effort.

---

## 2) Hard constraints (must follow)

If you cannot comply, say so and explain why.

1) **No new files without reuse analysis** (includes docs).  
   - Before creating a file, search for an existing place to extend.  
   - Response must include:  
     **Reuse analysis:** checked `A`, `B`, `C`. Cannot extend because `<technical reason>`.

2) **No rewrites when refactoring is possible.**  
   - Prefer incremental refactors over wholesale rewrites.  
   - Before proposing/doing a rewrite, response must include:  
     **Refactor not viable because:** `<specific constraint>`.

3) **No generic advice.**  
   - All recommendations must include concrete integration points with citations (code + docs).  
   - If line numbers are unavailable, use `#AnchorName` and state why.

4) **Do not ignore existing architecture.**  
   - Identify existing patterns/components first; extend them; consolidate duplicates.  
   - When introducing a new component/pattern or changing architecture, response must include:  
     **Extends existing pattern:** `path/to/file.ext:line` (or `#AnchorName`).

---

## 3) Preferred style (strong defaults)

- Prefer **small, reversible, reviewable** changes.
- Prefer **extending existing code** over introducing new abstractions.
- Prefer **explicitness** over cleverness.
- Prefer **composition** over inheritance.

---

## 4) Workflow (two paths)

### 4.1 Common steps (always)

1. **Understanding** (1–3 bullets): task + constraints.
2. **Docs consulted** (required): cite `README.md` / `docs/` sections used.
3. **Plan** (short, numbered). Include reuse analysis if relevant.
4. **Change intent (what will change + where)**:
   - List files/areas to touch (with citations).
   - Describe intended edits so they can be checked against git diff.
   - Cite docs that justify key decisions.

After step 4, follow Path A or Path B.

---

### 4.2 Path A — Tool CAN modify repository files (default)

5. **Apply implementation changes** (code/config/tests/etc).
6. **QA**: validate the **actual working tree** after step 5.
7. **Docs changes + Docs impact**:
   - Update `README.md` and/or `docs/` when relevant.
   - If adding a new doc, also update `docs/toc.md`.
   - State **Docs impact** (or explicitly: **Docs impact: none**).
8. **Applied changes summary**:
   - What actually changed.
   - Any deviation from plan/change intent.
   - Files touched (citations when practical).

**Rule:** In Path A, do **not** generate patch/diff blocks in chat unless the user explicitly requests them.

---

### 4.3 Path B — Tool CANNOT modify repository files

5. **Provide implementation patch/snippets**:
   - Prefer a minimal diff/patch; otherwise focused snippets.
   - Include exact file paths and enough context to apply safely.
6. **QA**: list commands/checks to run after manual apply.
7. **Provide docs patch/snippets + Docs impact**:
   - Include `README.md` and `docs/` patches/snippets when relevant.
   - Include `docs/toc.md` updates if adding a new doc.
   - Or explicitly: **Docs impact: none**.
8. **Manual-apply summary**:
   - Apply order.
   - Risky steps / follow-ups.

---

## 5) Engineering rules (language-agnostic)

### 5.1 General
1. Follow standard conventions (language/ecosystem idioms).
2. Keep it simple: reduce complexity aggressively.
3. Always look for the root cause (not symptoms).

### 5.2 Design
1. Keep configurable data at high levels (composition roots / wiring layers).
2. Prefer polymorphism to `if/else` or `switch/case` for behavior selection.
3. Separate concurrency/multi-threading from core domain logic.
4. Prevent over-configurability (avoid adding knobs without strong need).
5. Use dependency injection for external dependencies (I/O, time, randomness, network, persistence).
6. Follow the Law of Demeter (know only direct dependencies).

### 5.3 Understandability
1. Be consistent.
2. Use explanatory variables.
3. Encapsulate boundary conditions.
4. Prefer dedicated value objects to primitive types.
5. Avoid logical dependency (hidden ordering/state requirements).
6. Avoid negative conditionals when a positive form is clearer.

### 5.4 Naming
1. Descriptive and unambiguous.
2. Meaningful distinctions.
3. Pronounceable.
4. Searchable.
5. Replace magic numbers with named constants.
6. Avoid encodings (no prefixes/type info in names).

### 5.5 Functions / methods
1. Small.
2. Do one thing.
3. Descriptive names.
4. Fewer arguments.
5. No side effects (or isolate at boundaries explicitly).
6. No flag arguments; split into separate operations.

### 5.6 Comments
1. Explain intent in code first.
2. No redundancy/noise.
3. Don’t comment out code; remove it.
4. Use comments for intent, tricky clarifications, and warnings of consequences.

### 5.7 Source structure
1. Separate concepts vertically; keep related code dense.
2. Declare variables close to usage.
3. Keep dependent and similar functions close.
4. Downward direction: high-level → details.
5. Keep lines short; avoid horizontal alignment.
6. Use whitespace to communicate structure; don’t break indentation.

### 5.8 Objects and data structures
1. Hide internal structure.
2. Prefer simple data carriers when appropriate; objects when behavior is central.
3. Avoid hybrids (half object / half data).
4. Keep objects small; do one thing; few instance variables.
5. Base types know nothing about derivatives.
6. Prefer many functions over passing code into a selector function.
7. Prefer non-static methods unless strongly idiomatic otherwise.

### 5.9 Tests
1. One assert per test (prefer focused tests).
2. Readable, fast, independent, repeatable.
3. Prefer deterministic tests; avoid real network/time unless explicitly testing integration.

### 5.10 Code smells (avoid)
- Rigidity, fragility, immobility.
- Needless complexity, needless repetition.
- Opacity.

---

## 6) Traceability (citations)

Use citations for:
- places you will change,
- patterns you are extending,
- files inspected for reuse analysis,
- things you propose to delete/refactor,
- docs rules/patterns you are applying.

Format:
- `relative/path/to/file.ext:123` (preferred)
- `relative/path/to/file.ext#AnchorName` (if line numbers unavailable; state why)

---

## 7) Verification (QA) — always required

For any non-trivial change, include a **QA** section:
- Prefer the repo’s documented workflow in `docs/projectRules.md`.
- In Path A, QA validates the applied working tree.
- In Path B, QA lists what to run after manual apply.
- If you cannot run commands, say so; still list what should be run.

---

## 8) Documentation rules (`README.md` + `docs/` are the shared source of truth)

### 8.1 Documentation split of responsibilities

- **`README.md`** is the quick-start, high-signal entrypoint:
  - Keep existing badges.
  - Briefly explain what the project is and why it is useful.
  - Show the fastest path to a first successful result (minimal setup + minimal run/use example).
  - Keep it short, concise, and to the point.
  - Link to `docs/` for details.

- **`docs/`** contains long-form/reference content:
  - setup and installation details,
  - configuration,
  - usage guides / examples,
  - integration and API/reference material (if applicable),
  - architecture/patterns,
  - troubleshooting/operations,
  - contributor/agent guidance,
  - other detailed guides.

### 8.2 Documentation updates and refactors are valid changes

Update/refactor documentation when you change APIs, behavior, configuration, architecture patterns, or development workflow:
- Update `README.md` if the quick-start path, positioning, or first-run experience changes.
- Update/add files in `docs/` for long-form details.

When adopting or aligning a project to this AGENTS.md, documentation restructuring/refactoring is an allowed docs change (including creating the minimum baseline docs when missing).

### 8.3 Adding new docs is allowed (sometimes required)

If new content does **not fit** any existing documentation file:
- Add a new focused doc under `docs/`.
- Update `docs/toc.md`.
- Justify why the content does not belong in an existing doc.
- If the new doc is expected to influence future implementation decisions, add it to the **Minimum Reading Set / Core Docs** section in `docs/toc.md`.

This does not bypass **No new files without reuse analysis**; it satisfies it when reuse analysis shows no existing doc is an appropriate home.

### 8.4 Documentation bootstrap and refactor (non-prescriptive; create what is needed)

This AGENTS.md may be introduced into:
- a **new/empty project**, or
- an **existing project** with partial or oversized documentation.

When asked to align a project with this AGENTS.md, agents should establish or refactor documentation so that:
- `README.md` acts as a **quick-start, high-signal entrypoint** (section 8.1), and
- `docs/` contains the project’s long-form/reference documentation.

#### Minimum documentation baseline (create/refactor when needed)
If missing or not fit for purpose, create or refactor:

- `README.md` — quick-start entrypoint
- `docs/toc.md` — documentation index + minimum/core reading registry
- `docs/projectbrief.md` — goals, non-goals, constraints, requirements
- `docs/systemPatterns.md` — architecture patterns and conventions
- `docs/projectRules.md` — language/tool specifics and QA commands

#### Additional docs (create only when justified)
Create additional focused docs under `docs/` when needed by project scope (e.g., setup, configuration, usage/examples, integration/reference, troubleshooting, operations, architecture overview).

#### Refactor rule for existing repos
If documentation already exists:
- reuse and refactor existing docs before creating new ones,
- split oversized documents when needed,
- preserve useful content and links,
- keep the final structure coherent and discoverable via `docs/toc.md`.

#### Minimum reading promotion rule
If a new or refactored doc is expected to influence future implementation decisions:
- add it to the **Minimum Reading Set / Core Docs** section in `docs/toc.md`.

---

## 9) Conflicts

If any instruction here conflicts with a user request:
- Follow the user’s explicit instruction and state the deviation from this file.
- If forced to proceed without clarity, prefer:
  1) correctness and safety,
  2) minimal diff,
  3) preserving existing architecture and patterns.
