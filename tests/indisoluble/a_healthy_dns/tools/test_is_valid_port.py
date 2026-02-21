#!/usr/bin/env python3

import pytest

from indisoluble.a_healthy_dns.tools.is_valid_port import is_valid_port


@pytest.mark.parametrize("valid_port", [1, 80, 443, 8080, 53, 22, 3306, 65535])
def test_valid_ports(valid_port):
    result, message = is_valid_port(valid_port)
    assert result is True
    assert message == ""


@pytest.mark.parametrize(
    "invalid_port,expected_message",
    [
        ("80", "Port must be an integer"),
        (None, "Port must be an integer"),
        (8080.5, "Port must be an integer"),
        ([], "Port must be an integer"),
        ({}, "Port must be an integer"),
        (0, "Port must be between 1 and 65535"),
        (-1, "Port must be between 1 and 65535"),
        (65536, "Port must be between 1 and 65535"),
        (100000, "Port must be between 1 and 65535"),
    ],
)
def test_invalid_ports(invalid_port, expected_message):
    result, message = is_valid_port(invalid_port)
    assert result is False
    assert message == expected_message
