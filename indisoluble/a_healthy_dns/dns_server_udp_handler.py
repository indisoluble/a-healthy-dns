#!/usr/bin/env python3

"""UDP DNS server request handler.

Handles incoming DNS queries over UDP, processes them against the configured
zone, and returns appropriate DNS responses with authoritative answers.
"""

import logging
import socketserver

from typing import List

import dns.exception
import dns.flags
import dns.message
import dns.name
import dns.rcode
import dns.rdatatype
import dns.rrset
import dns.versioned
import dns.zone

from indisoluble.a_healthy_dns.records.zone_origins import ZoneOrigins


def _build_authority_with_apex_soa(
    zone: dns.versioned.Zone, txn: dns.zone.Transaction
) -> List[dns.rrset.RRset]:
    soa_rdataset = txn.get(dns.name.empty, dns.rdatatype.SOA)
    if soa_rdataset is None:
        return []

    soa_rrset = dns.rrset.RRset(zone.origin, soa_rdataset.rdclass, soa_rdataset.rdtype)
    soa_rrset.ttl = soa_rdataset.ttl
    for rdata in soa_rdataset:
        soa_rrset.add(rdata)

    return [soa_rrset]


def _build_answer(
    query_name: dns.name.Name, rdataset: dns.rdataset.Rdataset
) -> List[dns.rrset.RRset]:
    rrset = dns.rrset.RRset(query_name, rdataset.rdclass, rdataset.rdtype)
    rrset.ttl = rdataset.ttl
    for rdata in rdataset:
        rrset.add(rdata)

    return [rrset]


def _update_response(
    response: dns.message.Message,
    query_name: dns.name.Name,
    query_type: dns.rdatatype.RdataType,
    zone: dns.versioned.Zone,
    zone_origins: ZoneOrigins,
):
    relative_name = zone_origins.relativize(query_name)
    if relative_name is None:
        logging.warning(
            "Received query for domain not in hosted or alias zones: %s", query_name
        )
        response.set_rcode(dns.rcode.REFUSED)
        return

    with zone.reader() as txn:
        rcode = dns.rcode.NOERROR
        authority = []
        answer = []

        node = txn.get_node(relative_name)
        if node:
            rdataset = node.get_rdataset(zone.rdclass, query_type)
            if rdataset:
                answer = _build_answer(query_name, rdataset)
                logging.debug("Answered query for %s with %s", query_name, answer)
            else:
                logging.debug(
                    "Subdomain %s exists but has no %s records",
                    query_name,
                    dns.rdatatype.to_text(query_type),
                )
                authority = _build_authority_with_apex_soa(zone, txn)
        else:
            logging.warning("Received query for unknown subdomain: %s", query_name)
            rcode = dns.rcode.NXDOMAIN
            authority = _build_authority_with_apex_soa(zone, txn)

    response.set_rcode(rcode)
    response.authority.extend(authority)
    response.answer.extend(answer)


class DnsServerUdpHandler(socketserver.BaseRequestHandler):
    """UDP request handler for DNS queries with health-aware responses."""

    def handle(self):
        """Handle incoming DNS query and send appropriate response."""
        data, sock = self.request

        try:
            query = dns.message.from_wire(data)
        except dns.exception.DNSException as ex:
            logging.warning("Failed to parse DNS query: %s", ex)
            return

        response = dns.message.make_response(query)
        response.flags |= dns.flags.AA  # Authoritative Answer

        if query.question:
            question = query.question[0]
            _update_response(
                response,
                question.name,
                question.rdtype,
                self.server.zone,
                self.server.zone_origins,
            )
        else:
            logging.warning("Received query without question section")
            response.set_rcode(dns.rcode.FORMERR)

        # Send the response back to the client
        sock.sendto(response.to_wire(), self.client_address)
