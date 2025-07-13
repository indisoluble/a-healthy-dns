#!/usr/bin/env python3

"""DNS SOA record factory with dynamic serial number generation.

Creates DNS SOA records with time-based serial numbers and calculated timing
parameters for zone refresh, retry, and expiration.
"""

import logging

import dns.name
import dns.rdataclass
import dns.rdataset
import dns.rdatatype

from typing import Iterator

from indisoluble.a_healthy_dns.records.time import (
    calculate_soa_expire,
    calculate_soa_min_ttl,
    calculate_soa_refresh,
    calculate_soa_retry,
    calculate_soa_ttl,
)
from indisoluble.a_healthy_dns.tools.uint32_current_time import uint32_current_time


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


def iter_soa_record(
    max_interval: int, origin_name: dns.name.Name, primary_ns: str
) -> Iterator[dns.rdataset.Rdataset]:
    """Generate SOA records with dynamic serial numbers and timing parameters."""
    ttl = calculate_soa_ttl(max_interval)
    responsible = f"hostmaster.{origin_name}"
    serial = _iter_soa_serial()
    refresh = str(calculate_soa_refresh(max_interval))
    retry = str(calculate_soa_retry(max_interval))
    expire = str(calculate_soa_expire(max_interval))
    min_ttl = str(calculate_soa_min_ttl(max_interval))

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
