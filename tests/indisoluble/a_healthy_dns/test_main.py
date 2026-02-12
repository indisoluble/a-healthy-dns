#!/usr/bin/env python3

import pytest

from typing import Dict, Any
from unittest.mock import ANY, patch, MagicMock

from indisoluble.a_healthy_dns import dns_server_config_factory as dscf
from indisoluble.a_healthy_dns.main import (
    _ARG_CONNECTION_TIMEOUT,
    _ARG_LOG_LEVEL,
    _ARG_MIN_TEST_INTERVAL,
    _ARG_PORT,
    _main,
)


@pytest.fixture
def default_args() -> Dict[str, Any]:
    return {
        _ARG_PORT: 53053,
        _ARG_LOG_LEVEL: "info",
        dscf.ARG_HOSTED_ZONE: "example.com",
        dscf.ARG_ZONE_RESOLUTIONS: '{"www": {"ips": ["192.168.1.1"], "health_port": 8080}}',
        _ARG_MIN_TEST_INTERVAL: 1,
        _ARG_CONNECTION_TIMEOUT: 2,
        dscf.ARG_NAME_SERVERS: '["ns1.example.com", "ns2.example.com"]',
        dscf.ARG_DNSSEC_PRIVATE_KEY_PATH: None,
        dscf.ARG_DNSSEC_ALGORITHM: "RSASHA256",
    }


@pytest.fixture
def mock_config():
    mock = MagicMock()
    mock.alias_zones = frozenset()
    return mock


@patch("indisoluble.a_healthy_dns.main.logging")
@patch("indisoluble.a_healthy_dns.main.make_config")
@patch("indisoluble.a_healthy_dns.main.DnsServerZoneUpdaterThreated")
@patch("indisoluble.a_healthy_dns.main.socketserver.UDPServer")
def test_main_success(
    mock_udp_server,
    mock_zone_updater,
    mock_make_config,
    mock_logging,
    default_args,
    mock_config,
):
    # Setup mocks
    mock_make_config.return_value = mock_config

    mock_zone_updater_instance = MagicMock()
    mock_zone_updater.return_value = mock_zone_updater_instance

    mock_server_instance = MagicMock()
    mock_udp_server.return_value.__enter__.return_value = mock_server_instance

    # Call function
    _main(default_args)

    # Assert
    mock_logging.basicConfig.assert_called_once()

    mock_make_config.assert_called_once()

    mock_zone_updater.assert_called_once_with(1, 2, mock_config)
    mock_zone_updater_instance.start.assert_called_once()

    mock_udp_server.assert_called_once_with(("", default_args[_ARG_PORT]), ANY)

    assert mock_server_instance.zone == mock_zone_updater_instance.zone
    assert mock_server_instance.alias_zones == mock_config.alias_zones
    mock_server_instance.serve_forever.assert_called_once()

    mock_zone_updater_instance.stop.assert_called_once()


@patch("indisoluble.a_healthy_dns.main.logging")
@patch("indisoluble.a_healthy_dns.main.make_config")
@patch("indisoluble.a_healthy_dns.main.DnsServerZoneUpdaterThreated")
@patch("indisoluble.a_healthy_dns.main.socketserver.UDPServer")
def test_main_with_failed_config(
    mock_udp_server,
    mock_zone_updater,
    mock_make_config,
    mock_logging,
    default_args,
    mock_config,
):
    # Setup mocks
    mock_make_config.return_value = None

    # Call function
    _main(default_args)

    # Assert
    mock_logging.basicConfig.assert_called_once()

    mock_make_config.assert_called_once()

    mock_zone_updater.assert_not_called()
    mock_udp_server.assert_not_called()
