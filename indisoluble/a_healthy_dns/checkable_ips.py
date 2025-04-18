#!/usr/bin/env python3

from typing import List

from .tools.is_valid_ip import is_valid_ip
from .tools.is_valid_port import is_valid_port


class CheckableIps:
    @property
    def ips(self) -> List[str]:
        return self._ips

    @property
    def health_port(self) -> int:
        return self._health_port

    def __init__(self, ips: List[str], health_port: int):
        if not ips:
            raise ValueError("IP list cannot be empty")

        self._ips = []
        for ip in ips:
            success, error = is_valid_ip(ip)
            if not success:
                raise ValueError(f"Invalid IP address '{ip}': {error}")

            self._ips.append(ip)

        success, error = is_valid_port(health_port)
        if not success:
            raise ValueError(f"Invalid port '{health_port}': {error}")

        self._health_port = health_port

    def __repr__(self):
        return f"CheckableIps(ips={self.ips}, health_port={self.health_port})"
