#!/usr/bin/env python3

import pytest

from unittest.mock import patch

from indisoluble.a_healthy_dns.tools import uint32_current_time as u32_module
from indisoluble.a_healthy_dns.tools.uint32_current_time import uint32_current_time


class TestUint32CurrentTime:
    @pytest.mark.parametrize(
        "current_time,expected",
        [
            (12345.978, 12345),
            (
                float(u32_module._MAX_UINT32),
                u32_module._MAX_UINT32,
            ),
        ],
    )
    @patch("indisoluble.a_healthy_dns.tools.uint32_current_time.time.time")
    def test_returns_integer_timestamp_when_within_uint32_range(
        self, mock_time, current_time, expected
    ):
        mock_time.return_value = current_time

        assert uint32_current_time() == expected

    @patch("indisoluble.a_healthy_dns.tools.uint32_current_time.time.time")
    def test_raises_overflow_when_timestamp_exceeds_uint32_limit(self, mock_time):
        mock_time.return_value = float(u32_module._MAX_UINT32 + 1)

        with pytest.raises(OverflowError) as excinfo:
            uint32_current_time()

        assert str(u32_module._MAX_UINT32 + 1) in str(excinfo.value)
        assert str(u32_module._MAX_UINT32) in str(excinfo.value)
