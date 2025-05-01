#!/usr/bin/env python3

import logging
import threading
import time

import dns.rdataclass
import dns.rdataset
import dns.transaction

from typing import Any, Dict

from .dns_server_zone_factory import ExtendedZone
from .healthy_a_record import HealthyARecord
from .tools.can_create_connection import can_create_connection


_STOP_JOIN_EXTRA_TIMEOUT = 1
ARG_CONNECTION_TIMEOUT = "connection_timeout"
ARG_TEST_INTERVAL = "test_interval"


class DnsServerZoneUpdater:
    def __init__(self, ext_zone: ExtendedZone, args: Dict[str, Any]):
        check_interval_seconds = args[ARG_TEST_INTERVAL]
        if check_interval_seconds <= 0:
            raise ValueError("Check interval must be positive")

        connection_timeout = args[ARG_CONNECTION_TIMEOUT]
        if connection_timeout <= 0:
            raise ValueError("Connection timeout must be positive")

        self._zone = ext_zone.zone
        self._a_records = ext_zone.a_records.copy()
        self._check_interval = check_interval_seconds
        self._connection_timeout = connection_timeout

        self._stop_event = threading.Event()
        self._updater_thread = None

    def _update_a_record_in_zone(
        self, a_record: HealthyARecord, txn: dns.transaction.Transaction
    ) -> HealthyARecord:
        updated_ips = set()
        for health_ip in a_record.healthy_ips:
            if self._stop_event.is_set():
                logging.debug("Abort record update. Return A record as it is")
                return a_record

            updated_ips.add(
                health_ip.updated_status(
                    can_create_connection(
                        health_ip.ip, health_ip.health_port, self._connection_timeout
                    )
                )
            )

        if updated_ips == a_record.healthy_ips:
            return a_record

        logging.debug(f"Updating A record {a_record.subdomain} with IPs: {updated_ips}")
        updated_a_record = a_record.updated_ips(frozenset(updated_ips))

        ips = [ip.ip for ip in updated_a_record.healthy_ips if ip.is_healthy]
        if ips:
            txn.replace(
                updated_a_record.subdomain,
                dns.rdataset.from_text(
                    dns.rdataclass.IN, dns.rdatatype.A, updated_a_record.ttl_a, *ips
                ),
            )
        else:
            txn.delete(updated_a_record.subdomain)

        return updated_a_record

    def _update_zone(self):
        with self._zone.writer() as txn:
            updated_a_records = set()
            for a_record in self._a_records:
                if self._stop_event.is_set():
                    logging.debug("Zone updater stopped")
                    break

                updated_a_records.add(self._update_a_record_in_zone(a_record, txn))

            self._a_records = updated_a_records | self._a_records

            if txn.changed():
                txn.update_serial()

    def _update_zone_loop(self):
        while not self._stop_event.is_set():
            start_time = time.time()

            self._update_zone()

            elapsed = time.time() - start_time
            sleep_time = max(0, self._check_interval - elapsed)
            if sleep_time > 0 and not self._stop_event.wait(sleep_time):
                logging.debug("Completed sleep between connectivity tests")

    def start(self):
        if self._updater_thread and self._updater_thread.is_alive():
            logging.warning("Zone Updater is already running")
            return

        logging.info("Starting Zone Updater")
        self._stop_event.clear()
        self._updater_thread = threading.Thread(
            target=self._update_zone_loop, name="ZoneUpdaterThread", daemon=True
        )
        self._updater_thread.start()

    def stop(self) -> bool:
        if not self._updater_thread or not self._updater_thread.is_alive():
            logging.warning("Zone Updater is not running")
            return True

        logging.info("Stopping Zone Updater")
        self._stop_event.set()
        self._updater_thread.join(
            timeout=self._connection_timeout + _STOP_JOIN_EXTRA_TIMEOUT
        )
        if self._updater_thread.is_alive():
            logging.warning("Zone Updater thread did not terminate gracefully")
            return False

        return True
