#!/usr/bin/env python3

from typing import NamedTuple


class RRSigLifetime(NamedTuple):
    resign: int
    expiration: int


def calculate_a_ttl(max_interval: int) -> int:
    return max_interval * 2


def calculate_ns_ttl(max_interval: int) -> int:
    return calculate_a_ttl(max_interval) * 30


def calculate_soa_ttl(max_interval: int) -> int:
    return calculate_ns_ttl(max_interval)


def calculate_soa_refresh(max_interval: int) -> int:
    return calculate_dnskey_ttl(max_interval)


def calculate_soa_retry(max_interval: int) -> int:
    return calculate_a_ttl(max_interval)


def calculate_soa_expire(max_interval: int) -> int:
    return calculate_soa_retry(max_interval) * 5


def calculate_soa_min_ttl(max_interval: int) -> int:
    return calculate_a_ttl(max_interval)


def calculate_dnskey_ttl(max_interval: int) -> int:
    return calculate_a_ttl(max_interval) * 10


def calculate_rrsig_lifetime(max_interval: int) -> RRSigLifetime:
    return RRSigLifetime(
        resign=calculate_soa_refresh(max_interval),
        expiration=2 * calculate_soa_refresh(max_interval)
        + calculate_soa_expire(max_interval)
        + calculate_soa_retry(max_interval),
    )
