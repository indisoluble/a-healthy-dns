#!/usr/bin/env python3

from typing import Tuple


def is_valid_ip(ip: str) -> Tuple[bool, str]:
    parts = ip.split(".")
    if len(parts) != 4:
        return (False, "IP address must have 4 octets")

    if not all(part.isdigit() and (0 <= int(part) <= 255) for part in parts):
        return (False, "Each octet must be a number between 0 and 255")

    return (True, "")
