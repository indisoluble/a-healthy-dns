#!/usr/bin/env python3

import pytest

from indisoluble.a_healthy_dns.tools.is_valid_ip import is_valid_ip


def _assert_valid_ip(ip):
    result, message = is_valid_ip(ip)

    assert result is True
    assert message == ""


def _assert_invalid_ip(ip, expected_message):
    result, message = is_valid_ip(ip)

    assert result is False
    assert message == expected_message


class TestValidIpAddresses:
    @pytest.mark.parametrize(
        "valid_ip",
        [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "127.0.0.1",
            "0.0.0.0",
            "255.255.255.255",
        ],
    )
    def test_accepts_ipv4_address(self, valid_ip):
        _assert_valid_ip(valid_ip)

    def test_accepts_leading_zeros(self):
        _assert_valid_ip("0192.0168.001.001")


class TestInvalidIpAddresses:
    @pytest.mark.parametrize(
        "invalid_ip",
        [
            None,
            123,
            1.5,
            [],
            {},
        ],
    )
    def test_rejects_non_string_values(self, invalid_ip):
        _assert_invalid_ip(invalid_ip, "It must be a string")

    @pytest.mark.parametrize(
        "invalid_ip",
        [
            "192.168.1",
            "192.168.1.1.5",
            "",
        ],
    )
    def test_rejects_wrong_octet_count(self, invalid_ip):
        _assert_invalid_ip(invalid_ip, "IP address must have 4 octets")

    @pytest.mark.parametrize(
        "invalid_ip",
        [
            "256.0.0.1",
            "192.168.1.256",
            "192.168.1.a",
            "192.168..1",
            ".168.1.1",
            "192.168.1.",
        ],
    )
    def test_rejects_invalid_octets(self, invalid_ip):
        _assert_invalid_ip(invalid_ip, "Each octet must be a number between 0 and 255")

    @pytest.mark.parametrize(
        "invalid_ip",
        [
            " 192.168.1.1",
            "192.168.1.1 ",
            "192.168. 1.1",
        ],
    )
    def test_rejects_whitespace(self, invalid_ip):
        _assert_invalid_ip(invalid_ip, "Each octet must be a number between 0 and 255")
