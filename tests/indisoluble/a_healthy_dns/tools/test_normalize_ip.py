#!/usr/bin/env python3

import pytest

from indisoluble.a_healthy_dns.tools.normalize_ip import normalize_ip


def test_normalize_ip_no_leading_zeros():
    ip_addresses = [
        "192.168.1.1",
        "10.0.0.1",
        "172.16.0.1",
        "127.0.0.1",
        "0.0.0.0",
        "255.255.255.255",
    ]

    for ip in ip_addresses:
        assert normalize_ip(ip) == ip


def test_normalize_ip_with_leading_zeros():
    test_cases = [
        ("192.168.001.001", "192.168.1.1"),
        ("010.020.030.040", "10.20.30.40"),
        ("001.002.003.004", "1.2.3.4"),
        ("192.0168.1.1", "192.168.1.1"),
    ]

    for input_ip, expected_output in test_cases:
        assert normalize_ip(input_ip) == expected_output


def test_normalize_ip_with_all_zeros():
    test_cases = [
        ("000.168.1.1", "0.168.1.1"),
        ("192.000.1.1", "192.0.1.1"),
        ("192.168.000.1", "192.168.0.1"),
        ("192.168.1.000", "192.168.1.0"),
        ("000.000.000.000", "0.0.0.0"),
    ]

    for input_ip, expected_output in test_cases:
        assert normalize_ip(input_ip) == expected_output
