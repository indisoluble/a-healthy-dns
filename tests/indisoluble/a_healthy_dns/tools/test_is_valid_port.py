#!/usr/bin/env python3

import pytest

from indisoluble.a_healthy_dns.tools.is_valid_port import is_valid_port


def test_valid_ports():
    valid_ports = [
        1,  # Minimum valid port
        80,  # HTTP
        443,  # HTTPS
        8080,  # Common alternative HTTP port
        53,  # DNS
        22,  # SSH
        3306,  # MySQL
        65535,  # Maximum valid port
    ]

    for port in valid_ports:
        result, message = is_valid_port(port)
        assert result is True
        assert message == ""


@pytest.mark.parametrize(
    "invalid_port,expected_message",
    [
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
