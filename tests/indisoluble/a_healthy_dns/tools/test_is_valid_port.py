#!/usr/bin/env python3

import pytest

from indisoluble.a_healthy_dns.tools.is_valid_port import is_valid_port


def _assert_valid_port(port):
    result, message = is_valid_port(port)

    assert result is True
    assert message == ""


def _assert_invalid_port(port, expected_message):
    result, message = is_valid_port(port)

    assert result is False
    assert message == expected_message


class TestValidPorts:
    @pytest.mark.parametrize("valid_port", [1, 22, 53, 80, 443, 3306, 8080, 65535])
    def test_accepts_port_in_valid_range(self, valid_port):
        _assert_valid_port(valid_port)


class TestInvalidPorts:
    @pytest.mark.parametrize(
        "invalid_port",
        [
            "80",
            None,
            8080.5,
            [],
            {},
        ],
    )
    def test_rejects_non_integer_values(self, invalid_port):
        _assert_invalid_port(invalid_port, "Port must be an integer")

    @pytest.mark.parametrize(
        "invalid_port",
        [
            0,
            -1,
            65536,
            100000,
        ],
    )
    def test_rejects_integer_values_outside_valid_range(self, invalid_port):
        _assert_invalid_port(invalid_port, "Port must be between 1 and 65535")
