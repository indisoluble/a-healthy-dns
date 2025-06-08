#!/usr/bin/env python3

import dns.name

from typing import FrozenSet, List

from .healthy_ip import HealthyIp


class HealthyARecord:
    @property
    def subdomain(self) -> dns.name.Name:
        return self._subdomain

    @property
    def healthy_ips(self) -> FrozenSet[HealthyIp]:
        return self._healthy_ips

    def __init__(self, subdomain: dns.name.Name, healthy_ips: List[HealthyIp]):
        self._subdomain = subdomain
        self._healthy_ips = frozenset(healthy_ips)

    def updated_ips(self, updated_ips: List[HealthyIp]) -> "HealthyARecord":
        if updated_ips == self.healthy_ips:
            return self

        return HealthyARecord(subdomain=self.subdomain, healthy_ips=updated_ips)

    def __eq__(self, other):
        if not isinstance(other, HealthyARecord):
            return False

        return self.subdomain == other.subdomain

    def __hash__(self):
        return hash(self.subdomain)

    def __repr__(self):
        ips_str = ", ".join(f"{ip}" for ip in self.healthy_ips)

        return f"HealthyARecord(subdomain={self.subdomain}, healthy_ips=[{ips_str}])"
