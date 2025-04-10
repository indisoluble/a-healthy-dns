#!/usr/bin/env python3

import logging

from .checkable_ip import CheckableIp


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
    def checkable_ips(self) -> list[CheckableIp]:
        return self._checkable_ips

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
        resolutions: dict[str, list[CheckableIp]],
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
        self._abs_hosted_zone = f"{hosted_zone}."

        if not name_servers:
            raise ValueError("Name server list cannot be empty")

        self._abs_name_servers = []
        for ns in name_servers:
            success, error = DNSServerConfig._is_valid_subdomain(ns)
            if not success:
                raise ValueError(f"Name server '{ns}' is not a valid FQDN: {error}")
            self._abs_name_servers.append(f"{ns}.")

        if not resolutions:
            raise ValueError("Zone resolutions cannot be empty")

        self._abs_resolutions = {}
        self._healthy_ips = {}
        for subdomain, checkable_ips in resolutions.items():
            success, error = DNSServerConfig._is_valid_subdomain(subdomain)
            if not success:
                raise ValueError(
                    f"Zone resolution subdomain '{subdomain}' is not valid: {error}"
                )
            if not checkable_ips:
                raise ValueError(f"IP list for '{subdomain}' cannot be empty")
            self._abs_resolutions[f"{subdomain}.{hosted_zone}."] = list(checkable_ips)
            self._healthy_ips.update({ip: True for ip in checkable_ips})
        self._checkable_ips = list(self._healthy_ips.keys())

        if ttl_a <= 0:
            raise ValueError("TTL for A records must be positive")
        self._ttl_a = ttl_a

        if ttl_ns <= 0:
            raise ValueError("TTL for NS records must be positive")
        self._ttl_ns = ttl_ns

        if soa_serial <= 0:
            raise ValueError("SOA serial must be positive")
        self._soa_serial = soa_serial

        if soa_refresh <= 0:
            raise ValueError("SOA refresh value must be positive")
        self._soa_refresh = soa_refresh

        if soa_retry <= 0:
            raise ValueError("SOA retry value must be positive")
        self._soa_retry = soa_retry

        if soa_expire <= 0:
            raise ValueError("SOA expire value must be positive")
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

    def _update_ip_status(self, checkable_ip: CheckableIp, status: bool):
        if checkable_ip in self._healthy_ips:
            # Update boolean values is an atomic operation in CPython,
            # following code is thread-safe
            self._healthy_ips[checkable_ip] = status

            logging.debug("Updated IP %s to %s", checkable_ip, status)
        else:
            logging.warning("IP %s not found in the config", checkable_ip)

    def enable_ip(self, checkable_ip: CheckableIp):
        self._update_ip_status(checkable_ip, True)

    def disable_ip(self, checkable_ip: CheckableIp):
        self._update_ip_status(checkable_ip, False)

    def healthy_ips(self, qname: str) -> list[str]:
        if qname not in self._abs_resolutions:
            logging.warning("%s not found", qname)
            return []

        # Update boolean values is an atomic operation in CPython,
        # following code is thread-safe
        ips = [
            checkIp.ip
            for checkIp in self._abs_resolutions[qname]
            if self._healthy_ips[checkIp]
        ]
        if ips:
            logging.debug("Resolved %s to %s", qname, ips)
        else:
            logging.warning("No healthy IPs for %s", qname)

        return ips
