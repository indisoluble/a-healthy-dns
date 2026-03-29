# AGENTS.md

Non-negotiable rules for any AI coding agent (IDE agents, PR agents, chat agents) working in this repository.

**Release date:** 2026-03-29
**Canonical source:** https://github.com/indisoluble/AGENTS-spec

**Inspiration / lineage (non-normative):**
- Robert C. Martin (“Uncle Bob”) *Clean Code* principles
- msitarzewski/AGENT-ZERO

## Goals
- Produce changes that are easy to review and consistent with this repository’s style.
- Prevent churn (rewrites, unnecessary files) and reduce architectural drift.
- Ensure changes are verifiable and documented.

---

## 0) Definitions

- **Agent**: any AI tool producing analysis, plans, patches, or file edits for this repository.
- **Regular work**: normal feature work, fixes, refactors, or ordinary documentation updates.
- **Documentation bootstrap mode**: a documentation workflow used when this AGENTS.md is introduced into an existing project that already has meaningful implemented code/behavior but missing, weak, oversized, or poorly structured documentation.
- **Path A**: the tool can modify repository files.
- **Path B**: the tool cannot modify repository files (chat-only suggestions/patches).
- **Implementation changes**: repository changes outside `README.md` and `docs/`.
- **Docs changes**: changes to `README.md` and/or files under `docs/`.
- **Substantive documentation file**: the main documentation file being created or refactored in the current bootstrap cycle. Updates to `docs/table-of-contents.md` used only to register or index that file do not count as a second substantive file.
- **Citation**:
  - `path/to/file.ext:123` (preferred), or
  - `path/to/file.ext#AnchorName` (if line numbers are unavailable; state why).

---

## 1) Docs-first (mandatory)

### 1.1 Required reading
Before proposing or applying changes, consult project documentation as primary input.

#### Base required reading
- `README.md` — project entrypoint: what it is, why it exists, and the fastest path to a first successful result.
- `docs/table-of-contents.md` — documentation index and minimum/core reading registry.
- `docs/project-brief.md` — goals, non-goals, constraints, requirements.
- `docs/system-patterns.md` — architecture patterns, structural conventions, and the default home for folder hierarchy / codebase layout rules.
- `docs/project-rules.md` — language/tool specifics and QA commands.

#### Extended required reading
Read all task-relevant items from:
- the **Minimum Reading Set / Core Docs / Primary Docs** section in `docs/table-of-contents.md` (project naming may vary),
- documents explicitly linked from `README.md` as the primary path for setup, usage, configuration, architecture, troubleshooting, or operations,
- any document explicitly designated by `docs/system-patterns.md` for folder hierarchy, codebase layout, or file-grouping conventions.

If `docs/table-of-contents.md` exists but has no minimum/core reading section:
1. read the base required reading,
2. use best effort to identify the most relevant docs linked from `README.md` and `docs/table-of-contents.md`.

### 1.2 Response requirement
Every response that proposes or applies changes must include:

- **Docs consulted:** citations to the specific sections used, including dynamic docs when applicable.

If any required docs are missing, include:

- **Missing docs:** list missing items, then proceed with best effort.

---

## 2) Hard constraints

If you cannot comply, say so and explain why.

1) **No new files without reuse analysis.**  
   Before creating any file, including docs, check whether an existing file can be extended.  
   Response must include:  
   **Reuse analysis:** checked `A`, `B`, `C`. Cannot extend because `<technical reason>`.

2) **No rewrites when refactoring is possible.**  
   Prefer incremental refactors over wholesale rewrites.  
   Before proposing or doing a rewrite, response must include:  
   **Refactor not viable because:** `<specific constraint>`.

3) **No generic advice.**  
   All recommendations must include concrete integration points with citations (code + docs).  
   If line numbers are unavailable, use `#AnchorName` and state why.

4) **Do not ignore existing architecture.**  
   Identify existing patterns and components first. Extend them and consolidate duplicates.  
   When introducing a new component or pattern, or changing architecture, response must include:  
   **Extends existing pattern:** `path/to/file.ext:line` (or `#AnchorName`).

5) **Enforce single source of truth.**  
   When the same value or logic is needed in more than one place, reuse an existing definition or extract one shared definition before adding another copy.  
   Prefer the smallest viable refactor (for example: shared constant, helper, value object, or function) over duplicating literals or logic.  
   If duplication must remain, response must include:  
   **Single source of truth:** reused `A` / extracted `B`; could not consolidate `<specific constraint>`.

6) **Preserve intentional folder hierarchy.**  
   New files and folders must follow the project’s grouping logic and use meaningful names that reflect their contents or role.  
   Honor framework or technology-imposed structure first. Otherwise, group related files together and keep shared concerns in explicit shared locations.  
   If no suitable location exists, prefer the smallest viable folder refactor over ad hoc placement.  
   Response must include:  
   **Folder hierarchy:** reused `A` / created `B` because `<grouping logic>`; constraints: `<technology/framework limits or none>`.

---

## 3) Preferred style

- Prefer small, reversible, reviewable changes.
- Prefer extending existing code over introducing new abstractions.
- Prefer explicitness over cleverness.
- Prefer composition over inheritance.

---

## 4) Workflow

First choose the workflow mode:
- use **Regular work** for normal changes,
- use **Documentation bootstrap mode** only when its trigger conditions apply.

Then choose the execution path:
- use **Path A** if the tool can edit files,
- use **Path B** if it cannot.

### 4.1 Regular work (default)
Use this mode for normal feature work, fixes, refactors, and ordinary documentation changes that are not part of documentation bootstrap mode.

#### 4.1.1 Common steps
1. **Understanding** (1–3 bullets): task + constraints.
2. **Docs consulted**: cite the `README.md` / `docs/` sections used.
3. **Plan** (short, numbered). Include reuse analysis if relevant.
4. **Change intent**:
   - list files or areas to touch (with citations),
   - describe intended edits so they can be checked against git diff,
   - cite docs that justify key decisions.

#### 4.1.2 Path A — tool CAN modify repository files
5. **Apply implementation changes**.
6. **QA**: validate the actual working tree after step 5.
7. **Docs changes + Docs impact**:
   - update `README.md` and/or `docs/` when relevant,
   - if adding a new doc, also update `docs/table-of-contents.md`,
   - state **Docs impact** or explicitly **Docs impact: none**.
8. **Applied changes summary**:
   - what actually changed,
   - any deviation from plan or change intent,
   - files touched (citations when practical).

**Rule:** In Path A, do not generate patch or diff blocks in chat unless the user explicitly requests them.

#### 4.1.3 Path B — tool CANNOT modify repository files
5. **Provide implementation patch/snippets**:
   - prefer a minimal diff or patch; otherwise provide focused snippets,
   - include exact file paths and enough context to apply safely.
6. **QA**: list commands or checks to run after manual apply.
7. **Provide docs patch/snippets + Docs impact**:
   - include `README.md` and `docs/` patches or snippets when relevant,
   - include `docs/table-of-contents.md` updates if adding a new doc,
   - or explicitly **Docs impact: none**.
8. **Manual-apply summary**:
   - apply order,
   - risky steps or follow-ups.

### 4.2 Documentation bootstrap mode (existing projects only)
Use this mode only when all of the following are true:
- the project already has meaningful implemented code or behavior,
- documentation is missing, weak, oversized, or poorly structured,
- the user asks to align the project with this AGENTS.md or to bootstrap/refactor project documentation.

This mode is not the default for ordinary feature work.

In documentation bootstrap mode, the default scope is documentation only.  
Do not modify implementation files unless the user explicitly asks for implementation changes.

#### 4.2.1 First interaction: bootstrap plan only
When entering documentation bootstrap mode, do not generate all docs in one response.

First produce only a **Documentation bootstrap plan**:
- current documentation inventory,
- key documentation gaps,
- proposed minimum documentation baseline,
- additional docs likely needed (if any),
- proposed generation/refactor order,
- which file should be produced or refactored next,
- brief justification for that order.

Stop after the plan and wait for user confirmation to continue.

#### 4.2.2 Single-file review cycle
After the bootstrap plan is accepted, each subsequent cycle must handle exactly one substantive documentation file.

For each cycle:
1. select the next target file,
2. generate or refactor only that file,
3. explain which sources were used (code, README, existing docs),
4. explain why this file is being produced now,
5. if needed, update `docs/table-of-contents.md` only to register or re-index that file,
6. stop and ask the user to review it,
7. wait for explicit user instruction before continuing.

Do not generate the next substantive documentation file until the user explicitly asks to continue.

#### 4.2.3 Default document order
Unless the user requests a different order, use this sequence:

1. `docs/table-of-contents.md`
2. `docs/project-brief.md`
3. `docs/system-patterns.md`
4. `docs/project-rules.md`
5. additional focused docs, one by one, as justified by project scope
6. `README.md`
7. final cross-document normalization pass

#### 4.2.4 Final cross-document normalization pass (mandatory)
After all planned documentation files have been created or refactored, perform one final documentation-only pass across:
- `README.md`,
- all relevant `docs/*.md` files.

Goals of this pass:
- ensure cross-document consistency,
- fix contradictions,
- trim unnecessary overlap,
- align terminology, filenames, and references,
- verify that `docs/table-of-contents.md` reflects the final document set and minimum/core reading set.

This pass is mandatory in documentation bootstrap mode, even if no large changes are expected.

#### 4.2.5 Bootstrap rules
During documentation bootstrap:
- create or refactor one substantive documentation file per cycle,
- do not batch multiple new docs in one turn,
- do not refactor `README.md` before the long-form target docs exist,
- do not create placeholder docs unless they already contain useful content,
- prefer refactoring or reusing existing documentation before creating new files.

#### 4.2.6 Minimum reading growth rule
During bootstrap, the effective minimum/core reading set grows incrementally.

After a documentation file is reviewed and accepted by the user:
- add it to the minimum/core reading set in `docs/table-of-contents.md` if it is expected to influence future implementation decisions,
- treat it as required reading in future agent work.

#### 4.2.7 Execution path inside bootstrap mode
Within each bootstrap cycle:
- use **Path A** if the tool can modify repository files,
- use **Path B** if the tool cannot modify repository files.

In bootstrap mode:
- **Path A** means apply the current documentation-file change directly,
- **Path B** means provide the current documentation-file patch or snippet only.

The single-file review cycle in this section takes precedence over any broader batching allowed elsewhere.

---

## 5) Engineering rules (language-agnostic)

### 5.1 General
1. Follow standard conventions (language/ecosystem idioms).
2. Keep it simple: reduce complexity aggressively.
3. Always look for the root cause, not symptoms.

### 5.2 Design
1. Keep configurable data at high levels (composition roots / wiring layers).
2. Prefer polymorphism to `if/else` or `switch/case` for behavior selection.
3. Separate concurrency/multi-threading from core domain logic.
4. Prevent over-configurability; do not add knobs without strong need.
5. Use dependency injection for external dependencies (I/O, time, randomness, network, persistence).
6. Follow the Law of Demeter; know only direct dependencies.

### 5.3 Understandability
1. Be consistent.
2. Use explanatory variables.
3. Encapsulate boundary conditions.
4. Prefer dedicated value objects to primitive types.
5. Avoid logical dependency (hidden ordering/state requirements).
6. Avoid negative conditionals when a positive form is clearer.

### 5.4 Naming
1. Use descriptive, unambiguous names.
2. Make meaningful distinctions.
3. Use pronounceable names.
4. Use searchable names.
5. Replace magic numbers with named constants.
6. Avoid encodings (no prefixes/type info in names).

### 5.5 Functions / methods
1. Keep them small.
2. Make them do one thing.
3. Use descriptive names.
4. Prefer fewer arguments.
5. Avoid side effects, or isolate them explicitly at boundaries.
6. Avoid flag arguments; split into separate operations.

### 5.6 Comments
1. Explain intent in code first.
2. Avoid redundancy and noise.
3. Do not comment out code; remove it.
4. Use comments for intent, tricky clarifications, and warnings of consequences.

### 5.7 Source structure
1. Separate concepts vertically; keep related code dense.
2. Declare variables close to usage.
3. Keep dependent and similar functions close.
4. Organize top-down: high-level before details.
5. Keep lines short; avoid horizontal alignment.
6. Use whitespace to communicate structure; do not break indentation.

### 5.8 Objects and data structures
1. Hide internal structure.
2. Prefer simple data carriers when appropriate; objects when behavior is central.
3. Avoid hybrids (half object / half data).
4. Keep objects small; do one thing; keep few instance variables.
5. Base types should know nothing about derivatives.
6. Prefer many functions over passing code into a selector function.
7. Prefer non-static methods unless strongly idiomatic otherwise.

### 5.9 Tests
1. Prefer one assert per test when practical.
2. Keep tests readable, fast, independent, and repeatable.
3. Prefer deterministic tests; avoid real network/time unless explicitly testing integration.

### 5.10 Code smells (avoid)
- Rigidity
- Fragility
- Immobility
- Needless complexity
- Needless repetition
- Opacity

---

## 6) Traceability (citations)

Use citations for:
- places you will change,
- patterns you are extending,
- files inspected for reuse analysis,
- things you propose to delete or refactor,
- docs rules or patterns you are applying.

Format:
- `relative/path/to/file.ext:123` (preferred)
- `relative/path/to/file.ext#AnchorName` (if line numbers are unavailable; state why)

---

## 7) Verification (QA)

For any non-trivial change, include a **QA** section:
- prefer the repository’s documented workflow in `docs/project-rules.md`,
- in Path A, QA validates the applied working tree,
- in Path B, QA lists what to run after manual apply,
- if you cannot run commands, say so and still list what should be run.

For documentation-only bootstrap cycles, QA may be limited to:
- link consistency,
- filename/reference consistency,
- index/register consistency,
- obvious content-structure checks.

---

## 8) Documentation rules (`README.md` + `docs/` are the shared source of truth)

### 8.1 Documentation split of responsibilities
- **`README.md`** is the quick-start, high-signal entrypoint:
  - keep existing badges,
  - briefly explain what the project is and why it is useful,
  - show the fastest path to a first successful result,
  - keep it short and to the point,
  - link to `docs/` for details.

- **`docs/`** contains long-form or reference content:
  - setup and installation details,
  - configuration,
  - usage guides / examples,
  - integration and API/reference material when applicable,
  - architecture and patterns,
  - troubleshooting / operations,
  - contributor / agent guidance,
  - other detailed guides.

### 8.2 Documentation updates and refactors are valid changes
Update or refactor documentation when you change APIs, behavior, configuration, architecture patterns, or development workflow:
- update `README.md` if the quick-start path, positioning, or first-run experience changes,
- update or add files in `docs/` for long-form details.

When adopting or aligning a project to this AGENTS.md, documentation restructuring or refactoring is an allowed docs change, including creating the minimum baseline docs when missing.

### 8.3 Adding new docs is allowed when justified
If new content does not fit any existing documentation file:
- add a new focused doc under `docs/`,
- update `docs/table-of-contents.md`,
- justify why the content does not belong in an existing doc,
- if the new doc is expected to influence future implementation decisions, add it to the **Minimum Reading Set / Core Docs** section in `docs/table-of-contents.md`,
- during documentation bootstrap for existing projects, add new docs one by one using section 4.2.

This does not bypass **No new files without reuse analysis**; it satisfies it when reuse analysis shows no existing doc is an appropriate home.

Project folder hierarchy / codebase layout rules belong in `docs/system-patterns.md` by default.  
Use another existing doc, or a dedicated focused doc, only when the hierarchy rules are substantial enough to warrant it.  
If documented outside `docs/system-patterns.md`, add an explicit reference in `docs/system-patterns.md` and `docs/table-of-contents.md`.  
If that document is expected to influence future implementation decisions, add it to the **Minimum Reading Set / Core Docs** section in `docs/table-of-contents.md`.

### 8.4 Documentation bootstrap and refactor
This AGENTS.md may be introduced into:
- a new/empty project, or
- an existing project with partial, missing, oversized, or poorly structured documentation.

When aligning a project with this AGENTS.md:
- establish or refactor the documentation structure so `README.md` is the quick-start entrypoint and `docs/` contains long-form/reference content,
- create or refactor the minimum documentation baseline when missing or not fit for purpose,
- reuse and refactor existing documentation before creating new docs,
- use **Documentation bootstrap mode** (section 4.2) for existing projects with implemented code and inadequate documentation.

#### Minimum documentation baseline
If missing or not fit for purpose, create or refactor:
- `README.md`
- `docs/table-of-contents.md`
- `docs/project-brief.md`
- `docs/system-patterns.md`
- `docs/project-rules.md`

#### Additional docs
Create additional focused docs only when justified by project scope.

If a new or refactored doc is expected to influence future implementation decisions:
- add it to the **Minimum Reading Set / Core Docs** section in `docs/table-of-contents.md`.

---

## 9) Conflicts

If any instruction here conflicts with a user request:
- follow the user’s explicit instruction and state the deviation from this file,
- if forced to proceed without clarity, prefer:
  1) correctness and safety,
  2) minimal diff,
  3) preserving existing architecture and patterns.
