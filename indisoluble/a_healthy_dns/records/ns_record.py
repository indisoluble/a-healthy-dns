#!/usr/bin/env python3

import logging

import dns.rdataclass
import dns.rdataset
import dns.rdatatype

from typing import FrozenSet

from indisoluble.a_healthy_dns.records.time import calculate_ns_ttl


def make_ns_record(
    max_interval: int, name_servers: FrozenSet[str]
) -> dns.rdataset.Rdataset:
    ttl = calculate_ns_ttl(max_interval)
    rdataset = dns.rdataset.from_text(
        dns.rdataclass.IN, dns.rdatatype.NS, ttl, *name_servers
    )
    logging.debug(
        "Created NS record with ttl: %d, and name servers: %s", ttl, name_servers
    )

    return rdataset
