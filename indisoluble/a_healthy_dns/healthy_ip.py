#!/usr/bin/env python3

from .tools.is_valid_ip import is_valid_ip
from .tools.is_valid_port import is_valid_port
from .tools.normalize_ip import normalize_ip


class HealthyIp:
    @property
    def ip(self) -> str:
        return self._ip

    @property
    def ttl_a(self) -> int:
        return self._ttl_a

    @property
    def health_port(self) -> int:
        return self._health_port

    @property
    def is_healthy(self) -> bool:
        return self._is_healthy

    def __init__(self, ip: str, ttl_a: int, health_port: int, is_healthy: bool):
        success, error = is_valid_ip(ip)
        if not success:
            raise ValueError(f"Invalid IP address: {error}")

        if ttl_a <= 0:
            raise ValueError("TTL for A records must be positive")

        success, error = is_valid_port(health_port)
        if not success:
            raise ValueError(f"Invalid port: {error}")

        self._ip = normalize_ip(ip)
        self._ttl_a = ttl_a
        self._health_port = health_port
        self._is_healthy = is_healthy

    def __eq__(self, other):
        if not isinstance(other, HealthyIp):
            return False

        return (
            self.ip == other.ip
            and self.ttl_a == other.ttl_a
            and self.health_port == other.health_port
            and self.is_healthy == other.is_healthy
        )

    def __hash__(self):
        return hash((self.ip, self.ttl_a, self.health_port, self.is_healthy))

    def __repr__(self):
        return (
            f"HealthyIp(ip='{self.ip}', "
            f"ttl_a={self.ttl_a}, "
            f"health_port={self.health_port}, "
            f"is_healthy={self.is_healthy})"
        )
