#!/usr/bin/env python3

import pytest

from typing import Dict, Any
from unittest.mock import ANY, patch, MagicMock

from indisoluble.a_healthy_dns import dns_server_zone_factory as dszf
from indisoluble.a_healthy_dns.dns_server_zone_updater import (
    ARG_CONNECTION_TIMEOUT,
    ARG_TEST_INTERVAL,
)
from indisoluble.a_healthy_dns.main import (
    _ARG_DNSSEC_PRIVATE_KEY_PATH,
    _ARG_LOG_LEVEL,
    _ARG_PORT,
    _main,
    _normalize_config,
)


@pytest.fixture
def default_args() -> Dict[str, Any]:
    return {
        dszf.ARG_HOSTED_ZONE: "example.com",
        dszf.ARG_NAME_SERVERS: '["ns1.example.com", "ns2.example.com"]',
        dszf.ARG_ZONE_RESOLUTIONS: '{"www": {"ip_list": ["192.168.1.1"], "health_port": 8080}}',
        _ARG_PORT: 53053,
        dszf.ARG_TTL_A: 60,
        dszf.ARG_TTL_NS: 86400,
        dszf.ARG_TTL_SOA: None,
        dszf.ARG_SOA_REFRESH: None,
        dszf.ARG_SOA_RETRY: None,
        dszf.ARG_SOA_EXPIRE: None,
        dszf.ARG_SOA_MIN_TTL: 600,
        _ARG_DNSSEC_PRIVATE_KEY_PATH: None,
        dszf.ARG_DNSSEC_ALGORITHM: "RSASHA256",
        dszf.ARG_DNSSEC_TTL_DNSKEY: 86400,
        dszf.ARG_DNSSEC_LIFETIME: 1209600,
        ARG_TEST_INTERVAL: None,
        ARG_CONNECTION_TIMEOUT: 2,
        _ARG_LOG_LEVEL: "info",
    }


@pytest.fixture
def mock_zone():
    mock = MagicMock()
    mock.zone = MagicMock()
    return mock


@patch("indisoluble.a_healthy_dns.main.logging")
@patch("indisoluble.a_healthy_dns.main.dszf.make_zone")
@patch("indisoluble.a_healthy_dns.main.DnsServerZoneUpdater")
@patch("indisoluble.a_healthy_dns.main.socketserver.UDPServer")
def test_main_success(
    mock_udp_server,
    mock_zone_updater,
    mock_make_zone,
    mock_logging,
    default_args,
    mock_zone,
):
    # Setup mocks
    mock_make_zone.return_value = mock_zone

    mock_zone_updater_instance = MagicMock()
    mock_zone_updater.return_value = mock_zone_updater_instance

    mock_server_instance = MagicMock()
    mock_udp_server.return_value.__enter__.return_value = mock_server_instance

    # Call function
    _main(default_args)

    # Assert
    mock_logging.basicConfig.assert_called_once()

    mock_make_zone.assert_called_once()

    mock_zone_updater.assert_called_once_with(mock_zone, ANY)
    mock_zone_updater_instance.start.assert_called_once()

    mock_udp_server.assert_called_once_with(("", default_args[_ARG_PORT]), ANY)

    assert mock_server_instance.zone == mock_zone.zone
    mock_server_instance.serve_forever.assert_called_once()

    mock_zone_updater_instance.stop.assert_called_once()


@patch("builtins.open")
@patch("indisoluble.a_healthy_dns.main.logging")
@patch("indisoluble.a_healthy_dns.main.dszf.make_zone")
@patch("indisoluble.a_healthy_dns.main.DnsServerZoneUpdater")
@patch("indisoluble.a_healthy_dns.main.socketserver.UDPServer")
def test_main_invalid_private_key(
    mock_udp_server,
    mock_zone_updater,
    mock_make_zone,
    mock_logging,
    mock_open,
    default_args,
):
    # Setup mocks
    default_args[_ARG_DNSSEC_PRIVATE_KEY_PATH] = "/path/to/key.pem"
    mock_open.side_effect = Exception("Failed to open private key file")

    # Call function
    _main(default_args)

    # Assert
    mock_logging.basicConfig.assert_called_once()
    mock_open.assert_called_once_with("/path/to/key.pem", "rb")
    mock_make_zone.assert_not_called()
    mock_zone_updater.assert_not_called()
    mock_udp_server.assert_not_called()


@patch("indisoluble.a_healthy_dns.main.logging")
@patch("indisoluble.a_healthy_dns.main.dszf.make_zone")
@patch("indisoluble.a_healthy_dns.main.DnsServerZoneUpdater")
@patch("indisoluble.a_healthy_dns.main.socketserver.UDPServer")
def test_main_invalid_zone(
    mock_udp_server, mock_zone_updater, mock_make_zone, mock_logging, default_args
):
    # Setup mocks
    mock_make_zone.return_value = None

    # Call function
    _main(default_args)

    # Assert
    mock_logging.basicConfig.assert_called_once()
    mock_make_zone.assert_called_once()
    mock_zone_updater.assert_not_called()
    mock_udp_server.assert_not_called()


def test_normalize_config(default_args):
    # Assert original values
    assert default_args[dszf.ARG_TTL_SOA] is None
    assert default_args[dszf.ARG_SOA_REFRESH] is None
    assert default_args[dszf.ARG_SOA_RETRY] is None
    assert default_args[dszf.ARG_SOA_EXPIRE] is None
    assert default_args[_ARG_DNSSEC_PRIVATE_KEY_PATH] is None
    assert dszf.ARG_DNSSEC_PRIVATE_KEY_PEM not in default_args
    assert default_args[ARG_TEST_INTERVAL] is None

    # Call function
    config = _normalize_config(default_args)

    # Assert defaults were set correctly
    assert config[dszf.ARG_TTL_SOA] == default_args[dszf.ARG_TTL_A]
    assert config[dszf.ARG_SOA_REFRESH] == default_args[dszf.ARG_TTL_A]
    assert config[dszf.ARG_SOA_RETRY] == default_args[dszf.ARG_TTL_A] // 4
    assert config[dszf.ARG_SOA_EXPIRE] == default_args[dszf.ARG_TTL_A] * 30
    assert _ARG_DNSSEC_PRIVATE_KEY_PATH not in config
    assert config[dszf.ARG_DNSSEC_PRIVATE_KEY_PEM] is None
    assert config[ARG_TEST_INTERVAL] == default_args[dszf.ARG_TTL_A] // 2


@patch("builtins.open")
def test_normalize_with_provided_config_values(mock_open, default_args):
    # Mock file
    private_key_content = (
        "-----BEGIN PRIVATE KEY-----\nMockPrivateKey\n-----END PRIVATE KEY-----"
    )

    mock_file = MagicMock()
    mock_file.read.return_value = private_key_content

    mock_open.return_value.__enter__.return_value = mock_file

    # Set values that would normally be defaulted
    default_args[dszf.ARG_TTL_SOA] = 121
    default_args[dszf.ARG_SOA_REFRESH] = 241
    default_args[dszf.ARG_SOA_RETRY] = 61
    default_args[dszf.ARG_SOA_EXPIRE] = 3601
    default_args[ARG_TEST_INTERVAL] = 31

    default_args[_ARG_DNSSEC_PRIVATE_KEY_PATH] = "/path/to/private/key.pem"
    assert dszf.ARG_DNSSEC_PRIVATE_KEY_PEM not in default_args

    # Call function
    config = _normalize_config(default_args)

    # Assert values were not overridden
    assert config[dszf.ARG_TTL_SOA] == 121
    assert config[dszf.ARG_SOA_REFRESH] == 241
    assert config[dszf.ARG_SOA_RETRY] == 61
    assert config[dszf.ARG_SOA_EXPIRE] == 3601
    assert config[ARG_TEST_INTERVAL] == 31

    # Assert the private key was read and set correctly
    mock_open.assert_called_once_with("/path/to/private/key.pem", "rb")
    mock_file.read.assert_called_once()
    assert _ARG_DNSSEC_PRIVATE_KEY_PATH not in config
    assert config[dszf.ARG_DNSSEC_PRIVATE_KEY_PEM] == private_key_content
