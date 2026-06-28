#!/usr/bin/env python3

import unittest.mock

import pytest

from indisoluble.a_healthy_dns.records.soa_record import _iter_soa_serial
from indisoluble.a_healthy_dns.tools import uint32_current_time as u32_module
from indisoluble.a_healthy_dns.tools.uint32_current_time import uint32_current_time


class TestSoaSerialNumberSpace:
    @pytest.mark.parametrize(
        "current_time,expected",
        [
            (12345.978, 12345),
            (float(u32_module._MAX_UINT32), u32_module._MAX_UINT32),
        ],
    )
    @unittest.mock.patch(
        "indisoluble.a_healthy_dns.tools.uint32_current_time.time.time"
    )
    def test_soa_serial_source_returns_unsigned_32_bit_value(
        self, mock_time, current_time, expected
    ):
        mock_time.return_value = current_time

        assert uint32_current_time() == expected

    @unittest.mock.patch(
        "indisoluble.a_healthy_dns.tools.uint32_current_time.time.time"
    )
    def test_soa_serial_source_rejects_value_outside_uint32_range(self, mock_time):
        mock_time.return_value = float(u32_module._MAX_UINT32 + 1)

        with pytest.raises(OverflowError):
            uint32_current_time()

    @unittest.mock.patch("indisoluble.a_healthy_dns.records.soa_record.time.sleep")
    @unittest.mock.patch(
        "indisoluble.a_healthy_dns.records.soa_record.uint32_current_time"
    )
    def test_consecutive_generated_soa_serials_do_not_repeat(
        self, mock_uint32_current_time, mock_sleep
    ):
        mock_uint32_current_time.side_effect = [1234567890, 1234567890, 1234567891]
        serial_iterator = _iter_soa_serial()

        assert next(serial_iterator) == 1234567890
        assert next(serial_iterator) == 1234567891
        mock_sleep.assert_called_once_with(1)
