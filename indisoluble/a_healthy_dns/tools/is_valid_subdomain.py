#!/usr/bin/env python3

"""Subdomain and domain name validation utilities.

Provides functions to validate DNS subdomain names according to basic
DNS naming rules and character restrictions.
"""

from typing import Any, Tuple


def is_valid_subdomain(name: Any) -> Tuple[bool, str]:
    """Validate subdomain name format and character restrictions."""
    if not isinstance(name, str):
        return (False, "It must be a string")

    if not name:
        return (False, "It cannot be empty")

    if not all(
        label and all(c.isalnum() or c == "-" for c in label)
        for label in name.split(".")
    ):
        return (False, "Labels must contain only alphanumeric characters or hyphens")

    return (True, "")
