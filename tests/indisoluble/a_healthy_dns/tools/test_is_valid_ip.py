#!/usr/bin/env python3

import pytest

from indisoluble.a_healthy_dns.tools.is_valid_ip import is_valid_ip


def test_valid_ip_addresses():
    valid_ips = [
        "192.168.1.1",
        "10.0.0.1",
        "172.16.0.1",
        "127.0.0.1",
        "0.0.0.0",
        "255.255.255.255",
    ]

    for ip in valid_ips:
        result, message = is_valid_ip(ip)
        assert result is True
        assert message == ""


@pytest.mark.parametrize(
    "invalid_ip,expected_message",
    [
        ("256.0.0.1", "Each octet must be a number between 0 and 255"),
        ("192.168.1", "IP address must have 4 octets"),
        ("192.168.1.256", "Each octet must be a number between 0 and 255"),
        ("192.168.1.a", "Each octet must be a number between 0 and 255"),
        ("192.168.1.1.5", "IP address must have 4 octets"),
        ("", "IP address must have 4 octets"),
        ("192.168..1", "Each octet must be a number between 0 and 255"),
        (".168.1.1", "Each octet must be a number between 0 and 255"),
        ("192.168.1.", "Each octet must be a number between 0 and 255"),
    ],
)
def test_invalid_ip_addresses(invalid_ip, expected_message):
    result, message = is_valid_ip(invalid_ip)
    assert result is False
    assert message == expected_message


def test_ip_with_whitespace():
    result, message = is_valid_ip(" 192.168.1.1")
    assert result is False
    assert "Each octet must be a number between 0 and 255" == message

    result, message = is_valid_ip("192.168.1.1 ")
    assert result is False
    assert "Each octet must be a number between 0 and 255" == message

    result, message = is_valid_ip("192.168. 1.1")
    assert result is False
    assert "Each octet must be a number between 0 and 255" == message


def test_ip_with_leading_zeros():
    result, message = is_valid_ip("0192.0168.001.001")
    assert result is True
    assert message == ""
