#!/usr/bin/env python3

import socket
from unittest.mock import patch, MagicMock

from indisoluble.a_healthy_dns.tools.can_create_connection import can_create_connection


@patch("socket.create_connection")
def test_successful_connection(mock_create_connection):
    mock_create_connection.return_value = MagicMock()

    result = can_create_connection("192.168.1.1", 80, 5)

    assert result is True
    mock_create_connection.assert_called_once_with(("192.168.1.1", 80), 5)


@patch("socket.create_connection")
def test_connection_failure(mock_create_connection):
    mock_create_connection.side_effect = socket.timeout("Connection timed out")

    result = can_create_connection("192.168.1.1", 80, 5)

    assert result is False
    mock_create_connection.assert_called_once_with(("192.168.1.1", 80), 5)
