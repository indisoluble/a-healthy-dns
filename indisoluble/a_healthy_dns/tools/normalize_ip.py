#!/usr/bin/env python3

"""IP address normalization utilities.

Provides functions to normalize IPv4 addresses by removing leading zeros
from octets while preserving valid format.
"""


def normalize_ip(ip_address: str) -> str:
    """Normalize IPv4 address by removing leading zeros from octets."""
    octets = ip_address.split(".")
    normalized_octets = [octet.lstrip("0") or "0" for octet in octets]

    return ".".join(normalized_octets)
