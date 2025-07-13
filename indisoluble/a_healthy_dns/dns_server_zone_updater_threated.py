#!/usr/bin/env python3

"""Threaded DNS zone updater with background health checking.

Provides a threaded wrapper around DnsServerZoneUpdater that continuously
performs health checks and zone updates in the background.
"""

import logging
import threading
import time

import dns.versioned

from indisoluble.a_healthy_dns.dns_server_config_factory import DnsServerConfig
from indisoluble.a_healthy_dns.dns_server_zone_updater import (
    DELTA_PER_RECORD_MANAGEMENT,
    DnsServerZoneUpdater,
)


class DnsServerZoneUpdaterThreated:
    """Threaded DNS zone updater that runs health checks in background."""

    @property
    def zone(self) -> dns.versioned.Zone:
        """Get the current DNS zone from the underlying updater."""
        return self._updater.zone

    def __init__(
        self, min_interval: int, connection_timeout: int, config: DnsServerConfig
    ):
        """Initialize threaded zone updater with timing and configuration."""
        try:
            self._updater = DnsServerZoneUpdater(
                min_interval, connection_timeout, config
            )
        except Exception as ex:
            raise ValueError(f"Failed to initialize updater: {ex}") from ex

        self._min_interval = float(min_interval)
        self._connection_timeout = float(connection_timeout)

        self._stop_event = threading.Event()
        self._updater_thread = None

    def _update_zone_loop(self):
        while not self._stop_event.is_set():
            start_time = time.time()

            self._updater.update(should_abort=lambda: self._stop_event.is_set())

            elapsed = time.time() - start_time
            sleep_time = max(0.0, self._min_interval - elapsed)
            if sleep_time > 0.0 and not self._stop_event.wait(sleep_time):
                logging.debug("Completed sleep between connectivity tests")

    def start(self):
        """Start the background zone updater thread."""
        if self._updater_thread and self._updater_thread.is_alive():
            logging.warning("Zone Updater is already running")
            return

        logging.info("Initializing zone...")
        self._updater.update(check_ips=False)

        logging.info("Starting Zone Updater...")
        self._stop_event.clear()
        self._updater_thread = threading.Thread(
            target=self._update_zone_loop, name="ZoneUpdaterThread", daemon=True
        )
        self._updater_thread.start()

    def stop(self) -> bool:
        """Stop the background zone updater thread and wait for completion."""
        if not self._updater_thread or not self._updater_thread.is_alive():
            logging.warning("Zone Updater is not running")
            return True

        logging.info("Stopping Zone Updater...")
        self._stop_event.set()
        self._updater_thread.join(
            timeout=self._connection_timeout + DELTA_PER_RECORD_MANAGEMENT
        )
        if self._updater_thread.is_alive():
            logging.warning("Zone Updater thread did not terminate gracefully")
            return False

        return True
