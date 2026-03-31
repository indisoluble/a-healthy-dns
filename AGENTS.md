# AGENTS.md

Non-negotiable rules for any AI coding agent (IDE agents, PR agents, chat agents) working in this repository.

**Release date:** 2026-03-31 - **Canonical source:** https://github.com/indisoluble/AGENTS-spec

**Inspiration / lineage (non-normative):**
- Robert C. Martin (“Uncle Bob”) *Clean Code* principles
- msitarzewski/AGENT-ZERO

## Goals
- Produce reviewable changes consistent with repository style.
- Prevent churn, duplication, and architectural drift.
- Keep changes verifiable and documented.

---

## 0) Definitions

- **Agent**: any AI tool producing analysis, plans, patches, or file edits for this repository.
- **Regular work**: normal feature work, fixes, refactors, or ordinary documentation updates.
- **Documentation bootstrap mode**: used when this AGENTS.md is introduced into an existing project with meaningful code but inadequate documentation.
- **Path A**: the tool can modify repository files.
- **Path B**: the tool cannot modify repository files.
- **Implementation changes**: repository changes outside `README.md` and `docs/`.
- **Docs changes**: changes to `README.md` and/or files under `docs/`.
- **Substantive documentation file**: the main documentation file being created or refactored in the current bootstrap cycle. `docs/table-of-contents.md` updates used only to register that file do not count as a second substantive file.
- **Task-relevant documentation**: any document that defines, constrains, or materially affects the files, behavior, interfaces, folder placement, workflow, or acceptance checks involved in the requested change.
- **Citation**:
  - `path/to/file.ext:123` (preferred), or
  - `path/to/file.ext#AnchorName` (if line numbers are unavailable; state why).

---

## 1) Docs-first (mandatory)

### 1.1 Required reading
Before proposing or applying changes, consult project documentation as primary input.

#### Base required reading
- `README.md` — project entrypoint and fastest path to a first successful result.
- `docs/table-of-contents.md` — documentation index and minimum/core reading registry.
- `docs/project-brief.md` — goals, non-goals, constraints, requirements.
- `docs/system-patterns.md` — architecture patterns, structural conventions, and the default home for folder hierarchy / codebase layout rules.
- `docs/project-rules.md` — language/tool specifics, repository-specific code conventions, and QA commands.

#### Extended required reading
Read all task-relevant items from:
- the **Minimum Reading Set / Core Docs / Primary Docs** section in `docs/table-of-contents.md` (project naming may vary),
- docs explicitly linked from `README.md` for setup, usage, configuration, architecture, troubleshooting, or operations,
- docs explicitly designated by `docs/system-patterns.md` for folder hierarchy, codebase layout, or file-grouping conventions.

If `docs/table-of-contents.md` exists but has no minimum/core reading section:
1. read the base required reading,
2. use best effort to identify the most relevant docs linked from `README.md` and `docs/table-of-contents.md`.

### 1.2 Response requirement
Every response that proposes or applies changes must include:

- **Docs consulted:** citations to the specific sections used, including dynamic docs when applicable.

If required docs are missing, include:

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
   All recommendations must include concrete integration points with citations.  
   If line numbers are unavailable, use `#AnchorName` and state why.

4) **Do not ignore existing architecture.**  
   Identify existing patterns and components first. Extend them and consolidate duplicates.  
   When introducing a new component or pattern, or changing architecture, response must include:  
   **Extends existing pattern:** `path/to/file.ext:line` (or `#AnchorName`).

5) **Enforce single source of truth.**  
   Reuse an existing definition or extract a shared definition before duplicating values or logic.  
   Prefer the smallest viable refactor.  
   If duplication must remain, response must include:  
   **Single source of truth:** reused `A` / extracted `B`; could not consolidate `<specific constraint>`.

6) **Preserve intentional folder hierarchy.**  
   New files and folders must follow the project’s grouping logic and meaningful naming.  
   Honor framework or technology-imposed structure first. Otherwise, group related files and keep shared concerns in explicit shared locations.  
   If no suitable location exists, prefer the smallest viable folder refactor over ad hoc placement.  
   Response must include:  
   **Folder hierarchy:** reused `A` / created `B` because `<grouping logic>`; constraints: `<technology/framework limits or none>`.

---

## 3) Preferred style

- Prefer small, reversible, reviewable changes.
- Prefer extending existing code over new abstractions.
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
   - apply all documentation updates required by section 8,
   - update `docs/table-of-contents.md` if document structure changes,
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
   - include all documentation changes required by section 8,
   - include `docs/table-of-contents.md` updates if document structure changes,
   - or explicitly **Docs impact: none**.
8. **Manual-apply summary**:
   - apply order,
   - risky steps or follow-ups.

### 4.2 Documentation bootstrap mode
Use this mode only when:
- the project already has meaningful implemented code,
- documentation is missing, weak, oversized, or poorly structured,
- the user asks to align the project with this AGENTS.md or to bootstrap/refactor project documentation.

Bootstrap mode is documentation-only unless the user explicitly asks for implementation changes.

#### 4.2.1 First interaction: bootstrap plan only
When entering bootstrap mode, do not generate all docs in one response.

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
- verify that each document has a clear primary purpose,
- verify that each major topic has one canonical home,
- reduce duplicated substantive content by replacing it with concise summaries and links where appropriate,
- verify that `docs/table-of-contents.md` reflects the final document set and minimum/core reading set.

This pass is mandatory even if no large changes are expected.

#### 4.2.5 Bootstrap rules
During documentation bootstrap:
- create or refactor one substantive documentation file per cycle,
- do not batch multiple new docs in one turn,
- do not refactor `README.md` before the long-form target docs exist,
- do not create placeholder docs unless they already contain useful content,
- prefer refactoring or reusing existing documentation before creating new files.

#### 4.2.6 Minimum reading growth rule
After a documentation file is reviewed and accepted by the user:
- add it to the minimum/core reading set in `docs/table-of-contents.md` if it is expected to influence future implementation decisions,
- treat it as required reading in future agent work.

#### 4.2.7 Execution path inside bootstrap mode
Within each bootstrap cycle:
- use **Path A** if the tool can modify repository files,
- use **Path B** if the tool cannot.

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

### 8.0 Documentation-specific definitions
- **Documentation update is relevant**: a change affects project behavior, setup, configuration, architecture, interfaces, workflow, recurring code conventions, or the accuracy, scope, or canonical ownership of existing documentation.
- **Canonical home**: the single document that owns the detailed or normative treatment of a topic.
- **Substantive information**: explanatory, normative, procedural, or reference content whose continued duplication would create a maintenance risk. Brief navigational summaries, local context, and README quick-start summaries do not count unless they become detailed enough to compete with the canonical source.
- **Not fit for purpose**: missing critical content, materially outdated, structurally confusing, oversized for its role, or inconsistent with the current documentation split.

### 8.1 Documentation split of responsibilities
- **`README.md`** is the quick-start, high-signal entrypoint and a summary-and-navigation document:
  - keep existing badges,
  - briefly explain what the project is and why it is useful,
  - show the fastest path to a first successful result,
  - keep it short and to the point,
  - link to canonical long-form docs for detail.

- **`docs/`** contains canonical long-form or reference content:
  - setup and installation details,
  - configuration,
  - usage guides / examples,
  - integration and API/reference material when applicable,
  - architecture and patterns,
  - troubleshooting / operations,
  - contributor / agent guidance,
  - other detailed guides.

By default:
- `docs/system-patterns.md` owns structural repository organization and architecture patterns,
- `docs/project-rules.md` owns language/tool-specific practices, QA workflow, and repository-specific code conventions.

### 8.1.1 Repository-specific code conventions
`docs/project-rules.md` is the default home for repository-specific code conventions that affect future code generation.

These conventions must be derived from the current repository code when possible. They should document recurring implementation patterns that future agent-generated code is expected to follow, for example:
- import structure,
- type-hint forms,
- string formatting,
- naming conventions,
- interface/protocol patterns,
- class/member layout,
- other repeatable code-shape rules visible in the repository.

During documentation bootstrap, if the project already contains enough implementation to infer recurring code patterns, create or refactor a concise `Code conventions` section in `docs/project-rules.md`.

That section should:
- describe repository-observed patterns, not generic language advice,
- distinguish between conventions that are already consistent and conventions that are common but not yet fully normalized,
- stay concise and example-driven,
- focus only on conventions that materially improve consistency of future generated code.

During regular work, update that section in the same change cycle whenever implementation changes introduce, normalize, replace, or intentionally retire a recurring code convention.

### 8.1.2 Document single responsibility and canonical ownership
Documentation should follow single responsibility as closely as practical.

Rules:
- Each document should have one primary purpose and clear scope.
- Each topic should have one canonical home.
- Other documents should reference or briefly summarize that canonical source only when needed for navigation, orientation, or local comprehension.
- Avoid maintaining the same substantive information in multiple documents.
- When a document accumulates unrelated responsibilities, split or refactor it.
- When information fits an existing document’s scope, extend that document instead of creating a parallel source.

`README.md` is the main exception because it is the project entrypoint. It may intentionally repeat a small amount of high-value information needed for orientation and quick start, but that duplication must be minimal. `README.md` should summarize and link to canonical long-form documents rather than restating them in detail.

Prefer:
- one canonical document per topic,
- short navigational summaries outside the canonical document,
- explicit cross-links instead of duplicated explanation.

### 8.2 Documentation update policy
When a documentation update is relevant:
- update the canonical document that owns the changed topic,
- update `README.md` only if the quick-start path, positioning, or first-run experience changes,
- update `docs/project-rules.md` when implementation changes affect repository-specific code conventions, QA workflow, or recurring code patterns,
- update `docs/system-patterns.md` when structural repository organization, architecture patterns, or file-grouping rules change,
- refactor existing documents when scope has drifted, responsibilities have become mixed, or the same substantive information appears in more than one place,
- prefer moving information to its canonical document and replacing duplicate content with concise summaries and links.

Documentation restructuring or refactoring is valid when needed to:
- restore accurate document boundaries,
- reduce duplicated substantive information,
- keep `README.md` brief and entrypoint-focused,
- preserve a clear canonical home for each topic.

### 8.3 Adding new docs
If new content does not fit any existing documentation file:
- add a new focused doc under `docs/`,
- update `docs/table-of-contents.md`,
- justify why the content does not belong in an existing doc,
- add it to the **Minimum Reading Set / Core Docs** section in `docs/table-of-contents.md` if it is expected to influence future implementation decisions,
- during documentation bootstrap, add new docs one by one using section 4.2.

This does not bypass **No new files without reuse analysis**; it satisfies it when reuse analysis shows no existing doc is an appropriate home.

If folder hierarchy or codebase layout rules are documented outside `docs/system-patterns.md`, add an explicit reference in:
- `docs/system-patterns.md`,
- `docs/table-of-contents.md`.

### 8.4 Documentation bootstrap and alignment
This AGENTS.md may be introduced into:
- a new/empty project, or
- an existing project with documentation that is missing, weak, oversized, poorly structured, or not fit for purpose.

When aligning a project with this AGENTS.md:
- establish or refactor the documentation split so `README.md` remains the quick-start entrypoint and `docs/` remains the canonical home of long-form content,
- create or refactor the minimum documentation baseline when missing or not fit for purpose,
- reuse and refactor existing documentation before creating new docs,
- use **Documentation bootstrap mode** (section 4.2) for existing projects with meaningful code and inadequate documentation.

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
