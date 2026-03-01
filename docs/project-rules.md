# Project Rules

This file contains **Python-specific** rules and **QA commands**.  
`AGENTS.md` remains the source of truth for workflow, constraints, docs-first behavior, citations, and general engineering principles.

---

## Python-specific conventions (deltas)

### Interfaces / contracts
- Prefer `typing.Protocol` for interfaces (behavior contracts) rather than abstract base classes, unless there is a strong reason.

### Value objects / immutability
- Default for domain/value types: `@dataclass(frozen=True, slots=True)` when compatible with the repo/runtime.
- Avoid mutation unless there is an explicit, documented reason.

### Construction and invariants
- Prefer factory constructors for non-trivial initialization: `@classmethod def from_...(...)` / `create(...)`.
- Keep invariant checks centralized in the constructor/factory path (not scattered across call sites).

### External dependencies
- Do not add new runtime dependencies unless explicitly requested or clearly justified.

---

## QA commands (Python)

Prefer repo-defined entry points (Makefile/tox/nox/CI scripts) **when present**.

If the repo has no established workflow yet, propose:

- Lint / format:
  - `ruff check .`
  - `ruff format .` *(or `black .` if the repo standardizes on Black)*
- Type checking:
  - `mypy .` *(or `pyright` if the repo standardizes on Pyright)*
- Tests:
  - `pytest -q`