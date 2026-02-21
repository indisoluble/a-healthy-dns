#!/usr/bin/env python3

"""Port number validation utilities.

Provides functions to validate TCP/UDP port numbers within the valid
range of 1-65535.
"""

from typing import Any, Tuple


def is_valid_port(port: Any) -> Tuple[bool, str]:
    """Validate port number is within valid range (1-65535)."""
    if not isinstance(port, int):
        return (False, "Port must be an integer")

    if not (1 <= port <= 65535):
        return (False, "Port must be between 1 and 65535")

    return (True, "")
