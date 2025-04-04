#!/usr/bin/env python3

import json
import logging
import time

from typing import Optional


HOSTED_ZONE_ARG = "hosted_zone"
NAME_SERVERS_ARG = "name_servers"
ZONE_RESOLUTIONS_ARG = "zone_resolutions"
TTL_A_ARG = "ttl_a"
TTL_NS_ARG = "ttl_ns"
SOA_REFRESH_ARG = "soa_refresh"
SOA_RETRY_ARG = "soa_retry"
SOA_EXPIRE_ARG = "soa_expire"


class DNSServerConfig:
    @property
    def hosted_zone(self) -> str:
        return self._hosted_zone

    @property
    def primary_name_server(self) -> str:
        return self._name_servers[0]

    @property
    def name_servers(self) -> list[str]:
        return self._name_servers

    @property
    def resolutions(self) -> dict[str, list[str]]:
        return self._resolutions

    @property
    def ttl_a(self) -> int:
        return self._ttl_a

    @property
    def ttl_ns(self) -> int:
        return self._ttl_ns

    @property
    def soa_serial(self) -> int:
        return self._soa_serial

    @property
    def soa_refresh(self) -> int:
        return self._soa_refresh

    @property
    def soa_retry(self) -> int:
        return self._soa_retry

    @property
    def soa_expire(self) -> int:
        return self._soa_expire

    def __init__(
        self,
        hosted_zone: str,
        name_servers: list[str],
        resolutions: dict[str, list[str]],
        ttl_a: int,
        ttl_ns: int,
        soa_serial: int,
        soa_refresh: int,
        soa_retry: int,
        soa_expire: int,
    ):
        self._hosted_zone = hosted_zone
        self._name_servers = name_servers
        self._resolutions = resolutions
        self._ttl_a = ttl_a
        self._ttl_ns = ttl_ns
        self._soa_serial = soa_serial
        self._soa_refresh = soa_refresh
        self._soa_retry = soa_retry
        self._soa_expire = soa_expire

    @classmethod
    def make_config(cls, args) -> Optional["DNSServerConfig"]:
        # Parse name servers
        try:
            raw_name_servers = json.loads(args[NAME_SERVERS_ARG])
        except json.JSONDecodeError as ex:
            logging.exception("Failed to parse name servers: %s", ex)
            return

        name_servers = [f"{ns}." for ns in raw_name_servers]

        # Parse resolutions
        try:
            raw_resolutions = json.loads(args[ZONE_RESOLUTIONS_ARG])
        except json.JSONDecodeError as ex:
            logging.exception("Failed to parse zone resolutions: %s", ex)
            return

        resolutions = {
            f"{subdomain}.{args[HOSTED_ZONE_ARG]}.": ips
            for subdomain, ips in raw_resolutions.items()
        }

        # Compose config
        return cls(
            hosted_zone=f"{args[HOSTED_ZONE_ARG]}.",
            name_servers=name_servers,
            resolutions=resolutions,
            ttl_a=args[TTL_A_ARG],
            ttl_ns=args[TTL_NS_ARG],
            soa_serial=int(time.time()),
            soa_refresh=args[SOA_REFRESH_ARG],
            soa_retry=args[SOA_RETRY_ARG],
            soa_expire=args[SOA_EXPIRE_ARG],
        )
