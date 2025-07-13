#!/usr/bin/env python3

"""32-bit unsigned integer time utilities.

Provides functions to get current time as 32-bit unsigned integer with
overflow protection for DNS serial number generation.
"""

import time


_MAX_UINT32 = (1 << 32) - 1  # 4294967295


def uint32_current_time() -> int:
    """Get current time as 32-bit unsigned integer with overflow check."""
    current_time = int(time.time())
    if current_time > _MAX_UINT32:
        raise OverflowError(
            f"Current timestamp {current_time} exceeds 32-bit unsigned integer limit ({_MAX_UINT32})"
        )

    return current_time
