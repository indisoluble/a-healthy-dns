#!/usr/bin/env python3

"""Network connectivity testing utilities.

Provides functions to test TCP connectivity to IP addresses and ports
for health checking purposes.
"""

import logging
import socket


def can_create_connection(ip: str, port: int, timeout: float) -> bool:
    """Test TCP connectivity to an IP address and port with timeout."""
    try:
        with socket.create_connection((ip, port), timeout):
            logging.debug("TCP connectivity test to '%s:%d' successful", ip, port)
            return True
    except Exception as ex:
        logging.debug("TCP connectivity test to '%s:%d' failed: %s", ip, port, ex)
        return False
