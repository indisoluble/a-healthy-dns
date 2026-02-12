#!/usr/bin/env python3

"""DNS server configuration factory and validation.

Creates and validates DNS server configurations from command-line arguments,
handling zone setup, DNSSEC key management, and health check parameters.
"""

import json
import logging

import dns.dnssec
import dns.dnssecalgs
import dns.name

from typing import Any, Dict, FrozenSet, List, NamedTuple, Optional, Union

from indisoluble.a_healthy_dns.records.a_healthy_record import AHealthyRecord
from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp
from indisoluble.a_healthy_dns.tools.is_valid_subdomain import is_valid_subdomain


class ExtendedPrivateKey(NamedTuple):
    """Extended private key containing both the private key and DNSKEY record."""

    private_key: dns.dnssec.PrivateKey
    dnskey: dns.dnssec.DNSKEY


class DnsServerConfig(NamedTuple):
    """DNS server configuration containing zone data and security settings."""

    origin_name: dns.name.Name
    name_servers: FrozenSet[str]
    a_records: FrozenSet[AHealthyRecord]
    ext_private_key: Optional[ExtendedPrivateKey]
    alias_zones: FrozenSet[dns.name.Name]


ARG_ALIAS_ZONES = "alias_zones"
ARG_DNSSEC_ALGORITHM = "priv_key_alg"
ARG_DNSSEC_PRIVATE_KEY_PATH = "priv_key_path"
ARG_HOSTED_ZONE = "zone"
ARG_NAME_SERVERS = "name_servers"
ARG_SUBDOMAIN_HEALTH_PORT = "health_port"
ARG_SUBDOMAIN_IP_LIST = "ips"
ARG_ZONE_RESOLUTIONS = "resolutions"


def _make_origin_name(args: Dict[str, Any]) -> Optional[dns.name.Name]:
    hosted_zone = args[ARG_HOSTED_ZONE]
    success, error = is_valid_subdomain(hosted_zone)
    if not success:
        logging.error("Hosted zone '%s' is not a valid FQDN: %s", hosted_zone, error)
        return None

    return dns.name.from_text(hosted_zone, origin=dns.name.root)


def _make_healthy_a_record(
    origin_name: dns.name.Name,
    subdomain: str,
    sub_config: Dict[str, Union[List[str], int]],
) -> Optional[AHealthyRecord]:
    success, error = is_valid_subdomain(subdomain)
    if not success:
        logging.error(
            "Zone resolution subdomain '%s' is not valid: %s", subdomain, error
        )
        return None

    subdomain_name = dns.name.from_text(subdomain, origin=origin_name)

    if not isinstance(sub_config, dict):
        logging.error(
            "Zone resolution for '%s' must be a dictionary, got %s",
            subdomain,
            type(sub_config).__name__,
        )
        return None

    ip_list = sub_config[ARG_SUBDOMAIN_IP_LIST]
    if not isinstance(ip_list, list):
        logging.error(
            "IP list for '%s' must be a list, got %s", subdomain, type(ip_list).__name__
        )
        return None

    if not ip_list:
        logging.error("IP list for '%s' cannot be empty", subdomain)
        return None

    health_port = sub_config[ARG_SUBDOMAIN_HEALTH_PORT]
    if not isinstance(health_port, int):
        logging.error(
            "Health port for '%s' must be an integer, got %s",
            subdomain,
            type(health_port).__name__,
        )
        return None

    try:
        healthy_ips = [AHealthyIp(ip, health_port, False) for ip in ip_list]
    except ValueError as ex:
        logging.error("Invalid IP address in '%s': %s", subdomain, ex)
        return None

    return AHealthyRecord(subdomain_name, healthy_ips)


def _make_a_records(
    origin_name: dns.name.Name, args: Dict[str, Any]
) -> Optional[FrozenSet[AHealthyRecord]]:
    try:
        raw_resolutions = json.loads(args[ARG_ZONE_RESOLUTIONS])
    except json.JSONDecodeError as ex:
        logging.error("Failed to parse zone resolutions: %s", ex)
        return None

    if not isinstance(raw_resolutions, dict):
        logging.error(
            "Zone resolutions must be a dictionary, got %s",
            type(raw_resolutions).__name__,
        )
        return None

    if not raw_resolutions:
        logging.error("Zone resolutions cannot be empty")
        return None

    a_records = []
    for subdomain, sub_config in raw_resolutions.items():
        a_record = _make_healthy_a_record(origin_name, subdomain, sub_config)
        if not a_record:
            logging.error("Failed to create A record for '%s'", subdomain)
            return None

        a_records.append(a_record)

    return frozenset(a_records)


def _make_name_servers(args: Dict[str, Any]) -> Optional[FrozenSet[str]]:
    try:
        name_servers = json.loads(args[ARG_NAME_SERVERS])
    except json.JSONDecodeError as ex:
        logging.error("Failed to parse name servers: %s", ex)
        return None

    if not isinstance(name_servers, list):
        logging.error(
            "Name servers must be a list, got %s", type(name_servers).__name__
        )
        return None

    if not name_servers:
        logging.error("Name server list cannot be empty")
        return None

    abs_name_servers = []
    for ns in name_servers:
        success, error = is_valid_subdomain(ns)
        if not success:
            logging.error("Name server '%s' is not a valid FQDN: %s", ns, error)
            return None

        abs_name_servers.append(f"{ns}.")

    return frozenset(abs_name_servers)


def _make_alias_zones(args: Dict[str, Any]) -> FrozenSet[dns.name.Name]:
    """Parse and validate alias zones from command-line arguments."""
    if ARG_ALIAS_ZONES not in args or not args[ARG_ALIAS_ZONES]:
        return frozenset()

    try:
        alias_zones = json.loads(args[ARG_ALIAS_ZONES])
    except json.JSONDecodeError as ex:
        logging.error("Failed to parse alias zones: %s", ex)
        return frozenset()

    if not isinstance(alias_zones, list):
        logging.error("Alias zones must be a list, got %s", type(alias_zones).__name__)
        return frozenset()

    valid_alias_zones = []
    for zone in alias_zones:
        success, error = is_valid_subdomain(zone)
        if not success:
            logging.warning("Alias zone '%s' is not a valid FQDN: %s", zone, error)
            continue

        alias_zone_name = dns.name.from_text(zone, origin=dns.name.root)
        valid_alias_zones.append(alias_zone_name)

    if valid_alias_zones:
        logging.info("Configured %d alias zone(s)", len(valid_alias_zones))

    return frozenset(valid_alias_zones)


def _load_dnssec_private_key(key_path: str) -> Optional[bytes]:
    try:
        with open(key_path, "rb") as key_file:
            private_key = key_file.read()
            logging.info("Loaded DNSSEC private key from %s", key_path)
            return private_key
    except Exception as ex:
        logging.error("Failed to load DNSSEC private key: %s", ex)
        return None


def _make_private_key(args: Dict[str, Any]) -> Optional[ExtendedPrivateKey]:
    priv_key_pem = _load_dnssec_private_key(args[ARG_DNSSEC_PRIVATE_KEY_PATH])
    if not priv_key_pem:
        return None

    try:
        alg = dns.dnssec.algorithm_from_text(args[ARG_DNSSEC_ALGORITHM])

        priv_key = dns.dnssecalgs.get_algorithm_cls(alg).from_pem(priv_key_pem)
        dnskey = dns.dnssec.make_dnskey(priv_key.public_key(), alg)
    except Exception as ex:
        logging.error("Failed to load private key: %s", ex)
        return None

    return ExtendedPrivateKey(private_key=priv_key, dnskey=dnskey)


def make_config(args: Dict[str, Any]) -> Optional[DnsServerConfig]:
    """Create complete DNS server configuration from command-line arguments."""
    origin_name = _make_origin_name(args)
    if not origin_name:
        return None

    a_records = _make_a_records(origin_name, args)
    if not a_records:
        return None

    name_servers = _make_name_servers(args)
    if not name_servers:
        return None

    alias_zones = _make_alias_zones(args)

    ext_private_key = None
    if args[ARG_DNSSEC_PRIVATE_KEY_PATH]:
        ext_private_key = _make_private_key(args)
        if not ext_private_key:
            return None

    return DnsServerConfig(
        origin_name=origin_name,
        name_servers=name_servers,
        a_records=a_records,
        ext_private_key=ext_private_key,
        alias_zones=alias_zones,
    )
