#!/usr/bin/env python3

from typing import Tuple


class CheckableIp:
    @property
    def ip(self) -> str:
        return self._ip

    @property
    def health_port(self) -> int:
        return self._health_port

    def __init__(self, ip: str, health_port: int):
        success, error = self._is_valid_ip(ip)
        if not success:
            raise ValueError(f"Invalid IP address: {error}")

        success, error = self._is_valid_port(health_port)
        if not success:
            raise ValueError(f"Invalid port: {error}")

        self._ip = ip
        self._health_port = health_port

    @classmethod
    def _is_valid_ip(cls, ip: str) -> Tuple[bool, str]:
        parts = ip.split(".")
        if len(parts) != 4:
            return (False, "IP address must have 4 octets")

        for part in parts:
            if not part.isdigit() or not (0 <= int(part) <= 255):
                return (False, "Each octet must be a number between 0 and 255")

        return (True, "")

    @classmethod
    def _is_valid_port(cls, port: int) -> Tuple[bool, str]:
        if not (1 <= port <= 65535):
            return (False, "Port must be between 1 and 65535")

        return (True, "")

    def __eq__(self, other):
        if not isinstance(other, CheckableIp):
            return False

        return self.ip == other.ip and self.health_port == other.health_port

    def __hash__(self):
        return hash((self.ip, self.health_port))

    def __repr__(self):
        return f"CheckableIp(ip='{self.ip}', health_port={self.health_port})"
