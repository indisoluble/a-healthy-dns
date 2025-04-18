#!/usr/bin/env python3

from typing import Tuple


def is_valid_port(port: int) -> Tuple[bool, str]:
    if not (1 <= port <= 65535):
        return (False, "Port must be between 1 and 65535")

    return (True, "")
