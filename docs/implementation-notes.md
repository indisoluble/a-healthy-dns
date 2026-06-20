# Implementation Notes

Python-specific implementation guidance for **A Healthy DNS**.

This document owns language-, runtime-, and module-level conventions. Repository-wide engineering principles live in [`docs/engineering-rules.md`](engineering-rules.md); testing in [`docs/testing.md`](testing.md); workflow in [`docs/workflow.md`](workflow.md); architecture in [`docs/architecture.md`](architecture.md).

Unless a section explicitly defines a narrower scope, the rules in this document are repository-wide Python implementation conventions for all source and test code. If one of these conventions is itself the problem, change it through the scoped pattern-change process in [`docs/engineering-rules.md`](engineering-rules.md#changing-established-patterns).

## Runtime And Package Shape

| Item | Rule |
|---|---|
| Python version | **3.11 minimum** (`pyproject.toml:project.requires-python=">=3.11"`) |
| Entry point | `a-healthy-dns` CLI -> `indisoluble.a_healthy_dns.main:main` (`pyproject.toml:[project.scripts]`) |
| Package root | `indisoluble/a_healthy_dns/` |
| Test root | `tests/indisoluble/a_healthy_dns/` mirrors the source tree by default |

## Dependencies

Dependencies are managed in `pyproject.toml`. Runtime dependencies belong in `[project.dependencies]`; test-only dependencies belong in `[project.optional-dependencies].test`.

Runtime dependency summary:

| Package | Constraint | Purpose |
|---|---|---|
| `dnspython` | `>=2.8.0,<3.0.0` | DNS message, zone, and record primitives; DNSSEC artifact signing support |
| `cryptography` | `>=48.0.1,<49.0.0` | DNSSEC key loading and crypto operations |

Test dependency summary:

| Package | Constraint | Purpose |
|---|---|---|
| `pytest` | `>=8.0,<9.0` | Test framework and fixtures |
| `pytest-cov` | `>=5.0,<6.0` | Pytest coverage integration |
| `coverage` | `>=7.0,<8.0` | Coverage measurement and reports |

Keep upper-bound pins at the next major version so minor and patch updates are allowed automatically.

## Naming Rules

| Context | Convention |
|---|---|
| Source modules | `snake_case.py` |
| Test modules | `test_<source_module>.py` |
| Class names | `PascalCase` |
| Function / method names | `snake_case` |
| Constants | `UPPER_SNAKE_CASE` |
| Private helpers | prefix `_` |
| CLI argument names | `kebab-case` (for example, `--hosted-zone`) |
| `argparse` dest / internal keys | `snake_case`, matching `ARG_*` constants where applicable |

## Import Ordering

Organize source and test imports into these groups, separated by blank lines:

1. Standard-library direct imports (`import X`)
2. Third-party direct imports (`import X`)
3. Standard-library from-imports (`from X import Y`)
4. Third-party from-imports (`from X import Y`)
5. Local imports (`from indisoluble.a_healthy_dns... import Y`)

Within each group, sort import statements alphabetically by full statement text.

```python
import json

import dns.dnssectypes
import dns.name
import pytest

from unittest.mock import patch

from dns.dnssecalgs.rsa import PrivateRSASHA256

from indisoluble.a_healthy_dns import dns_server_config_factory as dscf
from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp
```

Skip unused groups without collapsing the remaining groups. Local imports normally use `from ... import ...`; aliases are acceptable when they reduce repeated access noise.

## Module-Level Declarations

Here, **constant** means a module-level `UPPER_SNAKE_CASE` or `_UPPER_SNAKE_CASE` assignment intended to stay stable. Lowercase module-level assignments are not constants.

Here, **simple declaration** means a module-level declaration that defines a type shape or a lightweight local control-flow signal, without owning domain, service, framework, I/O, lifecycle, or mutation behavior. This group includes `TypeVar`, `ParamSpec`, type aliases, `NamedTuple`, `Enum`, and local exception classes used only to stop or redirect helper flow. A local exception may define `__init__` only to initialize a diagnostic exception message and store payload needed by the catcher.

Here, **runtime class** means a class with ordinary behavior: public methods or properties, domain state, service orchestration, framework inheritance contracts, resource lifecycle, I/O, mutation, or reusable API surface. Runtime classes are not simple declarations.

Use this module-level declaration order:

1. Simple declarations.
2. Private constants.
3. Public constants.
4. Private helper functions (`def _...`).
5. Public functions.
6. Runtime classes.

Keep simple declarations directly after imports, before constants and the rest of the module. Sort simple declarations alphabetically by declared identifier using a case-insensitive ordering (equivalent to `sorted(..., key=str.casefold)`), regardless of declaration type; do not use declaration-type subgroups. Separate declaration groups with blank lines. Sort constants alphabetically within their private and public groups. If both private and public constants exist, private constants come first:

```python
class RRSigLifetime(NamedTuple):
    resign: int
    expiration: int


class _DropQuery(Exception):
    ...


_P = ParamSpec("_P")


_MAX_TTL = (1 << 31) - 1

DEFAULT_TTL = 60
```

Use this classification. This table is only a grouping reference, not a declaration-order example:

| Declaration | Group |
|---|---|
| `ShouldAbortOp = Callable[[], bool]` | simple declaration: type alias |
| `class RRSigAction(NamedTuple): ...` | simple declaration: immutable data shape |
| `class RefreshARecordsResult(Enum): ...` | simple declaration: named state set |
| `class _DropQuery(Exception): ...` | simple declaration: local control-flow signal |
| `class _QuestionRejected(Exception): ...` with an `__init__` that stores an rcode | simple declaration: local control-flow signal with payload |
| `class AHealthyIp: ...` | runtime class: domain value object with behavior |
| `class DnsServerUdpHandler(socketserver.BaseRequestHandler): ...` | runtime class: framework handler contract |

Runtime classes normally belong after module-level private helper and public functions. If a module-level constant must be constructed from a runtime class in the same module, define that class before the constant so the assignment can run, and keep the ordering exception local to that module.

Do not move a runtime class above constants just because it is a class. Only simple declarations belong in the top declaration group.

## Module Headers

Non-empty source modules start with the shebang line and then a module docstring:

```python
#!/usr/bin/env python3

"""Short description of what this module provides.

Optional longer explanation of scope and design intent.
"""
```

Non-empty test files include the shebang (`#!/usr/bin/env python3`) but omit the module docstring. Empty package `__init__.py` files in both source and test trees are exempt from shebang and module docstring requirements.

## Validation Function Signature

Primitive validators in `tools/` return `tuple[bool, str]`: `(True, "")` on success and `(False, error_message)` on failure. Input type is `Any` because validators accept untrusted external values.

```python
from typing import Any


def is_valid_ip(ip: Any) -> tuple[bool, str]:
    if not isinstance(ip, str):
        return (False, "It must be a string")

    return (True, "")
```

## Class Member Layout

This layout applies to every class in source and tests, including test helper classes, fakes, and fixtures implemented as classes.

Class members are declared in this order:

1. class-owned `@property` accessors
2. `__init__`
3. dunder methods for equality, hashing, representation, or ordering when they are not the primary protocol-conformance surface
4. private methods
5. protocol conformance members, such as context-manager methods or protocol-required properties
6. class inheritance conformance members, such as framework hooks or base-class-required properties
7. public methods

Protocol conformance implements an interface or Python protocol, such as context-manager hooks. Class inheritance conformance implements an inherited class or framework contract, such as `socketserver.BaseRequestHandler.handle()`.

Add a single-line comment before each protocol or inheritance section, naming the exact protocol or inherited class contract. If both exist, place protocol conformance first. Properties required by a protocol or inherited class belong under that section comment, not above `__init__`. Add `# Public methods.` only when ordinary public API follows a protocol or inheritance section.

```python
class ExampleService:
    @property
    def name(self) -> str: ...

    def __init__(self, state: str) -> None: ...

    def __repr__(self) -> str: ...

    def _load_state(self) -> str: ...

    # Implements context manager protocol.
    @property
    def resource(self) -> str: ...

    def __enter__(self) -> ExampleService: ...

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool:
        ...

    # Implements BaseWorker inheritance contract.
    @property
    def worker_id(self) -> str: ...

    def run(self) -> None: ...

    # Public methods.
    def refresh(self) -> None: ...
```

When a class has no protocol or inheritance section, place public methods after private methods without a public-method section comment.

```python
class AHealthyIp:
    @property
    def ip(self) -> str: ...

    @property
    def health_port(self) -> int | None: ...

    def __init__(self, ip: Any, health_port: Any, is_healthy: bool) -> None: ...

    def __eq__(self, other: object) -> bool: ...
    def __hash__(self) -> int: ...
    def __repr__(self) -> str: ...

    def updated_status(self, is_healthy: bool) -> AHealthyIp: ...
```

## NamedTuple Usage

Use `NamedTuple` for immutable containers with no behavior beyond construction, such as config, key containers, and signature timing. Use classes when objects carry behavior (`AHealthyIp`, `AHealthyRecord`, `ZoneOrigins`).

```python
class DnsServerConfig(NamedTuple):
    zone_origins: ZoneOrigins
    primary_name_server: str
    name_servers: frozenset[str]
    a_records: frozenset[AHealthyRecord]
    ext_private_key: ExtendedPrivateKey | None
```

## Logging Format

Use `%s`-style format strings with `logging` calls, not f-strings or `str.format()`:

```python
logging.error("Invalid IP address '%s': %s", ip, error)
logging.debug("Created A record with ttl: %d, and IPs: %s", ttl, ips)
```

## Type Annotations

In source modules, every function and method signature includes parameter and return type annotations. Use `Any` only when intentionally accepting unvalidated external input, such as validator parameters.

Use modern Python 3.11 annotation spelling:

- Use built-in generic containers such as `list[str]`, `tuple[bool, str]`, `dict[str, Any]`, and `frozenset[AHealthyRecord]` instead of `typing.List`, `typing.Tuple`, `typing.Dict`, and `typing.FrozenSet`.
- Use union syntax such as `str | None` instead of `Optional[str]`.
- Use `from __future__ import annotations` when forward references are needed, then write the type name directly instead of quoting it.
- Keep importing typing constructs that do not have built-in syntax equivalents, such as `Any`, `Callable`, `NamedTuple`, and `ParamSpec`.

```python
from __future__ import annotations

from typing import Any


def is_valid_ip(ip: Any) -> tuple[bool, str]:
    ...


def make_a_record(max_interval: int, ips: frozenset[str]) -> dns.rdataset.Rdataset | None:
    ...


def updated_status(self, is_healthy: bool) -> AHealthyIp:
    ...
```
