#!/usr/bin/env python3

import pytest

from indisoluble.a_healthy_dns.tools.normalize_ip import normalize_ip


class TestNormalizeIp:
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
    def test_leaves_ip_without_leading_zeros_unchanged(self, ip):
        assert normalize_ip(ip) == ip

    @pytest.mark.parametrize(
        "input_ip,expected_output",
        [
            ("192.168.001.001", "192.168.1.1"),
            ("010.020.030.040", "10.20.30.40"),
            ("001.002.003.004", "1.2.3.4"),
            ("192.0168.1.1", "192.168.1.1"),
            ("000.168.1.1", "0.168.1.1"),
            ("192.000.1.1", "192.0.1.1"),
            ("192.168.000.1", "192.168.0.1"),
            ("192.168.1.000", "192.168.1.0"),
            ("000.000.000.000", "0.0.0.0"),
        ],
    )
    def test_removes_leading_zeros_from_octets(self, input_ip, expected_output):
        assert normalize_ip(input_ip) == expected_output
