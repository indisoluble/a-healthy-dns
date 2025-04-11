#!/usr/bin/env python3

import pytest
import socket
import threading
import time

from unittest.mock import MagicMock, patch

from indisoluble.a_healthy_dns.checkable_ip import CheckableIp
from indisoluble.a_healthy_dns.dns_server_config import DNSServerConfig
from indisoluble.a_healthy_dns.tcp_connectivity_tester import TcpConnectivityTester


@pytest.fixture
def mock_dns_config():
    config = MagicMock(spec=DNSServerConfig)
    config.checkable_ips = [
        CheckableIp("192.168.1.1", 8080),
        CheckableIp("192.168.1.2", 8081),
    ]
    return config


@pytest.mark.parametrize(
    "check_interval,connection_timeout,error_message",
    [
        (0, 5, "Check interval must be positive"),
        (-1, 5, "Check interval must be positive"),
        (10, 0, "Connection timeout must be positive"),
        (10, -1, "Connection timeout must be positive"),
    ],
)
def test_invalid_initialization(
    mock_dns_config, check_interval, connection_timeout, error_message
):
    with pytest.raises(ValueError) as exc_info:
        TcpConnectivityTester(mock_dns_config, check_interval, connection_timeout)
    assert error_message in str(exc_info.value)


def test_test_connectivity_success(mock_dns_config):
    tester = TcpConnectivityTester(mock_dns_config, 10, 5)
    checkable_ip = CheckableIp("192.168.1.1", 8080)

    with patch("socket.create_connection") as mock_create_connection:
        mock_create_connection.return_value = MagicMock()

        assert tester._test_connectivity(checkable_ip)
        mock_create_connection.assert_called_once_with(
            (checkable_ip.ip, checkable_ip.health_port), timeout=5
        )


def test_test_connectivity_failure(mock_dns_config):
    tester = TcpConnectivityTester(mock_dns_config, 10, 5)
    checkable_ip = CheckableIp("192.168.1.1", 8080)

    with patch("socket.create_connection") as mock_create_connection:
        mock_create_connection.side_effect = socket.timeout("Connection timed out")

        assert not tester._test_connectivity(checkable_ip)
        mock_create_connection.assert_called_once_with(
            (checkable_ip.ip, checkable_ip.health_port), timeout=5
        )


def test_connectivity_test_loop(mock_dns_config):
    tester = TcpConnectivityTester(mock_dns_config, 10, 1)

    with patch.object(tester._stop_event, "is_set") as mock_stop_is_set, patch.object(
        tester, "_test_connectivity"
    ) as mock_test_connectivity, patch.object(
        tester._stop_event, "wait", return_value=True
    ):
        mock_stop_is_set.side_effect = [False, False, False, True]
        mock_test_connectivity.side_effect = [True, False]

        tester._connectivity_test_loop()

        assert mock_test_connectivity.call_count == 2
        mock_dns_config.set_ip_status.assert_any_call(
            mock_dns_config.checkable_ips[0], True
        )
        mock_dns_config.set_ip_status.assert_any_call(
            mock_dns_config.checkable_ips[1], False
        )


def test_start_stop(mock_dns_config):
    tester = TcpConnectivityTester(mock_dns_config, 10, 1)

    with patch("threading.Thread") as mock_thread_class:
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        mock_thread_class.return_value = mock_thread

        # Test start
        tester.start()
        assert not tester._stop_event.is_set()
        assert tester._tester_thread == mock_thread
        mock_thread_class.assert_called_with(
            target=tester._connectivity_test_loop,
            name="TcpConnectivityTester",
            daemon=True,
        )

        # Test start when already running
        with patch("logging.warning") as mock_warning:
            tester.start()
            mock_warning.assert_called_once_with(
                "TCP connectivity tester is already running"
            )

        # Test stop
        tester.stop()
        assert tester._stop_event.is_set()
        mock_thread.join.assert_called_once_with(timeout=2.0)

        # Test stop when not running
        mock_thread.is_alive.return_value = False
        with patch("logging.warning") as mock_warning:
            assert tester.stop()
            mock_warning.assert_called_once_with(
                "TCP connectivity tester is not running"
            )


def test_start_stop_real_thread(mock_dns_config):
    tester = TcpConnectivityTester(mock_dns_config, 1, 1)

    # Mock _test_connectivity to avoid actual network calls
    with patch.object(tester, "_test_connectivity", return_value=True):
        tester.start()
        assert tester._tester_thread.is_alive()

        time.sleep(0.1)

        assert tester.stop()
        assert not tester._tester_thread.is_alive()


def test_thread_not_terminating_gracefully(mock_dns_config):
    tester = TcpConnectivityTester(mock_dns_config, 1, 1)

    tester._tester_thread = threading.Thread(target=lambda: None)
    with patch.object(threading.Thread, "is_alive", return_value=True), patch.object(
        threading.Thread, "join"
    ), patch("logging.warning") as mock_warning:
        assert not tester.stop()
        mock_warning.assert_called_once_with(
            "Tester thread did not terminate gracefully"
        )
