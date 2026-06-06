#!/usr/bin/env python3

import pytest

from typing import Any
from unittest.mock import MagicMock, patch

from indisoluble.a_healthy_dns import dns_server_config_factory as dscf
from indisoluble.a_healthy_dns.dns_server_udp_handler import DnsServerUdpHandler
from indisoluble.a_healthy_dns.main import (
    _ARG_CONNECTION_TIMEOUT,
    _ARG_LOG_LEVEL,
    _ARG_MIN_TEST_INTERVAL,
    _ARG_PORT,
    _make_arg_parser,
    _main,
)


@pytest.fixture
def default_args() -> dict[str, Any]:
    return {
        _ARG_PORT: 53053,
        _ARG_LOG_LEVEL: "info",
        dscf.ARG_HOSTED_ZONE: "example.com",
        dscf.ARG_ZONE_RESOLUTIONS: '{"www": {"ips": ["192.168.1.1"], "health_port": 8080}}',
        _ARG_MIN_TEST_INTERVAL: 1,
        _ARG_CONNECTION_TIMEOUT: 2,
        dscf.ARG_NAME_SERVERS: '["ns1.dns.example.net", "ns2.dns.example.net"]',
        dscf.ARG_DNSSEC_PRIVATE_KEY_PATH: None,
        dscf.ARG_DNSSEC_ALGORITHM: "RSASHA256",
    }


@pytest.fixture
def mock_config():
    mock = MagicMock()
    mock.zone_origins = MagicMock()
    return mock


def _make_zone_updater(mock_zone_updater):
    zone_updater = MagicMock()
    mock_zone_updater.return_value = zone_updater
    return zone_updater


def _make_udp_server(mock_udp_server):
    server = MagicMock()
    mock_udp_server.return_value.__enter__.return_value = server
    return server


class TestMainServerLifecycle:
    @patch("indisoluble.a_healthy_dns.main.logging")
    @patch("indisoluble.a_healthy_dns.main.make_config")
    @patch("indisoluble.a_healthy_dns.main.DnsServerZoneUpdaterThreaded")
    @patch("indisoluble.a_healthy_dns.main.socketserver.UDPServer")
    def test_returns_zero_and_serves_udp_when_config_is_valid(
        self,
        mock_udp_server,
        mock_zone_updater,
        mock_make_config,
        mock_logging,
        default_args,
        mock_config,
    ):
        mock_make_config.return_value = mock_config
        zone_updater = _make_zone_updater(mock_zone_updater)
        server = _make_udp_server(mock_udp_server)

        exit_code = _main(default_args)

        assert exit_code == 0
        mock_logging.basicConfig.assert_called_once()
        mock_make_config.assert_called_once_with(default_args)

        mock_zone_updater.assert_called_once_with(1, 2, mock_config)
        zone_updater.start.assert_called_once()

        mock_udp_server.assert_called_once_with(
            ("", default_args[_ARG_PORT]), DnsServerUdpHandler
        )
        assert server.zone == zone_updater.zone
        assert server.zone_origins == mock_config.zone_origins
        server.serve_forever.assert_called_once()

        zone_updater.stop.assert_called_once()

    @patch("indisoluble.a_healthy_dns.main.logging")
    @patch("indisoluble.a_healthy_dns.main.make_config")
    @patch("indisoluble.a_healthy_dns.main.DnsServerZoneUpdaterThreaded")
    @patch("indisoluble.a_healthy_dns.main.socketserver.UDPServer")
    def test_stops_zone_updater_when_udp_server_setup_fails(
        self,
        mock_udp_server,
        mock_zone_updater,
        mock_make_config,
        mock_logging,
        default_args,
        mock_config,
    ):
        mock_make_config.return_value = mock_config
        zone_updater = _make_zone_updater(mock_zone_updater)
        mock_udp_server.side_effect = OSError("port already in use")

        with pytest.raises(OSError, match="port already in use"):
            _main(default_args)

        mock_logging.basicConfig.assert_called_once()
        mock_make_config.assert_called_once_with(default_args)
        zone_updater.start.assert_called_once()
        zone_updater.stop.assert_called_once()


class TestMainConfigurationFailure:
    @patch("indisoluble.a_healthy_dns.main.logging")
    @patch("indisoluble.a_healthy_dns.main.make_config")
    @patch("indisoluble.a_healthy_dns.main.DnsServerZoneUpdaterThreaded")
    @patch("indisoluble.a_healthy_dns.main.socketserver.UDPServer")
    def test_returns_one_and_skips_server_when_config_is_invalid(
        self,
        mock_udp_server,
        mock_zone_updater,
        mock_make_config,
        mock_logging,
        default_args,
    ):
        mock_make_config.return_value = None

        exit_code = _main(default_args)

        assert exit_code == 1
        mock_logging.basicConfig.assert_called_once()
        mock_make_config.assert_called_once_with(default_args)
        mock_zone_updater.assert_not_called()
        mock_udp_server.assert_not_called()


class TestMainArgumentParser:
    @pytest.mark.parametrize(
        "log_level",
        [
            "debug",
            "info",
            "warning",
            "error",
            "critical",
        ],
    )
    def test_accepts_documented_log_levels(self, log_level):
        parser = _make_arg_parser()

        args = parser.parse_args(
            [
                "--hosted-zone",
                "example.com",
                "--zone-resolutions",
                '{"www":["192.168.1.1"]}',
                "--ns",
                '["ns1.dns.example.net"]',
                "--log-level",
                log_level,
            ]
        )

        assert getattr(args, _ARG_LOG_LEVEL) == log_level

    @pytest.mark.parametrize("log_level", ["warn", "fatal", "INFO"])
    def test_rejects_undocumented_log_level_aliases(self, log_level):
        parser = _make_arg_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(
                [
                    "--hosted-zone",
                    "example.com",
                    "--zone-resolutions",
                    '{"www":["192.168.1.1"]}',
                    "--ns",
                    '["ns1.dns.example.net"]',
                    "--log-level",
                    log_level,
                ]
            )
