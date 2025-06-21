#!/usr/bin/env python3

import datetime
import logging
import threading
import time

import dns.dnssec
import dns.name
import dns.transaction
import dns.versioned

from typing import FrozenSet, Iterator, NamedTuple

from indisoluble.a_healthy_dns.dns_server_config_factory import DnsServerConfig
from indisoluble.a_healthy_dns.records.a_healthy_record import AHealthyRecord
from indisoluble.a_healthy_dns.records.a_record import make_a_record
from indisoluble.a_healthy_dns.records.dnssec import ExtendedRRSigKey, iter_rrsig_key
from indisoluble.a_healthy_dns.records.ns_record import make_ns_record
from indisoluble.a_healthy_dns.records.soa_record import iter_soa_record
from indisoluble.a_healthy_dns.tools.can_create_connection import can_create_connection


class RRSigAction(NamedTuple):
    resign: datetime.datetime
    iter: Iterator[ExtendedRRSigKey]


_DELTA_PER_RECORD_MANAGEMENT = 1
_DELTA_PER_RECORD_SIGN = 2
_STOP_JOIN_EXTRA_TIMEOUT = 1.0


def _calculate_max_interval(
    min_interval: int,
    connection_timeout: int,
    a_records: FrozenSet[AHealthyRecord],
    do_sign: bool,
) -> int:
    delta_per_record = _DELTA_PER_RECORD_MANAGEMENT + (
        _DELTA_PER_RECORD_SIGN if do_sign else 0
    )
    max_loop_duration = sum(
        len(record.healthy_ips) * connection_timeout + delta_per_record
        for record in a_records
    )

    return max_loop_duration if max_loop_duration > min_interval else min_interval


class DnsServerZoneUpdater:
    @property
    def zone(self) -> dns.versioned.Zone:
        return self._zone

    def __init__(
        self, min_interval: int, connection_timeout: int, config: DnsServerConfig
    ):
        if min_interval <= 0:
            raise ValueError("Minimum interval must be positive")
        if connection_timeout <= 0:
            raise ValueError("Connection timeout must be positive")

        self._min_interval = min_interval
        self._max_interval = _calculate_max_interval(
            min_interval,
            connection_timeout,
            config.a_records,
            config.ext_private_key is not None,
        )
        self._connection_timeout = float(connection_timeout)

        self._zone = dns.versioned.Zone(config.origin_name)

        self._ns_rec = make_ns_record(self._max_interval, config.name_servers)
        self._soa_rec = iter_soa_record(
            self._max_interval, config.origin_name, next(iter(config.name_servers))
        )
        self._rrsig_action = (
            RRSigAction(
                resign=datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc),
                iter=iter_rrsig_key(self._max_interval, config.ext_private_key),
            )
            if config.ext_private_key
            else None
        )
        self._a_recs = list(config.a_records)

        self._stop_event = threading.Event()
        self._updater_thread = None

    def _clear_zone_with_transaction(self, txn: dns.transaction.Transaction):
        logging.debug("Clearing zone...")

        for name in list(txn.iterate_names()):
            logging.debug("Deleting node %s...", name)
            txn.delete(name)

        logging.debug("Zone cleared")

    def _add_a_record_to_zone_with_transaction(
        self, a_record: AHealthyRecord, txn: dns.transaction.Transaction
    ):
        dataset = make_a_record(self._max_interval, a_record)
        if dataset:
            txn.add(a_record.subdomain, dataset)
            logging.debug("Added A record %s to zone", a_record.subdomain)
        else:
            logging.debug("A record %s skipped", a_record.subdomain)

    def _add_records_to_zone_with_transaction(self, txn: dns.transaction.Transaction):
        logging.debug("Adding records to zone...")

        txn.add(dns.name.empty, self._ns_rec)
        logging.debug("Added NS record to zone")

        txn.add(dns.name.empty, next(self._soa_rec))
        logging.debug("Added SOA record to zone")

        for a_record in self._a_recs:
            self._add_a_record_to_zone_with_transaction(a_record, txn)

        logging.debug("Records added to zone")

    def _sign_zone_with_transaction(self, txn: dns.transaction.Transaction):
        if not self._rrsig_action:
            return

        ext_rrsig_key = next(self._rrsig_action.iter)
        logging.debug(
            "Signing zone with inception time %s...", ext_rrsig_key.key.inception
        )

        dns.dnssec.sign_zone(self._zone, txn=txn, **ext_rrsig_key.key._asdict())
        logging.debug(
            "Zone signed with expiration time %s. Next signing time %s",
            ext_rrsig_key.key.expiration,
            ext_rrsig_key.resign,
        )

        self._rrsig_action = RRSigAction(
            resign=ext_rrsig_key.resign, iter=self._rrsig_action.iter
        )

    def _is_zone_sign_near_to_expire(self) -> bool:
        return (
            datetime.datetime.now(datetime.timezone.utc) >= self._rrsig_action.resign
            if self._rrsig_action
            else False
        )

    def _initialize_zone(self):
        with self._zone.writer() as txn:
            self._clear_zone_with_transaction(txn)
            self._add_records_to_zone_with_transaction(txn)
        # Sign requires the soa record to be present
        # in the zone. It does not work using the current
        # transaction, which seems to be a bug in dnspython
        with self._zone.writer() as txn:
            self._sign_zone_with_transaction(txn)

    def _refresh_a_record(self, a_record: AHealthyRecord) -> AHealthyRecord:
        updated_ips = []
        for health_ip in a_record.healthy_ips:
            if self._stop_event.is_set():
                logging.debug("Abort record check. Return A record as it is")
                return a_record

            updated_ips.append(
                health_ip.updated_status(
                    can_create_connection(
                        health_ip.ip, health_ip.health_port, self._connection_timeout
                    )
                )
            )

        return a_record.updated_ips(updated_ips)

    def _refresh_a_recs(self) -> bool:
        checked_a_recs = []

        are_there_any_changes = False
        for a_record in self._a_recs:
            if self._stop_event.is_set():
                logging.debug("Zone updater stopped")
                return False

            checked_record = self._refresh_a_record(a_record)
            checked_a_recs.append(checked_record)

            are_there_any_changes = (
                are_there_any_changes
                or checked_record.healthy_ips != a_record.healthy_ips
            )

        self._a_recs = checked_a_recs

        return are_there_any_changes

    def _update_zone(self):
        do_update_zone = False

        if self._refresh_a_recs():
            logging.info("A records changed")
            do_update_zone = True

        if self._is_zone_sign_near_to_expire():
            logging.info("Zone signing is near to expire")
            do_update_zone = True

        if do_update_zone:
            logging.info("Updating zone...")
            self._initialize_zone()

    def _update_zone_loop(self):
        while not self._stop_event.is_set():
            start_time = time.time()

            self._update_zone()

            elapsed = time.time() - start_time
            sleep_time = max(0, self._min_interval - elapsed)
            if sleep_time > 0 and not self._stop_event.wait(sleep_time):
                logging.debug("Completed sleep between connectivity tests")

    def start(self):
        if self._updater_thread and self._updater_thread.is_alive():
            logging.warning("Zone Updater is already running")
            return

        logging.info("Initializing zone...")
        self._initialize_zone()

        logging.info("Starting Zone Updater...")
        self._stop_event.clear()
        self._updater_thread = threading.Thread(
            target=self._update_zone_loop, name="ZoneUpdaterThread", daemon=True
        )
        self._updater_thread.start()

    def stop(self) -> bool:
        if not self._updater_thread or not self._updater_thread.is_alive():
            logging.warning("Zone Updater is not running")
            return True

        logging.info("Stopping Zone Updater...")
        self._stop_event.set()
        self._updater_thread.join(
            timeout=self._connection_timeout + _STOP_JOIN_EXTRA_TIMEOUT
        )
        if self._updater_thread.is_alive():
            logging.warning("Zone Updater thread did not terminate gracefully")
            return False

        return True
