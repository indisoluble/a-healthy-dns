#!/usr/bin/env python3

import time


_MAX_UINT32 = (1 << 32) - 1  # 4294967295


def uint32_current_time() -> int:
    current_time = int(time.time())
    if current_time > _MAX_UINT32:
        raise OverflowError(
            f"Current timestamp {current_time} exceeds 32-bit unsigned integer limit ({_MAX_UINT32})"
        )

    return current_time
