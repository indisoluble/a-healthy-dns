#!/usr/bin/env python3

"""Subdomain and domain name validation utilities.

Provides functions to validate DNS subdomain names according to basic
DNS naming rules and character restrictions.
"""

from typing import Any

_MAX_DNS_LABEL_LENGTH = 63
_MAX_DNS_NAME_LENGTH = 253
_ASCII_LABEL_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"
)


def _is_ascii_ldh_label(label: str) -> bool:
    return all(char in _ASCII_LABEL_CHARS for char in label)


def is_valid_subdomain(name: Any, origin_name: str = "") -> tuple[bool, str]:
    """Validate subdomain name format and character restrictions.

    origin_name is an already validated origin without a trailing root dot.
    """
    if not isinstance(name, str):
        return (False, "It must be a string")

    if not name:
        return (False, "It cannot be empty")

    if len(name) > _MAX_DNS_NAME_LENGTH:
        return (False, f"It must be {_MAX_DNS_NAME_LENGTH} characters or fewer")

    absolute_name = f"{name}.{origin_name}" if origin_name else name
    if len(absolute_name) > _MAX_DNS_NAME_LENGTH:
        return (
            False,
            f"It must be {_MAX_DNS_NAME_LENGTH} characters or fewer with the origin",
        )

    labels = name.split(".")
    if not all(label and _is_ascii_ldh_label(label) for label in labels):
        return (False, "Labels must contain only ASCII letters, digits, or hyphens")

    if not all(len(label) <= _MAX_DNS_LABEL_LENGTH for label in labels):
        return (False, f"Labels must be {_MAX_DNS_LABEL_LENGTH} characters or fewer")

    if not all(label[0].isalnum() and label[-1].isalnum() for label in labels):
        return (False, "Labels must start and end with an ASCII letter or digit")

    return (True, "")


def is_valid_fqdn(name: Any) -> tuple[bool, str]:
    """Validate a dotted hostname using subdomain validation as a base."""
    success, error = is_valid_subdomain(name)
    if not success:
        return (success, error)

    if "." not in name:
        return (False, "It must be a fully-qualified hostname")

    return (True, "")
