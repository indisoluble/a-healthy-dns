#!/usr/bin/env python3

"""Healthy A record containing multiple IP addresses with health status.

Provides a DNS A record implementation that tracks health status of multiple
IP addresses for a single subdomain.
"""

import dns.name

from typing import FrozenSet, List

from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp


class AHealthyRecord:
    """DNS A record with multiple IP addresses and health status tracking."""

    @property
    def subdomain(self) -> dns.name.Name:
        """Get the subdomain name for this A record."""
        return self._subdomain

    @property
    def healthy_ips(self) -> FrozenSet[AHealthyIp]:
        """Get the set of healthy IP addresses for this record."""
        return self._healthy_ips

    def __init__(self, subdomain: dns.name.Name, healthy_ips: List[AHealthyIp]):
        """Initialize healthy A record with subdomain and IP list."""
        self._subdomain = subdomain
        self._healthy_ips = frozenset(healthy_ips)

    def updated_ips(self, updated_ips: List[AHealthyIp]) -> "AHealthyRecord":
        """Return new record with updated IP list if changed."""
        if updated_ips == self.healthy_ips:
            return self

        return AHealthyRecord(subdomain=self.subdomain, healthy_ips=updated_ips)

    def __eq__(self, other):
        if not isinstance(other, AHealthyRecord):
            return False

        return self.subdomain == other.subdomain

    def __hash__(self):
        return hash(self.subdomain)

    def __repr__(self):
        ips_str = ", ".join(f"{ip}" for ip in self.healthy_ips)

        return f"AHealthyRecord(subdomain={self.subdomain}, healthy_ips=[{ips_str}])"
