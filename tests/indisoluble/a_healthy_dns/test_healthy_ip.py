#!/usr/bin/env python3

import pytest

from indisoluble.a_healthy_dns.healthy_ip import HealthyIp


def test_valid_initialization():
    ip = HealthyIp("192.168.1.1", 8080, True)
    assert ip.ip == "192.168.1.1"
    assert ip.health_port == 8080
    assert ip.is_healthy is True


@pytest.mark.parametrize(
    "non_normalized_ip, expected_ip",
    [("192.168.001.001", "192.168.1.1"), ("192.000.1.1", "192.0.1.1")],
)
def test_ip_normalization(non_normalized_ip, expected_ip):
    ip = HealthyIp(non_normalized_ip, 8080, True)
    assert ip.ip == expected_ip


@pytest.mark.parametrize(
    "invalid_ip",
    [
        "256.0.0.1",  # octet > 255
        "192.168.1",  # not enough octets
        "192.168.1.256",  # octet > 255
        "192.168.1.a",  # non-digit octet
        "192.168.1.1.5",  # too many octets
    ],
)
def test_invalid_ip(invalid_ip):
    with pytest.raises(ValueError) as exc_info:
        HealthyIp(invalid_ip, 8080, True)
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
        HealthyIp("192.168.1.1", invalid_port, True)
    assert "Invalid port" in str(exc_info.value)


def test_equality():
    ip1 = HealthyIp("192.168.1.1", 8080, True)

    ip2 = HealthyIp("192.168.1.1", 8080, True)
    assert ip1 == ip2

    ip3 = HealthyIp("192.168.001.01", 8080, True)
    assert ip1 == ip3

    ip4 = HealthyIp("192.168.1.1", 8080, False)
    assert ip1 != ip4

    ip5 = HealthyIp("192.168.1.2", 8080, True)
    assert ip1 != ip5

    ip6 = HealthyIp("192.168.1.1", 9090, True)
    assert ip1 != ip6

    assert ip1 != "not a HealthyIp object"


def test_hash():
    ip1 = HealthyIp("192.168.1.1", 8080, True)
    ip2 = HealthyIp("192.168.1.1", 8080, True)
    ip3 = HealthyIp("192.168.01.001", 8080, True)
    ip4 = HealthyIp("192.168.1.1", 8080, False)
    ip5 = HealthyIp("192.168.1.2", 8080, True)
    ip6 = HealthyIp("192.168.1.1", 9090, True)

    ip_dict = {ip1: "server1"}

    assert ip_dict[ip1] == "server1"
    assert ip_dict[ip2] == "server1"
    assert ip_dict[ip3] == "server1"

    with pytest.raises(KeyError):
        _ = ip_dict[ip4]
        _ = ip_dict[ip5]
        _ = ip_dict[ip6]

    assert {ip1, ip2, ip3} == {ip1}
    assert {ip1, ip5, ip2, ip4, ip3} == {ip1, ip4, ip5}


def test_repr():
    ip1 = HealthyIp("192.168.1.1", 8080, True)
    ip2 = HealthyIp("192.168.1.1", 8080, False)
    ip3 = HealthyIp("192.168.001.001", 8080, False)

    expected1 = "HealthyIp(ip='192.168.1.1', health_port=8080, is_healthy=True)"
    expected2 = "HealthyIp(ip='192.168.1.1', health_port=8080, is_healthy=False)"

    assert repr(ip1) == expected1
    assert repr(ip2) == expected2
    assert repr(ip3) == expected2
