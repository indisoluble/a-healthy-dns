#!/usr/bin/env python3

"""DNS timing calculations for TTL and DNSSEC signature lifetimes.

Provides functions to calculate appropriate TTL values for different DNS
record types based on health check intervals and zone update frequency.
"""

import functools

from collections.abc import Callable
from typing import NamedTuple


class RRSigLifetime(NamedTuple):
    """DNSSEC signature lifetime with resign and expiration times."""

    resign: int
    expiration: int


RFC8767_MAX_TTL = (1 << 31) - 1


def clamp_ttl(ttl: int) -> int:
    """Clamp DNS TTL values per RFC 8767's updated TTL definition.

    RFC 8767 updates the DNS TTL field definition to treat TTL values as
    unsigned and recommends a maximum caching TTL of 2^31-1 seconds.
    """
    if ttl <= 0:
        return 0
    if ttl > RFC8767_MAX_TTL:
        return RFC8767_MAX_TTL
    return ttl


def ttl_clamped(ttl_calculator: Callable[..., int]) -> Callable[..., int]:
    """Decorate a TTL calculator so its output complies with RFC 8767."""

    @functools.wraps(ttl_calculator)
    def wrapper(*args, **kwargs) -> int:
        return clamp_ttl(ttl_calculator(*args, **kwargs))

    return wrapper


@ttl_clamped
def calculate_a_ttl(max_interval: int) -> int:
    """Calculate A record TTL as 2x test interval to ensure clients get
    reasonably fresh data while reducing DNS server pressure."""
    return max_interval * 2


@ttl_clamped
def calculate_ns_ttl(max_interval: int) -> int:
    """Calculate NS record TTL as 30x A record TTL for highly dynamic
    environments where new VMs/baremetal deploy in ~15 minutes."""
    return calculate_a_ttl(max_interval) * 30


@ttl_clamped
def calculate_soa_ttl(max_interval: int) -> int:
    """Calculate SOA record TTL using NS record TTL as SOA contains
    the primary name server information."""
    return calculate_ns_ttl(max_interval)


def calculate_soa_refresh(max_interval: int) -> int:
    """Calculate SOA refresh interval using DNSKEY TTL to ensure slaves
    read new keys when manually updated (~5 minute deployment time)."""
    return calculate_dnskey_ttl(max_interval)


def calculate_soa_retry(max_interval: int) -> int:
    """Calculate SOA retry interval as A record TTL for frequent
    retry attempts in dynamic environments."""
    return calculate_a_ttl(max_interval)


def calculate_soa_expire(max_interval: int) -> int:
    """Calculate SOA expire time as 5x retry interval to handle
    extended connectivity issues between primary and secondary DNS."""
    return calculate_soa_retry(max_interval) * 5


@ttl_clamped
def calculate_soa_min_ttl(max_interval: int) -> int:
    """Calculate SOA minimum TTL using A record TTL as baseline
    for negative caching in dynamic environments."""
    return calculate_a_ttl(max_interval)


@ttl_clamped
def calculate_dnskey_ttl(max_interval: int) -> int:
    """Calculate DNSKEY TTL as 10x A record TTL, allowing ~5 minutes
    for manual key updates and redeployment in dynamic environments."""
    return calculate_a_ttl(max_interval) * 10


def calculate_rrsig_lifetime(max_interval: int) -> RRSigLifetime:
    """Calculate DNSSEC signature lifetime to handle worst-case scenario:
    slave refresh failures requiring validity through expire + retry periods."""
    return RRSigLifetime(
        resign=calculate_soa_refresh(max_interval),
        expiration=2 * calculate_soa_refresh(max_interval)
        + calculate_soa_expire(max_interval)
        + calculate_soa_retry(max_interval),
    )
