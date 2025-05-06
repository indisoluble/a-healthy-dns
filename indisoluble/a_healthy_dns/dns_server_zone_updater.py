#!/usr/bin/env python3

import datetime
import logging
import threading
import time

import dns.dnssec
import dns.name
import dns.rdataclass
import dns.rdataset
import dns.transaction

from typing import Any, Dict, NamedTuple, Tuple

from .dns_server_zone_factory import ExtendedZone
from .healthy_a_record import HealthyARecord
from .tools.can_create_connection import can_create_connection


class ZonePrivateKey(NamedTuple):
    dnskey: Tuple[dns.dnssec.PrivateKey, dns.dnssec.DNSKEY]
    dnskey_ttl: int
    rrsig_resign_time: datetime.datetime
    rrsig_resign_timedelta: datetime.timedelta
    rrsig_expiration_timedelta: datetime.timedelta


_RESIGN_EXTRA_DELTA = 5.0
_STOP_JOIN_EXTRA_TIMEOUT = 1.0
ARG_CONNECTION_TIMEOUT = "connection_timeout"
ARG_TEST_INTERVAL = "test_interval"


class DnsServerZoneUpdater:
    def __init__(self, ext_zone: ExtendedZone, args: Dict[str, Any]):
        check_interval_seconds = args[ARG_TEST_INTERVAL]
        if check_interval_seconds <= 0:
            raise ValueError("Check interval must be positive")

        self._check_interval = float(check_interval_seconds)

        connection_timeout = args[ARG_CONNECTION_TIMEOUT]
        if connection_timeout <= 0:
            raise ValueError("Connection timeout must be positive")

        self._connection_timeout = float(connection_timeout)

        self._zone = ext_zone.zone
        self._ns_rec = ext_zone.ns_rec
        self._soa_rec = ext_zone.soa_rec
        self._a_recs = ext_zone.a_recs.copy()

        self._zone_key = None
        if ext_zone.ext_priv_key:
            dnskey = (ext_zone.ext_priv_key.private_key, ext_zone.ext_priv_key.dnskey)
            rrsig_resign_timedelta = datetime.timedelta(
                seconds=self._check_interval
                + len(self._a_recs) * self._connection_timeout
                + _RESIGN_EXTRA_DELTA
            )
            rrsig_expiration_timedelta = datetime.timedelta(
                seconds=ext_zone.ext_priv_key.rrsig_lifetime
            )
            self._zone_key = ZonePrivateKey(
                dnskey,
                ext_zone.ext_priv_key.dnskey_ttl,
                datetime.datetime.now(datetime.timezone.utc),
                rrsig_resign_timedelta,
                rrsig_expiration_timedelta,
            )

        self._stop_event = threading.Event()
        self._updater_thread = None

    def _clear_zone_with_transaction(self, txn: dns.transaction.Transaction):
        logging.debug("Clearing zone...")

        for name in list(txn.iterate_names()):
            logging.debug("Deleting node %s...", name)
            txn.delete(name)

        logging.debug("Zone cleared")

    def _add_a_record_to_zone_with_transaction(
        self, a_record: HealthyARecord, txn: dns.transaction.Transaction
    ):
        ips = [ip.ip for ip in a_record.healthy_ips if ip.is_healthy]
        if ips:
            txn.add(
                a_record.subdomain,
                dns.rdataset.from_text(
                    dns.rdataclass.IN, dns.rdatatype.A, a_record.ttl_a, *ips
                ),
            )
            logging.debug("Added A record %s with IPs: %s", a_record.subdomain, ips)
        else:
            logging.debug("No healthy IPs for A record %s. Skip", a_record.subdomain)

    def _add_records_to_zone_with_transaction(self, txn: dns.transaction.Transaction):
        logging.debug("Adding records to zone...")

        txn.add(dns.name.empty, self._ns_rec)
        logging.debug("Added NS record to zone")

        txn.add(dns.name.empty, self._soa_rec)
        soa_serial = int(time.time())
        txn.update_serial(soa_serial, relative=False)
        logging.debug(
            "Added SOA record to zone with serial %d (epoch time)", soa_serial
        )

        for a_record in self._a_recs:
            self._add_a_record_to_zone_with_transaction(a_record, txn)

        logging.debug("Records added to zone")

    def _sign_zone_with_transaction(self, txn: dns.transaction.Transaction):
        if not self._zone_key:
            return

        inception = datetime.datetime.now(datetime.timezone.utc)
        logging.debug("Signing zone with inception time %s...", inception)

        rrsig_expiration = inception + self._zone_key.rrsig_expiration_timedelta
        dns.dnssec.sign_zone(
            self._zone,
            txn=txn,
            keys=[self._zone_key.dnskey],
            dnskey_ttl=self._zone_key.dnskey_ttl,
            inception=inception,
            expiration=rrsig_expiration,
        )
        logging.debug("Zone signed with expiration time %s", rrsig_expiration)

        self._zone_key = ZonePrivateKey(
            self._zone_key.dnskey,
            self._zone_key.dnskey_ttl,
            rrsig_expiration - self._zone_key.rrsig_resign_timedelta,
            self._zone_key.rrsig_resign_timedelta,
            self._zone_key.rrsig_expiration_timedelta,
        )
        logging.debug("Next signing time %s", self._zone_key.rrsig_resign_time)

    def _is_zone_sign_near_to_expire(self) -> bool:
        if not self._zone_key:
            return False

        return (
            datetime.datetime.now(datetime.timezone.utc)
            >= self._zone_key.rrsig_resign_time
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

    def _refresh_a_record(self, a_record: HealthyARecord) -> HealthyARecord:
        updated_ips = set()
        for health_ip in a_record.healthy_ips:
            if self._stop_event.is_set():
                logging.debug("Abort record check. Return A record as it is")
                return a_record

            updated_ips.add(
                health_ip.updated_status(
                    can_create_connection(
                        health_ip.ip, health_ip.health_port, self._connection_timeout
                    )
                )
            )

        return a_record.updated_ips(frozenset(updated_ips))

    def _refresh_a_recs(self) -> bool:
        checked_a_recs = set()

        are_there_any_changes = False
        for a_record in self._a_recs:
            if self._stop_event.is_set():
                logging.debug("Zone updater stopped")
                return False

            checked_record = self._refresh_a_record(a_record)
            checked_a_recs.add(checked_record)

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
            sleep_time = max(0, self._check_interval - elapsed)
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
