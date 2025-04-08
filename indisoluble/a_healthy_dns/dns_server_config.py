#!/usr/bin/env python3

import logging

from typing import Union

from .checkable_ip import CheckableIp


_SUBDOMAIN_HEALTH_PORT_ARG = "health_port"
_SUBDOMAIN_IP_LIST_ARG = "ips"


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
        resolutions: dict[str, dict[str, Union[list[str], int]]],
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

        if not isinstance(name_servers, list):
            raise ValueError(
                f"Name servers must be a list, got {type(name_servers).__name__}"
            )

        if not name_servers:
            raise ValueError("Name server list cannot be empty")

        for ns in name_servers:
            success, error = DNSServerConfig._is_valid_subdomain(ns)
            if not success:
                raise ValueError(f"Name server '{ns}' is not a valid FQDN: {error}")

        if not isinstance(resolutions, dict):
            raise ValueError(
                f"Zone resolutions must be a dictionary, got {type(name_servers).__name__}"
            )

        if not resolutions:
            raise ValueError("Zone resolutions cannot be empty")

        for subdomain, sub_config in resolutions.items():
            success, error = DNSServerConfig._is_valid_subdomain(subdomain)
            if not success:
                raise ValueError(
                    f"Zone resolution subdomain '{subdomain}' is not valid: {error}"
                )

            if not isinstance(sub_config, dict):
                raise ValueError(
                    f"Zone resolution for '{subdomain}' must be a dictionary, got {type(sub_config).__name__}"
                )

            health_port = sub_config[_SUBDOMAIN_HEALTH_PORT_ARG]
            success, error = DNSServerConfig._is_valid_port(health_port)
            if not success:
                raise ValueError(f"Health port for '{subdomain}' is not valid: {error}")

            ip_list = sub_config[_SUBDOMAIN_IP_LIST_ARG]

            if not isinstance(ip_list, list):
                raise ValueError(
                    f"IP list for '{subdomain}' must be a list, got {type(ip_list).__name__}"
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

        self._ttl_a = ttl_a
        self._ttl_ns = ttl_ns
        self._soa_serial = soa_serial
        self._soa_refresh = soa_refresh
        self._soa_retry = soa_retry
        self._soa_expire = soa_expire

        self._abs_hosted_zone = f"{hosted_zone}."
        self._abs_name_servers = [f"{ns}." for ns in name_servers]
        self._abs_resolutions = {
            f"{subdomain}.{hosted_zone}.": [
                CheckableIp(ip, sub_config[_SUBDOMAIN_HEALTH_PORT_ARG])
                for ip in sub_config[_SUBDOMAIN_IP_LIST_ARG]
            ]
            for subdomain, sub_config in resolutions.items()
        }
        self._healthy_ips = {
            CheckableIp(ip, sub_config[_SUBDOMAIN_HEALTH_PORT_ARG]): True
            for ip in sub_config[_SUBDOMAIN_IP_LIST_ARG]
            for _, sub_config in resolutions.items()
        }

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
    def _is_valid_port(cls, port: int) -> tuple[bool, str]:
        if not (1 <= port <= 65535):
            return (False, "Port must be between 1 and 65535")

        return (True, "")

    def _update_ip_status(self, ip: str, health_port: int, status: bool):
        checkIp = CheckableIp(ip, health_port)
        if checkIp in self._healthy_ips:
            # Update boolean values is an atomic operation in CPython,
            # following code is thread-safe
            self._healthy_ips[checkIp] = status

            logging.debug("Updated IP %s to %s", ip, status)
        else:
            logging.warning("IP %s not found in the config", ip)

    def enable_ip(self, ip: str, health_port: int):
        self._update_ip_status(ip, health_port, True)

    def disable_ip(self, ip: str, health_port: int):
        self._update_ip_status(ip, health_port, False)

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
