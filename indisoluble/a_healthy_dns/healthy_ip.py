#!/usr/bin/env python3

from .tools.is_valid_ip import is_valid_ip
from .tools.is_valid_port import is_valid_port
from .tools.normalize_ip import normalize_ip


class HealthyIp:
    @property
    def ip(self) -> str:
        return self._ip

    @property
    def health_port(self) -> int:
        return self._health_port

    @property
    def is_healthy(self) -> bool:
        return self._is_healthy

    def __init__(self, ip: str, health_port: int, is_healthy: bool):
        success, error = is_valid_ip(ip)
        if not success:
            raise ValueError(f"Invalid IP address: {error}")

        success, error = is_valid_port(health_port)
        if not success:
            raise ValueError(f"Invalid port: {error}")

        self._ip = normalize_ip(ip)
        self._health_port = health_port
        self._is_healthy = is_healthy

    def updated_status(self, is_healthy: bool) -> "HealthyIp":
        if is_healthy == self._is_healthy:
            return self

        return HealthyIp(
            ip=self.ip, health_port=self.health_port, is_healthy=is_healthy
        )

    def __eq__(self, other):
        if not isinstance(other, HealthyIp):
            return False

        return (
            self.ip == other.ip
            and self.health_port == other.health_port
            and self.is_healthy == other.is_healthy
        )

    def __hash__(self):
        return hash((self.ip, self.health_port, self.is_healthy))

    def __repr__(self):
        return (
            f"HealthyIp(ip='{self.ip}', "
            f"health_port={self.health_port}, "
            f"is_healthy={self.is_healthy})"
        )
