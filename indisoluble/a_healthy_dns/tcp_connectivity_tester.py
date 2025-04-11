#!/usr/bin/env python3

import logging
import socket
import threading
import time

from .checkable_ip import CheckableIp
from .dns_server_config import DNSServerConfig


class TcpConnectivityTester:
    def __init__(
        self,
        config: DNSServerConfig,
        check_interval_seconds: int,
        connection_timeout: int,
    ):
        if check_interval_seconds <= 0:
            raise ValueError("Check interval must be positive")

        if connection_timeout <= 0:
            raise ValueError("Connection timeout must be positive")

        self._config = config
        self._check_interval = check_interval_seconds
        self._connection_timeout = connection_timeout

        self._stop_event = threading.Event()
        self._tester_thread = None

    def _test_connectivity(self, checkable_ip: CheckableIp) -> bool:
        try:
            with socket.create_connection(
                (checkable_ip.ip, checkable_ip.health_port),
                timeout=self._connection_timeout,
            ):
                logging.debug("TCP connectivity test to %s successful", checkable_ip)
                return True
        except Exception as e:
            logging.debug("TCP connectivity test to %s failed: %s", checkable_ip, e)
            return False

    def _connectivity_test_loop(self):
        while not self._stop_event.is_set():
            start_time = time.time()

            for checkable_ip in self._config.checkable_ips:
                if not self._stop_event.is_set():
                    self._config.set_ip_status(
                        checkable_ip, self._test_connectivity(checkable_ip)
                    )

            elapsed = time.time() - start_time
            sleep_time = max(0, self._check_interval - elapsed)

            if sleep_time > 0 and not self._stop_event.wait(sleep_time):
                logging.debug("Completed sleep between connectivity tests")

    def start(self):
        if self._tester_thread is not None and self._tester_thread.is_alive():
            logging.warning("TCP connectivity tester is already running")
            return

        logging.info("Starting TCP connectivity tester")
        self._stop_event.clear()
        self._tester_thread = threading.Thread(
            target=self._connectivity_test_loop,
            name="TcpConnectivityTester",
            daemon=True,
        )
        self._tester_thread.start()

    def stop(self) -> bool:
        if self._tester_thread is None or not self._tester_thread.is_alive():
            logging.warning("TCP connectivity tester is not running")
            return True

        logging.info("Stopping TCP connectivity tester")
        self._stop_event.set()
        self._tester_thread.join(timeout=self._connection_timeout + 1)

        if self._tester_thread.is_alive():
            logging.warning("Tester thread did not terminate gracefully")
            return False

        return True
