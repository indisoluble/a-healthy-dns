#!/usr/bin/env python3

"""Healthy IP address representation with health checking capabilities.

Provides an IP address class that tracks health status and port information
for use in health-aware DNS A records.
"""

from typing import Any, Optional

from indisoluble.a_healthy_dns.tools.is_valid_ip import is_valid_ip
from indisoluble.a_healthy_dns.tools.is_valid_port import is_valid_port
from indisoluble.a_healthy_dns.tools.normalize_ip import normalize_ip


class AHealthyIp:
    """IP address with health status and optional port for health checking."""

    @property
    def ip(self) -> str:
        """Get the normalized IP address."""
        return self._ip

    @property
    def health_port(self) -> Optional[int]:
        """Get the health check port number."""
        return self._health_port

    @property
    def is_healthy(self) -> bool:
        """Get the current health status."""
        return self._is_healthy

    def __init__(self, ip: Any, health_port: Optional[Any], is_healthy: bool) -> None:
        """Initialize healthy IP with validation of IP address and optional port.

        Args:
            ip: IPv4 address string.
            health_port: TCP port for health checks, or None.
            is_healthy: Initial health status.
        """
        success, error = is_valid_ip(ip)
        if not success:
            raise ValueError(f"Invalid IP address: {error}")

        if health_port is not None:
            success, error = is_valid_port(health_port)
            if not success:
                raise ValueError(f"Invalid port: {error}")

        self._ip = normalize_ip(ip)
        self._health_port = health_port
        self._is_healthy = is_healthy

    def updated_status(self, is_healthy: bool) -> "AHealthyIp":
        """Return new instance with updated health status if changed."""
        if is_healthy == self._is_healthy:
            return self

        return AHealthyIp(
            ip=self.ip, health_port=self.health_port, is_healthy=is_healthy
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AHealthyIp):
            return False

        return (
            self.ip == other.ip
            and self.health_port == other.health_port
            and self.is_healthy == other.is_healthy
        )

    def __hash__(self) -> int:
        return hash((self.ip, self.health_port, self.is_healthy))

    def __repr__(self) -> str:
        port_part = f"health_port={self._health_port}, " if self._health_port is not None else ""
        return f"AHealthyIp(ip='{self._ip}', {port_part}is_healthy={self._is_healthy})"
