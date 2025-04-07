#!/usr/bin/env python3

import pytest

from indisoluble.a_healthy_dns.checkable_ip import CheckableIp


def test_valid_initialization():
    ip = CheckableIp("192.168.1.1", 8080)
    assert ip.ip == "192.168.1.1"
    assert ip.health_port == 8080


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
        CheckableIp(invalid_ip, 8080)
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
        CheckableIp("192.168.1.1", invalid_port)
    assert "Invalid port" in str(exc_info.value)


def test_equality():
    ip1 = CheckableIp("192.168.1.1", 8080)
    ip2 = CheckableIp("192.168.1.1", 8080)
    ip3 = CheckableIp("192.168.1.2", 8080)
    ip4 = CheckableIp("192.168.1.1", 9090)

    assert ip1 == ip2
    assert ip1 != ip3
    assert ip1 != ip4
    assert ip1 != "not a CheckableIp object"


def test_hash():
    ip1 = CheckableIp("192.168.1.1", 8080)
    ip2 = CheckableIp("192.168.1.1", 8080)
    ip3 = CheckableIp("192.168.1.2", 8080)

    ip_dict = {ip1: "server1", ip3: "server2"}

    assert ip_dict[ip1] == "server1"
    assert ip_dict[ip2] == "server1"  # ip2 has same hash as ip1
    assert ip_dict[ip3] == "server2"


def test_repr():
    ip = CheckableIp("192.168.1.1", 8080)
    expected = "CheckableIp(ip='192.168.1.1', health_port=8080)"
    assert repr(ip) == expected
