#!/usr/bin/env python3

from typing import Tuple


def is_valid_subdomain(name: str) -> Tuple[bool, str]:
    if not name:
        return (False, "It cannot be empty")

    if not all(
        label and all(c.isalnum() or c == "-" for c in label)
        for label in name.split(".")
    ):
        return (False, "Labels must contain only alphanumeric characters or hyphens")

    return (True, "")
