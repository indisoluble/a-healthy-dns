#!/usr/bin/env python3

import socket

import pytest

from unittest.mock import MagicMock, patch

from indisoluble.a_healthy_dns.tools.can_create_connection import can_create_connection

_IP = "192.168.1.1"
_PORT = 80
_TIMEOUT = 5


def _assert_create_connection_called(mock_create_connection):
    mock_create_connection.assert_called_once_with((_IP, _PORT), _TIMEOUT)


class TestCanCreateConnection:
    @patch(
        "indisoluble.a_healthy_dns.tools.can_create_connection.socket.create_connection"
    )
    def test_returns_true_when_connection_succeeds(self, mock_create_connection):
        mock_connection = MagicMock()
        mock_create_connection.return_value = mock_connection

        result = can_create_connection(_IP, _PORT, _TIMEOUT)

        assert result is True
        _assert_create_connection_called(mock_create_connection)
        mock_connection.__enter__.assert_called_once_with()
        mock_connection.__exit__.assert_called_once()

    @pytest.mark.parametrize(
        "exception",
        [
            socket.timeout("Connection timed out"),
            OSError("Connection refused"),
        ],
        ids=["timeout", "os-error"],
    )
    @patch(
        "indisoluble.a_healthy_dns.tools.can_create_connection.socket.create_connection"
    )
    def test_returns_false_when_connection_fails(
        self, mock_create_connection, exception
    ):
        mock_create_connection.side_effect = exception

        result = can_create_connection(_IP, _PORT, _TIMEOUT)

        assert result is False
        _assert_create_connection_called(mock_create_connection)
