#!/usr/bin/env python3

"""IPv4 address validation utilities.

Provides functions to validate IPv4 addresses by checking octet format
and numeric ranges.
"""

from typing import Any, Tuple


def is_valid_ip(ip: Any) -> Tuple[bool, str]:
    """Validate IPv4 address format and octet ranges."""
    if not isinstance(ip, str):
        return (False, "It must be a string")

    parts = ip.split(".")
    if len(parts) != 4:
        return (False, "IP address must have 4 octets")

    if not all(part.isdigit() and (0 <= int(part) <= 255) for part in parts):
        return (False, "Each octet must be a number between 0 and 255")

    return (True, "")
