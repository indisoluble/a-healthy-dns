#!/usr/bin/env python3

import datetime
import logging
import threading
import time

import dns.dnssec
import dns.name
import dns.rdataclass
import dns.rdataset
import dns.rdatatype
import dns.transaction
import dns.versioned

from typing import FrozenSet, Iterator, NamedTuple, Tuple

from .dns_server_config_factory import DnsServerConfig, ExtendedPrivateKey
from .healthy_a_record import HealthyARecord
from .tools.can_create_connection import can_create_connection
from .tools.uint32_current_time import uint32_current_time


class RRSigLifetime(NamedTuple):
    resign: int
    expiration: int


class RRSigKey(NamedTuple):
    dnskey: Tuple[dns.dnssec.PrivateKey, dns.dnssec.DNSKEY]
    dnskey_ttl: int
    inception: datetime
    expiration: datetime


class ExtendedRRSigKey(NamedTuple):
    key: RRSigKey
    resign: datetime


class RRSigAction(NamedTuple):
    resign: datetime
    iter: Iterator[ExtendedRRSigKey]


class ZonePrivateKey(NamedTuple):
    dnskey: Tuple[dns.dnssec.PrivateKey, dns.dnssec.DNSKEY]
    dnskey_ttl: int
    rrsig_resign_time: datetime.datetime
    rrsig_resign_timedelta: datetime.timedelta
    rrsig_expiration_timedelta: datetime.timedelta


_DELTA_PER_RECORD_MANAGEMENT = 1
_DELTA_PER_RECORD_SIGN = 2
_STOP_JOIN_EXTRA_TIMEOUT = 1.0


def _calculate_max_interval(
    min_interval: int,
    connection_timeout: int,
    a_records: FrozenSet[HealthyARecord],
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


def _calculate_a_ttl(max_interval: int) -> int:
    return max_interval * 2


def _calculate_ns_ttl(max_interval: int) -> int:
    return _calculate_a_ttl(max_interval) * 30


def _calculate_soa_ttl(max_interval: int) -> int:
    return _calculate_ns_ttl(max_interval)


def _calculate_dnskey_ttl(max_interval: int) -> int:
    return _calculate_a_ttl(max_interval) * 10


def _calculate_soa_refresh(max_interval: int) -> int:
    return _calculate_dnskey_ttl(max_interval)


def _calculate_soa_retry(max_interval: int) -> int:
    return _calculate_a_ttl(max_interval)


def _calculate_soa_expire(max_interval: int) -> int:
    return _calculate_soa_retry(max_interval) * 5


def _calculate_soa_min_ttl(max_interval: int) -> int:
    return _calculate_a_ttl(max_interval)


def _calculate_rrsig_lifetime(max_interval: int) -> RRSigLifetime:
    return RRSigLifetime(
        resign=_calculate_soa_refresh(max_interval),
        expiration=2 * _calculate_soa_refresh(max_interval)
        + _calculate_soa_expire(max_interval)
        + _calculate_soa_retry(max_interval),
    )


def _make_ns_record(
    max_interval: int, name_servers: FrozenSet[str]
) -> dns.rdataset.Rdataset:
    ttl = _calculate_ns_ttl(max_interval)
    rdataset = dns.rdataset.from_text(
        dns.rdataclass.IN, dns.rdatatype.NS, ttl, *name_servers
    )
    logging.debug(
        "Created NS record with ttl: %d, and name servers: %s", ttl, name_servers
    )

    return rdataset


def _iter_soa_serial() -> Iterator[int]:
    last_serial = 0

    while True:
        current_serial = uint32_current_time()
        if current_serial == last_serial:
            raise ValueError(
                f"Current serial {current_serial} is the same as last serial"
            )

        last_serial = current_serial

        yield current_serial


def _iter_soa_record(
    max_interval: int, origin_name: dns.name.Name, primary_ns: str
) -> Iterator[dns.rdataset.Rdataset]:
    ttl = _calculate_soa_ttl(max_interval)
    responsible = f"hostmaster.{origin_name}"
    serial = _iter_soa_serial()
    refresh = str(_calculate_soa_refresh(max_interval))
    retry = str(_calculate_soa_retry(max_interval))
    expire = str(_calculate_soa_expire(max_interval))
    min_ttl = str(_calculate_soa_min_ttl(max_interval))

    while True:
        admin_info = " ".join(
            [
                primary_ns,
                responsible,
                str(next(serial)),
                refresh,
                retry,
                expire,
                min_ttl,
            ]
        )
        rdataset = dns.rdataset.from_text(
            dns.rdataclass.IN, dns.rdatatype.SOA, ttl, admin_info
        )
        logging.debug(
            "Created SOA record with ttl: %d, and admin info: %s", ttl, admin_info
        )

        yield rdataset


def _iter_rrsig_key(
    max_interval: int, ext_private_key: ExtendedPrivateKey
) -> Iterator[ExtendedRRSigKey]:
    key = (ext_private_key.private_key, ext_private_key.dnskey)
    ttl = _calculate_dnskey_ttl(max_interval)
    lifetime = _calculate_rrsig_lifetime(max_interval)

    while True:
        inception = datetime.datetime.now(datetime.timezone.utc)
        expiration = inception + datetime.timedelta(seconds=lifetime.expiration)
        resign = expiration + datetime.timedelta(seconds=lifetime.resign)
        logging.debug(
            "Created RRSIG key with inception: %s, expiration: %s, resign: %s",
            inception,
            expiration,
            resign,
        )

        yield ExtendedRRSigKey(
            key=RRSigKey(
                dnskey=key, dnskey_ttl=ttl, inception=inception, expiration=expiration
            ),
            resign=resign,
        )


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
        self._connection_timeout = float(connection_timeout)

        self._zone = dns.versioned.Zone(config.origin_name)

        max_interval = _calculate_max_interval(
            min_interval,
            connection_timeout,
            config.a_records,
            config.ext_private_key is not None,
        )
        self._ns_rec = _make_ns_record(max_interval, config.name_servers)
        self._soa_rec = _iter_soa_record(
            max_interval, config.origin_name, config.name_servers[0]
        )
        self._rrsig_action = (
            RRSigAction(
                resign=datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc),
                iter=_iter_rrsig_key(max_interval, config.ext_private_key),
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
        if not self._rrsig_action:
            return

        ext_rrsig_key = next(self._rrsig_action.iter)
        logging.debug(
            "Signing zone with inception time %s...", ext_rrsig_key.key.inception
        )

        dns.dnssec.sign_zone(
            self._zone,
            txn=txn,
            keys=[ext_rrsig_key.key.dnskey],
            **ext_rrsig_key.key._asdict(),
        )
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

    def _refresh_a_record(self, a_record: HealthyARecord) -> HealthyARecord:
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
