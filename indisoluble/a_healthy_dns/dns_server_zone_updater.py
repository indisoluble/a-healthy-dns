#!/usr/bin/env python3

"""DNS zone updater with health checking capabilities.

Manages DNS zone updates based on health checks of configured IP addresses,
handles DNSSEC signing, and maintains zone freshness with configurable intervals.
"""

import datetime
import logging

import dns.dnssec
import dns.name
import dns.transaction
import dns.versioned

from enum import auto, Enum
from functools import partial
from typing import Callable, FrozenSet, Iterator, NamedTuple, Optional

from indisoluble.a_healthy_dns.dns_server_config_factory import DnsServerConfig
from indisoluble.a_healthy_dns.records.a_healthy_record import AHealthyRecord
from indisoluble.a_healthy_dns.records.a_record import make_a_record
from indisoluble.a_healthy_dns.records.dnssec import ExtendedRRSigKey, iter_rrsig_key
from indisoluble.a_healthy_dns.records.ns_record import make_ns_record
from indisoluble.a_healthy_dns.records.soa_record import iter_soa_record
from indisoluble.a_healthy_dns.tools.can_create_connection import can_create_connection


ShouldAbortOp = Callable[[], bool]


class RRSigAction(NamedTuple):
    """DNSSEC signature action containing resign time and key iterator."""

    resign: datetime.datetime
    iter: Iterator[ExtendedRRSigKey]


class RefreshARecordsResult(Enum):
    """Result states for A record refresh operations."""

    NO_CHANGES = auto()
    CHANGES = auto()
    ABORTED = auto()


_DELTA_PER_RECORD_SIGN = 2
DELTA_PER_RECORD_MANAGEMENT = 1


def _calculate_max_interval(
    min_interval: int,
    connection_timeout: int,
    a_records: FrozenSet[AHealthyRecord],
    do_sign: bool,
) -> int:
    delta_per_record = DELTA_PER_RECORD_MANAGEMENT + (
        _DELTA_PER_RECORD_SIGN if do_sign else 0
    )
    max_loop_duration = sum(
        len(record.healthy_ips) * connection_timeout + delta_per_record
        for record in a_records
    )

    return max_loop_duration if max_loop_duration > min_interval else min_interval


class DnsServerZoneUpdater:
    """DNS zone updater that performs health checks and updates zones accordingly."""

    @property
    def zone(self) -> dns.versioned.Zone:
        """Get the current DNS zone."""
        return self._zone

    def __init__(
        self, min_interval: int, connection_timeout: int, config: DnsServerConfig
    ):
        """Initialize zone updater with configuration and timing parameters."""
        if min_interval <= 0:
            raise ValueError("Minimum interval must be positive")
        if connection_timeout <= 0:
            raise ValueError("Connection timeout must be positive")

        max_interval = _calculate_max_interval(
            min_interval,
            connection_timeout,
            config.a_records,
            config.ext_private_key is not None,
        )

        self._ns_rec = make_ns_record(max_interval, config.name_servers)
        self._soa_rec = iter_soa_record(
            max_interval, config.zone_origins.primary, next(iter(config.name_servers))
        )
        self._rrsig_action = (
            RRSigAction(
                # The next signing time is set to the epoch start, so it will be signed immediately
                resign=datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc),
                iter=iter_rrsig_key(max_interval, config.ext_private_key),
            )
            if config.ext_private_key
            else None
        )
        self._a_recs = list(config.a_records)
        self._make_a_record = partial(make_a_record, max_interval)
        self._can_create_connection = partial(
            can_create_connection, timeout=float(connection_timeout)
        )

        self._zone = dns.versioned.Zone(config.zone_origins.primary)
        self._is_zone_recreated_at_least_once = False

    def _clear_zone(self, txn: dns.transaction.Transaction):
        logging.debug("Clearing zone...")

        for name in list(txn.iterate_names()):
            logging.debug("Deleting node %s...", name)
            txn.delete(name)

        logging.debug("Zone cleared")

    def _add_a_record_to_zone(
        self, a_record: AHealthyRecord, txn: dns.transaction.Transaction
    ):
        dataset = self._make_a_record(a_record)
        if dataset:
            txn.add(a_record.subdomain, dataset)
            logging.debug("Added A record %s to zone", a_record.subdomain)
        else:
            logging.debug("A record %s skipped", a_record.subdomain)

    def _add_records_to_zone(self, txn: dns.transaction.Transaction):
        logging.debug("Adding records to zone...")

        txn.add(dns.name.empty, self._ns_rec)
        logging.debug("Added NS record to zone")

        txn.add(dns.name.empty, next(self._soa_rec))
        logging.debug("Added SOA record to zone")

        for a_record in self._a_recs:
            self._add_a_record_to_zone(a_record, txn)

        logging.debug("Records added to zone")

    def _sign_zone(self, txn: dns.transaction.Transaction):
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

    def _recreate_zone(self):
        with self._zone.writer() as txn:
            self._clear_zone(txn)
            self._add_records_to_zone(txn)
            self._sign_zone(txn)

        self._is_zone_recreated_at_least_once = True

    def _is_zone_sign_near_to_expire(self) -> bool:
        return (
            datetime.datetime.now(datetime.timezone.utc) >= self._rrsig_action.resign
            if self._rrsig_action
            else False
        )

    def _refresh_a_record(
        self, a_record: AHealthyRecord, should_abort: ShouldAbortOp
    ) -> Optional[AHealthyRecord]:
        logging.debug("Checking A record %s ...", a_record.subdomain)

        updated_ips = []
        for health_ip in a_record.healthy_ips:
            if should_abort():
                logging.debug("Abort record check. Keep A record as it is")
                return None

            checked_ip = health_ip.updated_status(
                self._can_create_connection(health_ip.ip, health_ip.health_port)
            )
            logging.debug(
                "Checked IP %s on port %s: from %s to %s",
                checked_ip.ip,
                checked_ip.health_port,
                health_ip.is_healthy,
                checked_ip.is_healthy,
            )

            updated_ips.append(checked_ip)

        logging.debug("A record %s checked", a_record.subdomain)

        return a_record.updated_ips(updated_ips)

    def _refresh_a_recs(self, should_abort: ShouldAbortOp) -> RefreshARecordsResult:
        checked_a_recs = []

        are_there_any_changes = False
        for a_record in self._a_recs:
            checked_record = self._refresh_a_record(a_record, should_abort)
            if checked_record is None:
                logging.debug("Zone updater stopped. No A record updated")
                return RefreshARecordsResult.ABORTED

            checked_a_recs.append(checked_record)

            are_there_any_changes = (
                are_there_any_changes
                or checked_record.healthy_ips != a_record.healthy_ips
            )

        self._a_recs = checked_a_recs

        return (
            RefreshARecordsResult.CHANGES
            if are_there_any_changes
            else RefreshARecordsResult.NO_CHANGES
        )

    def _recreate_zone_after_refresh(self, should_abort: ShouldAbortOp):
        refresh_result = self._refresh_a_recs(should_abort)
        if refresh_result == RefreshARecordsResult.ABORTED:
            logging.info("Zone updater stopped. Keep zone as it is")
            return

        do_update_zone = refresh_result == RefreshARecordsResult.CHANGES
        if do_update_zone:
            logging.info("A records changed")

        if self._is_zone_sign_near_to_expire():
            logging.info("Zone signing is near to expire")
            do_update_zone = True

        if do_update_zone or not self._is_zone_recreated_at_least_once:
            logging.info("Updating zone...")
            self._recreate_zone()

    def update(
        self, *, check_ips: bool = True, should_abort: ShouldAbortOp = lambda: False
    ):
        """Update the zone with optional health checking and abort capability."""
        if check_ips:
            self._recreate_zone_after_refresh(should_abort)
        else:
            self._recreate_zone()
