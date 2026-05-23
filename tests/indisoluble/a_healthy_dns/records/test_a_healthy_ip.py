#!/usr/bin/env python3

import pytest

from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp

_IP = "192.168.1.1"
_NON_NORMALIZED_IP = "192.168.001.001"
_HEALTH_PORT = 8080
_OTHER_HEALTH_PORT = 9090


def _make_ip(ip=_IP, health_port=_HEALTH_PORT, is_healthy=True):
    return AHealthyIp(ip, health_port, is_healthy)


def _assert_ip_state(healthy_ip, *, ip=_IP, health_port=_HEALTH_PORT, is_healthy=True):
    assert healthy_ip.ip == ip
    assert healthy_ip.health_port == health_port
    assert healthy_ip.is_healthy is is_healthy


class TestAHealthyIpInitialization:
    @pytest.mark.parametrize(
        "health_port,is_healthy",
        [
            (_HEALTH_PORT, True),
            (None, False),
        ],
        ids=["health-checked-ip", "static-ip-without-health-port"],
    )
    def test_initialization_stores_valid_port_and_health_state(
        self, health_port, is_healthy
    ):
        healthy_ip = _make_ip(health_port=health_port, is_healthy=is_healthy)

        _assert_ip_state(
            healthy_ip,
            health_port=health_port,
            is_healthy=is_healthy,
        )

    @pytest.mark.parametrize(
        "non_normalized_ip,expected_ip",
        [
            ("192.168.001.001", "192.168.1.1"),
            ("192.000.1.1", "192.0.1.1"),
        ],
    )
    def test_normalizes_ip_address(self, non_normalized_ip, expected_ip):
        healthy_ip = _make_ip(ip=non_normalized_ip)

        assert healthy_ip.ip == expected_ip


class TestAHealthyIpValidation:
    @pytest.mark.parametrize(
        "invalid_ip",
        [
            None,
            123,
            1.5,
            [],
            {},
            "256.0.0.1",
            "192.168.1",
            "192.168.1.256",
            "192.168.1.a",
            "192.168.1.1.5",
        ],
    )
    def test_rejects_invalid_ip(self, invalid_ip):
        with pytest.raises(ValueError):
            _make_ip(ip=invalid_ip)

    @pytest.mark.parametrize(
        "invalid_port",
        [
            "8080",
            1.5,
            [],
            {},
            0,
            65536,
            -1,
        ],
    )
    def test_rejects_invalid_health_port(self, invalid_port):
        with pytest.raises(ValueError):
            _make_ip(health_port=invalid_port)


class TestAHealthyIpEqualityAndHashing:
    def test_equal_when_all_value_fields_match_after_normalization(self):
        healthy_ip = _make_ip()

        assert healthy_ip == _make_ip()
        assert healthy_ip == _make_ip(ip=_NON_NORMALIZED_IP)

    @pytest.mark.parametrize(
        "other",
        [
            AHealthyIp(_IP, _HEALTH_PORT, False),
            AHealthyIp("192.168.1.2", _HEALTH_PORT, True),
            AHealthyIp(_IP, _OTHER_HEALTH_PORT, True),
            "not an AHealthyIp object",
        ],
    )
    def test_not_equal_when_value_field_differs(self, other):
        assert _make_ip() != other

    def test_none_health_port_participates_in_equality(self):
        assert _make_ip(health_port=None) == _make_ip(health_port=None)
        assert _make_ip(health_port=None) != _make_ip()

    def test_hash_matches_equality_contract(self):
        healthy_ip = _make_ip()
        equivalent_ip = _make_ip()
        equivalent_normalized_ip = _make_ip(ip="192.168.01.001")
        unhealthy_ip = _make_ip(is_healthy=False)
        different_ip = _make_ip(ip="192.168.1.2")
        different_port = _make_ip(health_port=_OTHER_HEALTH_PORT)

        ip_dict = {healthy_ip: "server1"}

        assert ip_dict[equivalent_ip] == "server1"
        assert ip_dict[equivalent_normalized_ip] == "server1"
        assert unhealthy_ip not in ip_dict
        assert different_ip not in ip_dict
        assert different_port not in ip_dict

        assert {healthy_ip, equivalent_ip, equivalent_normalized_ip} == {healthy_ip}
        assert {
            healthy_ip,
            equivalent_ip,
            equivalent_normalized_ip,
            unhealthy_ip,
            different_ip,
        } == {healthy_ip, unhealthy_ip, different_ip}


class TestAHealthyIpStatusUpdates:
    def test_updated_status_returns_same_instance_when_status_is_unchanged(self):
        healthy_ip = _make_ip(is_healthy=True)

        assert healthy_ip.updated_status(True) is healthy_ip

    def test_updated_status_returns_new_instance_when_status_changes(self):
        healthy_ip = _make_ip(is_healthy=True)

        updated_ip = healthy_ip.updated_status(False)

        assert updated_ip is not healthy_ip
        _assert_ip_state(updated_ip, is_healthy=False)
        assert healthy_ip.is_healthy is True

    def test_updated_status_preserves_none_health_port(self):
        healthy_ip = _make_ip(health_port=None, is_healthy=True)

        updated_ip = healthy_ip.updated_status(False)

        assert updated_ip is not healthy_ip
        _assert_ip_state(updated_ip, health_port=None, is_healthy=False)

    def test_updated_status_maintains_equality_for_matching_values(self):
        first_ip = _make_ip(is_healthy=True)
        second_ip = _make_ip(is_healthy=True)

        first_unhealthy_ip = first_ip.updated_status(False)
        second_unhealthy_ip = second_ip.updated_status(False)

        assert first_unhealthy_ip != first_ip
        assert second_unhealthy_ip != second_ip
        assert first_unhealthy_ip == second_unhealthy_ip


class TestAHealthyIpRepresentation:
    @pytest.mark.parametrize(
        "healthy_ip,expected_repr",
        [
            (
                AHealthyIp(_IP, _HEALTH_PORT, True),
                "AHealthyIp(ip='192.168.1.1', health_port=8080, is_healthy=True)",
            ),
            (
                AHealthyIp(_IP, _HEALTH_PORT, False),
                "AHealthyIp(ip='192.168.1.1', health_port=8080, is_healthy=False)",
            ),
            (
                AHealthyIp(_NON_NORMALIZED_IP, _HEALTH_PORT, False),
                "AHealthyIp(ip='192.168.1.1', health_port=8080, is_healthy=False)",
            ),
            (
                AHealthyIp(_IP, None, True),
                "AHealthyIp(ip='192.168.1.1', health_port=None, is_healthy=True)",
            ),
        ],
        ids=[
            "healthy-with-port",
            "unhealthy-with-port",
            "normalized-ip",
            "without-port",
        ],
    )
    def test_repr_shows_normalized_value_fields(self, healthy_ip, expected_repr):
        assert repr(healthy_ip) == expected_repr
