# Implementation Notes

Python-specific implementation guidance for **A Healthy DNS**.

This document is the canonical home for language-specific, runtime-specific, and module-level implementation conventions. Repository-wide engineering principles live in [`docs/engineering-rules.md`](engineering-rules.md); testing strategy and commands live in [`docs/testing.md`](testing.md); CI and release workflow live in [`docs/workflow.md`](workflow.md); architecture lives in [`docs/architecture.md`](architecture.md).

## Runtime And Package Shape

| Item | Rule |
|---|---|
| Python version | **3.10 minimum** (`setup.py:python_requires=">=3.10"`) |
| Entry point | `a-healthy-dns` CLI -> `indisoluble.a_healthy_dns.main:main` (`setup.py:entry_points`) |
| Package root | `indisoluble/a_healthy_dns/` |
| Test root | `tests/indisoluble/a_healthy_dns/` mirrors the source tree by default |

## Dependencies

Dependencies are managed in `setup.py`. Do not introduce a `requirements.txt` or `pyproject.toml` in parallel unless the packaging model is intentionally changed and the documentation is updated in the same change.

| Package | Constraint | Purpose |
|---|---|---|
| `dnspython` | `>=2.8.0,<3.0.0` | DNS protocol, zones, records, and DNSSEC signing |
| `cryptography` | `>=46.0.5,<47.0.0` | DNSSEC key loading and crypto operations |

Dev/test packages (`pytest`, `pytest-cov`) are installed directly in CI and are not declared in `setup.py`.

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

Each source module organizes imports into five groups, each separated by a blank line:

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

Skip groups that are not needed; do not collapse remaining groups together. Local imports normally use `from ... import ...`; aliasing the imported symbol or submodule is acceptable when repeated constant access would otherwise add noise. Test files follow the same rule.

## Module Headers

Executable source modules start with the shebang line and, unless the file is an intentionally empty package `__init__.py`, immediately follow it with a module-level docstring:

```python
#!/usr/bin/env python3

"""Short description of what this module provides.

Optional longer explanation of scope and design intent.
"""
```

Test files include the shebang (`#!/usr/bin/env python3`) but omit the module docstring. Empty `__init__.py` files are the deliberate exception on the source side.

## Validation Function Signature

Utility functions in `tools/` that validate a primitive value return `Tuple[bool, str]`: `(True, "")` on success and `(False, error_message)` on failure. Input type is `Any` to safely handle unvalidated external input.

```python
from typing import Any, Tuple


def is_valid_ip(ip: Any) -> Tuple[bool, str]:
    if not isinstance(ip, str):
        return (False, "It must be a string")

    return (True, "")
```

## Class Member Layout

Class members are declared in this order:

1. `@property` accessors
2. `__init__`
3. public methods
4. dunder methods (`__eq__`, `__hash__`, `__repr__`)

```python
class AHealthyIp:
    @property
    def ip(self) -> str: ...

    @property
    def health_port(self) -> Optional[int]: ...

    def __init__(self, ip: Any, health_port: Any, is_healthy: bool) -> None: ...

    def updated_status(self, is_healthy: bool) -> "AHealthyIp": ...

    def __eq__(self, other: Any) -> bool: ...
    def __hash__(self) -> int: ...
    def __repr__(self) -> str: ...
```

## NamedTuple Usage

`NamedTuple` is used for immutable containers that hold related fields with no behavior beyond construction, such as config, key containers, and signature timing. Classes are used when objects carry behavior (`AHealthyIp`, `AHealthyRecord`, `ZoneOrigins`).

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

All function and method signatures include parameter type annotations and return type annotations. Use `Any` only where the function intentionally accepts unvalidated external input, such as validator parameters.

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
