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
    def abs_hosted_zone(self) -> str:
        return self._abs_hosted_zone

    @property
    def primary_abs_name_server(self) -> str:
        return self._abs_name_servers[0]

    @property
    def abs_name_servers(self) -> list[str]:
        return self._abs_name_servers

    @property
    def abs_resolutions(self) -> dict[str, list[str]]:
        return self._abs_resolutions

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
        sucess, error = DNSServerConfig._is_valid_subdomain(hosted_zone)
        if not sucess:
            raise ValueError(
                f"Hosted zone '{hosted_zone}' is not a valid FQDN: {error}"
            )

        if not name_servers:
            raise ValueError("Name server list cannot be empty")

        for ns in name_servers:
            success, error = DNSServerConfig._is_valid_subdomain(ns)
            if not success:
                raise ValueError(f"Name server '{ns}' is not a valid FQDN: {error}")

        if not resolutions:
            raise ValueError("Zone resolution cannot be empty")

        for subdomain, ip_list in resolutions.items():
            success, error = DNSServerConfig._is_valid_subdomain(subdomain)
            if not success:
                raise ValueError(
                    f"Zone resolution subdomain '{subdomain}' is not valid: {error}"
                )

            if not ip_list:
                raise ValueError(f"IP list for '{subdomain}' cannot be empty")

            for ip in ip_list:
                success, error = DNSServerConfig._is_valid_ip(ip)
                if not success:
                    raise ValueError(
                        f"Invalid IP address '{ip}' for '{subdomain}': {error}"
                    )

        if ttl_a <= 0:
            raise ValueError("TTL for A records must be positive")

        if ttl_ns <= 0:
            raise ValueError("TTL for NS records must be positive")

        if soa_serial <= 0:
            raise ValueError("SOA serial must be positive")

        if soa_refresh <= 0:
            raise ValueError("SOA refresh value must be positive")

        if soa_retry <= 0:
            raise ValueError("SOA retry value must be positive")

        if soa_expire <= 0:
            raise ValueError("SOA expire value must be positive")

        self._abs_hosted_zone = f"{hosted_zone}."
        self._abs_name_servers = [f"{ns}." for ns in name_servers]
        self._abs_resolutions = {
            f"{subdomain}.{hosted_zone}.": ip_list
            for subdomain, ip_list in resolutions.items()
        }
        self._ttl_a = ttl_a
        self._ttl_ns = ttl_ns
        self._soa_serial = soa_serial
        self._soa_refresh = soa_refresh
        self._soa_retry = soa_retry
        self._soa_expire = soa_expire

    @classmethod
    def _is_valid_subdomain(cls, name_server: str) -> tuple[bool, str]:
        if not name_server:
            return (False, "It cannot be empty")

        if not all(
            label and all(c.isalnum() or c == "-" for c in label)
            for label in name_server.split(".")
        ):
            return (
                False,
                "Labels must contain only alphanumeric characters or hyphens",
            )

        return (True, "")

    @classmethod
    def _is_valid_ip(cls, ip: str) -> tuple[bool, str]:
        parts = ip.split(".")
        if len(parts) != 4:
            return (False, "IP address must have 4 octets")

        for part in parts:
            if not part.isdigit() or not (0 <= int(part) <= 255):
                return (False, "Each octet must be a number between 0 and 255")

        return (True, "")

    @classmethod
    def make_config(cls, args) -> Optional["DNSServerConfig"]:
        try:
            name_servers = json.loads(args[NAME_SERVERS_ARG])
        except json.JSONDecodeError as ex:
            logging.exception("Failed to parse name servers: %s", ex)
            return

        try:
            resolutions = json.loads(args[ZONE_RESOLUTIONS_ARG])
        except json.JSONDecodeError as ex:
            logging.exception("Failed to parse zone resolutions: %s", ex)
            return

        try:
            config = cls(
                hosted_zone=args[HOSTED_ZONE_ARG],
                name_servers=name_servers,
                resolutions=resolutions,
                ttl_a=args[TTL_A_ARG],
                ttl_ns=args[TTL_NS_ARG],
                soa_serial=int(time.time()),
                soa_refresh=args[SOA_REFRESH_ARG],
                soa_retry=args[SOA_RETRY_ARG],
                soa_expire=args[SOA_EXPIRE_ARG],
            )
        except ValueError as ex:
            logging.exception("Failed to create DNS server config: %s", ex)
            return

        return config
