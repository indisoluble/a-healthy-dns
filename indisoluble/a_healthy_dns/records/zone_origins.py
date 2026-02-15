#!/usr/bin/env python3

"""Zone origins helper for DNS name normalization."""

import dns.name

from typing import List, Optional

from indisoluble.a_healthy_dns.tools.is_valid_subdomain import is_valid_subdomain


def _to_abs_name(raw_name: str) -> dns.name.Name:
    success, error = is_valid_subdomain(raw_name)
    if not success:
        raise ValueError(f"Invalid domain '{raw_name}': {error}")

    return dns.name.from_text(raw_name, origin=dns.name.root)


class ZoneOrigins:
    """Read-only holder of primary and alias zone origins."""

    @property
    def primary(self) -> dns.name.Name:
        """Get the primary zone origin."""
        return self._primary

    def __init__(self, primary: str, aliases: List[str]):
        """Initialize zone origins with a primary and alias set."""
        self._primary = _to_abs_name(primary)

        # Prefer the most specific matching zone and keep deterministic order.
        self._origins = sorted(
            {self._primary, *(_to_abs_name(alias) for alias in aliases)},
            key=lambda zone: (-len(zone), zone.to_text()),
        )

    def relativize(self, name: dns.name.Name) -> Optional[dns.name.Name]:
        """Return relative name using matching origin, or None when unmatched."""
        if not name.is_absolute():
            return name

        zone = next(
            (origin for origin in self._origins if name.is_subdomain(origin)), None
        )
        return name.relativize(zone) if zone else None
