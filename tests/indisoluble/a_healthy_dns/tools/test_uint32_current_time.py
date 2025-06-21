#!/usr/bin/env python3

import pytest

import indisoluble.a_healthy_dns.tools.uint32_current_time as u32_module

from unittest.mock import patch

from indisoluble.a_healthy_dns.tools.uint32_current_time import uint32_current_time


@patch("time.time")
def test_uint32_current_time_returns_expected_integer_from_float(mock_time):
    mock_time.return_value = 12345.978
    assert uint32_current_time() == 12345


@patch("time.time")
def test_uint32_current_time_returns_expected_integer_from_max_edge(mock_time):
    mock_time.return_value = float(u32_module._MAX_UINT32)
    assert uint32_current_time() == u32_module._MAX_UINT32


@patch("time.time")
def test_uint32_current_time_raises_overflow(mock_time):
    mock_time.return_value = float(u32_module._MAX_UINT32 + 1)
    with pytest.raises(OverflowError) as excinfo:
        uint32_current_time()
