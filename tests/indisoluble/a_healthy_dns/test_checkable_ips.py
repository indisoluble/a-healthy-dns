#!/usr/bin/env python3

import pytest

from indisoluble.a_healthy_dns.checkable_ips import CheckableIps


@pytest.mark.parametrize(
    "ip_list, port, expected_ips",
    [
        (["192.168.1.1", "10.0.0.1"], 8080, ["10.0.0.1", "192.168.1.1"]),
        (["192.168.001.001", "010.000.000.001"], 8080, ["10.0.0.1", "192.168.1.1"]),
        (["10.0.0.1", "192.168.1.1"], 8080, ["10.0.0.1", "192.168.1.1"]),
        (["172.16.0.1", "127.0.0.1"], 80, ["127.0.0.1", "172.16.0.1"]),
        (["001.002.003.004", "192.168.1.1"], 443, ["1.2.3.4", "192.168.1.1"]),
        (["192.168.1.1", "10.0.0.1"], 1234, ["10.0.0.1", "192.168.1.1"]),
        (["102.168.1.1", "19.0.0.1"], 2039, ["102.168.1.1", "19.0.0.1"]),
        (
            ["192.168.1.1", "10.0.0.1", "102.168.1.1", "19.0.0.1"],
            1234,
            ["10.0.0.1", "102.168.1.1", "19.0.0.1", "192.168.1.1"],
        ),
        (
            [
                "192.168.001.001",
                "010.000.000.001",
                "010.000.000.001",
                "192.168.001.001",
            ],
            8080,
            ["10.0.0.1", "192.168.1.1"],
        ),
        (
            ["192.168.001.001", "010.000.000.001", "10.0.0.1", "192.168.1.1"],
            8080,
            ["10.0.0.1", "192.168.1.1"],
        ),
    ],
)
def test_valid_initialization(ip_list, port, expected_ips):
    ips = CheckableIps(ip_list, port)
    assert isinstance(ips.ips, list)
    assert ips.ips == expected_ips
    assert ips.health_port == port


def test_empty_ip_list():
    with pytest.raises(ValueError) as exc_info:
        CheckableIps([], 8080)
    assert "IP list cannot be empty" in str(exc_info.value)


@pytest.mark.parametrize(
    "invalid_ips",
    [
        ["256.0.0.1"],  # octet > 255
        ["192.168.1.1", "192.168.1"],  # second IP has not enough octets
        ["192.168.1.256"],  # octet > 255
        ["192.168.1.a"],  # non-digit octet
        ["192.168.1.1.5"],  # too many octets
    ],
)
def test_invalid_ips(invalid_ips):
    with pytest.raises(ValueError) as exc_info:
        CheckableIps(invalid_ips, 8080)
    assert "Invalid IP address" in str(exc_info.value)


@pytest.mark.parametrize(
    "invalid_port",
    [
        0,  # below range
        65536,  # above range
        -1,  # negative
    ],
)
def test_invalid_port(invalid_port):
    with pytest.raises(ValueError) as exc_info:
        CheckableIps(["192.168.1.1"], invalid_port)
    assert "Invalid port" in str(exc_info.value)


def test_repr():
    ips = CheckableIps(["192.168.1.1", "10.0.0.1"], 8080)
    expected = "CheckableIps(ips=['10.0.0.1', '192.168.1.1'], health_port=8080)"
    assert repr(ips) == expected


def test_original_list_modification():
    original_ips = ["192.168.1.1", "10.0.0.1"]
    ips_instance = CheckableIps(original_ips, 8080)

    original_ips.append("172.16.0.1")
    original_ips[0] = "192.168.1.100"

    assert ips_instance.ips == ["10.0.0.1", "192.168.1.1"]
    assert original_ips == ["192.168.1.100", "10.0.0.1", "172.16.0.1"]
