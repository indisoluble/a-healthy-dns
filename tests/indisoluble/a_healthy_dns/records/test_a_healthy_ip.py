#!/usr/bin/env python3

import pytest

from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp


def test_valid_initialization():
    ip = AHealthyIp("192.168.1.1", 8080, True)
    assert ip.ip == "192.168.1.1"
    assert ip.health_port == 8080
    assert ip.is_healthy is True


@pytest.mark.parametrize(
    "non_normalized_ip, expected_ip",
    [("192.168.001.001", "192.168.1.1"), ("192.000.1.1", "192.0.1.1")],
)
def test_ip_normalization(non_normalized_ip, expected_ip):
    ip = AHealthyIp(non_normalized_ip, 8080, True)
    assert ip.ip == expected_ip


@pytest.mark.parametrize(
    "invalid_ip",
    [
        None,
        123,
        1.5,
        [],
        {},
        "256.0.0.1",  # octet > 255
        "192.168.1",  # not enough octets
        "192.168.1.256",  # octet > 255
        "192.168.1.a",  # non-digit octet
        "192.168.1.1.5",  # too many octets
    ],
)
def test_invalid_ip(invalid_ip):
    with pytest.raises(ValueError):
        AHealthyIp(invalid_ip, 8080, True)


@pytest.mark.parametrize(
    "invalid_port",
    [
        "8080",
        None,
        1.5,
        [],
        {},
        0,  # below range
        65536,  # above range
        -1,  # negative
    ],
)
def test_invalid_port(invalid_port):
    with pytest.raises(ValueError):
        AHealthyIp("192.168.1.1", invalid_port, True)


def test_equality():
    ip1 = AHealthyIp("192.168.1.1", 8080, True)

    ip2 = AHealthyIp("192.168.1.1", 8080, True)
    assert ip1 == ip2

    ip3 = AHealthyIp("192.168.001.01", 8080, True)
    assert ip1 == ip3

    ip4 = AHealthyIp("192.168.1.1", 8080, False)
    assert ip1 != ip4

    ip5 = AHealthyIp("192.168.1.2", 8080, True)
    assert ip1 != ip5

    ip6 = AHealthyIp("192.168.1.1", 9090, True)
    assert ip1 != ip6

    assert ip1 != "not a AHealthyIp object"


def test_hash():
    ip1 = AHealthyIp("192.168.1.1", 8080, True)
    ip2 = AHealthyIp("192.168.1.1", 8080, True)
    ip3 = AHealthyIp("192.168.01.001", 8080, True)
    ip4 = AHealthyIp("192.168.1.1", 8080, False)
    ip5 = AHealthyIp("192.168.1.2", 8080, True)
    ip6 = AHealthyIp("192.168.1.1", 8080, True)
    ip7 = AHealthyIp("192.168.1.1", 9090, True)

    ip_dict = {ip1: "server1"}

    assert ip_dict[ip1] == "server1"
    assert ip_dict[ip2] == "server1"
    assert ip_dict[ip3] == "server1"

    with pytest.raises(KeyError):
        _ = ip_dict[ip4]
        _ = ip_dict[ip5]
        _ = ip_dict[ip6]
        _ = ip_dict[ip7]

    assert {ip1, ip2, ip3} == {ip1}
    assert {ip1, ip5, ip2, ip4, ip3} == {ip1, ip4, ip5}


def test_updated_status():
    ip1 = AHealthyIp("192.168.1.1", 8080, True)

    # Test when status doesn't change
    ip2 = ip1.updated_status(True)
    # Should be the same instance
    assert ip2 is ip1

    # Test when status changes
    ip3 = ip1.updated_status(False)
    assert ip3 is not ip1
    assert ip3.ip == ip1.ip
    assert ip3.health_port == ip1.health_port
    assert ip3.is_healthy is False
    assert ip1.is_healthy is True


def test_updated_status_maintains_equality():
    ip1 = AHealthyIp("192.168.1.1", 8080, True)
    ip2 = AHealthyIp("192.168.1.1", 8080, True)

    assert ip1.updated_status(True) is ip1
    assert ip2.updated_status(True) is ip2

    ip1_unhealthy = ip1.updated_status(False)
    ip2_unhealthy = ip2.updated_status(False)

    assert ip1_unhealthy != ip1
    assert ip2_unhealthy != ip2
    assert ip1_unhealthy == ip2_unhealthy


def test_repr():
    ip1 = AHealthyIp("192.168.1.1", 8080, True)
    ip2 = AHealthyIp("192.168.1.1", 8080, False)
    ip3 = AHealthyIp("192.168.001.001", 8080, False)

    expected1 = "AHealthyIp(ip='192.168.1.1', health_port=8080, is_healthy=True)"
    expected2 = "AHealthyIp(ip='192.168.1.1', health_port=8080, is_healthy=False)"

    assert repr(ip1) == expected1
    assert repr(ip2) == expected2
    assert repr(ip3) == expected2
