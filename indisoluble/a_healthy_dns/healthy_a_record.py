#!/usr/bin/env python3

import dns.name

from typing import FrozenSet

from .healthy_ip import HealthyIp


class HealthyARecord:
    @property
    def subdomain(self) -> dns.name.Name:
        return self._subdomain

    @property
    def ttl_a(self) -> int:
        return self._ttl_a

    @property
    def healthy_ips(self) -> FrozenSet[HealthyIp]:
        return self._healthy_ips

    def __init__(
        self, subdomain: dns.name.Name, ttl_a: int, healthy_ips: FrozenSet[HealthyIp]
    ):
        if ttl_a <= 0:
            raise ValueError("TTL for A records must be positive")

        self._subdomain = subdomain
        self._ttl_a = ttl_a
        self._healthy_ips = healthy_ips

    def __eq__(self, other):
        if not isinstance(other, HealthyARecord):
            return False

        return self.subdomain == other.subdomain

    def __hash__(self):
        return hash(self.subdomain)

    def __repr__(self):
        ips_str = ", ".join(f"{ip}" for ip in self.healthy_ips)

        return (
            f"HealthyARecord(subdomain={self.subdomain}, "
            f"ttl_a={self.ttl_a}, "
            f"healthy_ips=[{ips_str}])"
        )
