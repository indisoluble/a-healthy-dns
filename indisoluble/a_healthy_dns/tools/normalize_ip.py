#!/usr/bin/env python3


def normalize_ip(ip_address: str) -> str:
    octets = ip_address.split(".")
    normalized_octets = [octet.lstrip("0") or "0" for octet in octets]

    return ".".join(normalized_octets)
