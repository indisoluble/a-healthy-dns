#!/usr/bin/env python3

import pytest

from indisoluble.a_healthy_dns.tools.normalize_ip import normalize_ip


@pytest.mark.parametrize(
    "ip",
    [
        "192.168.1.1",
        "10.0.0.1",
        "172.16.0.1",
        "127.0.0.1",
        "0.0.0.0",
        "255.255.255.255",
    ],
)
def test_normalize_ip_no_leading_zeros(ip):
    assert normalize_ip(ip) == ip


@pytest.mark.parametrize(
    "input_ip,expected_output",
    [
        ("192.168.001.001", "192.168.1.1"),
        ("010.020.030.040", "10.20.30.40"),
        ("001.002.003.004", "1.2.3.4"),
        ("192.0168.1.1", "192.168.1.1"),
    ],
)
def test_normalize_ip_with_leading_zeros(input_ip, expected_output):
    assert normalize_ip(input_ip) == expected_output


@pytest.mark.parametrize(
    "input_ip,expected_output",
    [
        ("000.168.1.1", "0.168.1.1"),
        ("192.000.1.1", "192.0.1.1"),
        ("192.168.000.1", "192.168.0.1"),
        ("192.168.1.000", "192.168.1.0"),
        ("000.000.000.000", "0.0.0.0"),
    ],
)
def test_normalize_ip_with_all_zeros(input_ip, expected_output):
    assert normalize_ip(input_ip) == expected_output
