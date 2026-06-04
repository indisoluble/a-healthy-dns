# Implementation Notes

Python-specific implementation guidance for **A Healthy DNS**.

This document owns language-, runtime-, and module-level conventions. Repository-wide engineering principles live in [`docs/engineering-rules.md`](engineering-rules.md); testing in [`docs/testing.md`](testing.md); workflow in [`docs/workflow.md`](workflow.md); architecture in [`docs/architecture.md`](architecture.md).

## Runtime And Package Shape

| Item | Rule |
|---|---|
| Python version | **3.11 minimum** (`pyproject.toml:project.requires-python=">=3.11"`) |
| Entry point | `a-healthy-dns` CLI -> `indisoluble.a_healthy_dns.main:main` (`pyproject.toml:[project.scripts]`) |
| Package root | `indisoluble/a_healthy_dns/` |
| Test root | `tests/indisoluble/a_healthy_dns/` mirrors the source tree by default |

## Dependencies

Dependencies are managed in `pyproject.toml`. Runtime dependencies belong in `[project.dependencies]`; test-only dependencies belong in `[project.optional-dependencies].test`.

| Package | Constraint | Purpose |
|---|---|---|
| `dnspython` | `>=2.8.0,<3.0.0` | DNS protocol, zones, records, and DNSSEC signing |
| `cryptography` | `>=46.0.5,<47.0.0` | DNSSEC key loading and crypto operations |

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

## Module-Level Constants And Type Parameters

Here, **constant** means a module-level `UPPER_SNAKE_CASE` or `_UPPER_SNAKE_CASE` assignment intended to stay stable. Lowercase module-level assignments are not constants.

Use this module-level declaration order:

1. Type definitions used by module-level constants, helpers, or public APIs: `TypeVar`, `ParamSpec`, type aliases, `NamedTuple`, and `Enum`.
2. Private constants.
3. Public constants.
4. Helper functions, public functions, and ordinary classes with methods or runtime behavior.

Separate groups with blank lines. Within each group, sort names alphabetically (ascending, case-sensitive). If both private and public constants exist, private constants come first:

```python
_P = ParamSpec("_P")


class RRSigLifetime(NamedTuple):
    resign: int
    expiration: int


_MAX_TTL = (1 << 31) - 1

DEFAULT_TTL = 60
```

Ordinary classes normally belong below constants. If a module-level constant is constructed from a class in the same module, define the class first so the assignment can run.

```python
class DefaultPolicy:
    ...


_DEFAULT_POLICY = DefaultPolicy()
```

## Module Headers

Non-empty source modules start with the shebang line and then a module docstring, except intentionally empty package `__init__.py` files:

```python
#!/usr/bin/env python3

"""Short description of what this module provides.

Optional longer explanation of scope and design intent.
"""
```

Test files include the shebang (`#!/usr/bin/env python3`) but omit the module docstring. Empty `__init__.py` files are the deliberate exception on the source side.

## Validation Function Signature

Primitive validators in `tools/` return `Tuple[bool, str]`: `(True, "")` on success and `(False, error_message)` on failure. Input type is `Any` because validators accept untrusted external values.

```python
from typing import Any, Tuple


def is_valid_ip(ip: Any) -> Tuple[bool, str]:
    if not isinstance(ip, str):
        return (False, "It must be a string")

    return (True, "")
```

## Class Member Layout

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

    def __enter__(self) -> "ExampleService": ...

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
    def health_port(self) -> Optional[int]: ...

    def __init__(self, ip: Any, health_port: Any, is_healthy: bool) -> None: ...

    def __eq__(self, other: Any) -> bool: ...
    def __hash__(self) -> int: ...
    def __repr__(self) -> str: ...

    def updated_status(self, is_healthy: bool) -> "AHealthyIp": ...
```

## NamedTuple Usage

Use `NamedTuple` for immutable containers with no behavior beyond construction, such as config, key containers, and signature timing. Use classes when objects carry behavior (`AHealthyIp`, `AHealthyRecord`, `ZoneOrigins`).

```python
class DnsServerConfig(NamedTuple):
    zone_origins: ZoneOrigins
    primary_name_server: str
    name_servers: FrozenSet[str]
    a_records: FrozenSet[AHealthyRecord]
    ext_private_key: Optional[ExtendedPrivateKey]
```

## Logging Format

Use `%s`-style format strings with `logging` calls, not f-strings or `str.format()`:

```python
logging.error("Invalid IP address '%s': %s", ip, error)
logging.debug("Created A record with ttl: %d, and IPs: %s", ttl, ips)
```

## Type Annotations

In source modules, every function and method signature includes parameter and return type annotations. Use `Any` only when intentionally accepting unvalidated external input, such as validator parameters.

```python
def is_valid_ip(ip: Any) -> Tuple[bool, str]:
    ...


def make_a_record(
    max_interval: int, ips: FrozenSet[str]
) -> Optional[dns.rdataset.Rdataset]:
    ...


def updated_status(self, is_healthy: bool) -> "AHealthyIp":
    ...
```
