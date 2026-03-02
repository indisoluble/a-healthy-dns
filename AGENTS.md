# AGENTS.md

Non-negotiable rules for any AI coding agent (IDE agents, PR agents, chat agents) working in this repository.

**Inspiration:**
- Robert C. Martin (“Uncle Bob”) *Clean Code* principles.
- msitarzewski/AGENT-ZERO (https://github.com/msitarzewski/AGENT-ZERO)

## Goals
- Produce changes that are **easy to review** and **consistent** with this repo’s style.
- Prevent churn (rewrites, unnecessary files) and reduce architectural drift.
- Ensure changes are **verifiable** and **documented**.

---

## 0) Definitions

- **Agent**: any AI tool producing analysis, plans, diffs, or file edits for this repo.
- **Path A**: tool **can** modify repository files.
- **Path B**: tool **cannot** modify repository files (chat-only suggestions/patches).
- **Implementation changes**: any repo changes **outside** `docs/` (code/config/tests/build/CI/etc).
- **Docs changes**: changes **under** `docs/`.
- **Citation**: reference format:
  - `path/to/file.ext:123` (preferred), or
  - `path/to/file.ext#AnchorName` (if line numbers are unavailable; state why).

---

## 1) Docs-first (mandatory)

### 1.1 Required reading (when present)
Before proposing or applying changes, consult and use `docs/` as primary inputs:

- `docs/toc.md` — documentation index / navigation map.
- `docs/projectbrief.md` — goals, non-goals, constraints, requirements.
- `docs/systemPatterns.md` — architecture patterns and conventions.
- `docs/projectRules.md` — language/tool specifics and QA commands.

### 1.2 Response requirement
Every response that proposes or applies changes must include:
- **Docs consulted:** citations to the specific sections used.

If any of the required docs are missing:
- **Missing docs:** list missing items, then proceed with best effort.

---

## 2) Hard constraints (must follow)

If you cannot comply, you must say so and explain why.

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

5) **Docs-first is mandatory.**  
   - Proposals must align with `docs/`.  
   - Response must include **Docs consulted** citations (section 1.2).

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
2. **Docs consulted** (required): cite `docs/` sections used.
3. **Plan** (short, numbered). Include reuse analysis if relevant.
4. **Change intent (what will change + where)**:
   - List the files/areas to touch (with citations).
   - Describe intended edits in a way that can be checked against git diff.
   - Cite docs that justify key decisions.

After step 4, follow Path A or Path B.

### 4.2 Path A — Tool CAN modify repository files (default)

5. **Apply implementation changes** (code/config/tests/etc).
6. **QA**: validate the **actual working tree** after step 5.
7. **Apply docs changes + Docs impact** (when relevant):
   - Update/add docs under `docs/`.
   - If adding a new doc, also update `docs/toc.md`.
   - State **Docs impact** (or explicitly: **Docs impact: none**).
8. **Applied changes summary**:
   - What actually changed.
   - Any deviation from plan/change intent.
   - Files touched (citations when practical).

**Rule:** In Path A, do **not** generate patch/diff blocks in chat unless the user explicitly requests them.

### 4.3 Path B — Tool CANNOT modify repository files

5. **Provide implementation patch/snippets**:
   - Prefer a minimal diff/patch; otherwise focused snippets.
   - Include exact file paths and enough context to apply safely.
6. **QA**: list commands/checks to run after manual apply.
7. **Provide docs patch/snippets + Docs impact** (when relevant):
   - Include `docs/toc.md` updates if adding a new doc.
   - Or explicitly: **Docs impact: none**.
8. **Manual-apply summary**:
   - Apply order and any risky steps/follow-ups.

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

## 8) Documentation rules (`docs/` is the shared source of truth)

- Docs are used for analysis (section 1), not only updated after.
- Update docs when you change APIs, behavior, configuration, architecture patterns, or development workflow.
- If new content does **not fit** any document in the minimum reading set:
  - Add a new focused doc under `docs/`.
  - Update `docs/toc.md`.
  - Justify why it does not belong in the existing docs.

This does not bypass **No new files without reuse analysis**; it satisfies it when reuse analysis shows no existing doc is an appropriate home.

---

## 9) Conflicts

If any instruction here conflicts with a user request:
- Follow the user’s explicit instruction and state the deviation from this file.
- If forced to proceed without clarity, prefer:
  1) correctness and safety,
  2) minimal diff,
  3) preserving existing architecture and patterns.