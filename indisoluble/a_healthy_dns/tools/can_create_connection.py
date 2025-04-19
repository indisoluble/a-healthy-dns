#!/usr/bin/env python3

import logging
import socket


def can_create_connection(ip: str, port: int, timeout: int) -> bool:
    try:
        with socket.create_connection((ip, port), timeout):
            logging.debug("TCP connectivity test to '%s:%d' successful", ip, port)
            return True
    except Exception as ex:
        logging.debug("TCP connectivity test to '%s:%d' failed: %s", ip, port, ex)
        return False
