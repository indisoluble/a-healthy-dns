#!/usr/bin/env python3

"""DNSSEC signature management and key handling.

Provides DNSSEC signature lifetime management and key iteration for
automatic zone signing with configurable timing parameters.
"""

import datetime
import logging

import dns.dnssec

from typing import Iterator, List, NamedTuple, Tuple

from indisoluble.a_healthy_dns.dns_server_config_factory import ExtendedPrivateKey
from indisoluble.a_healthy_dns.records.time import (
    calculate_dnskey_ttl,
    calculate_rrsig_lifetime,
)


class RRSigKey(NamedTuple):
    """DNSSEC signature key with timing and validation parameters."""

    keys: List[Tuple[dns.dnssec.PrivateKey, dns.dnssec.DNSKEY]]
    dnskey_ttl: int
    inception: datetime.datetime
    expiration: datetime.datetime


class ExtendedRRSigKey(NamedTuple):
    """Extended DNSSEC signature key with automatic resign timing."""

    key: RRSigKey
    resign: datetime.datetime


def iter_rrsig_key(
    max_interval: int, ext_private_key: ExtendedPrivateKey
) -> Iterator[ExtendedRRSigKey]:
    """Generate DNSSEC signature keys with automatic timing management."""
    dnskey = (ext_private_key.private_key, ext_private_key.dnskey)
    ttl = calculate_dnskey_ttl(max_interval)
    lifetime = calculate_rrsig_lifetime(max_interval)

    while True:
        inception = datetime.datetime.now(datetime.timezone.utc)
        expiration = inception + datetime.timedelta(seconds=lifetime.expiration)
        resign = inception + datetime.timedelta(seconds=lifetime.resign)
        logging.debug(
            "Created RRSIG key with inception: %s, expiration: %s, resign: %s",
            inception,
            expiration,
            resign,
        )

        yield ExtendedRRSigKey(
            key=RRSigKey(
                keys=[dnskey],
                dnskey_ttl=ttl,
                inception=inception,
                expiration=expiration,
            ),
            resign=resign,
        )
