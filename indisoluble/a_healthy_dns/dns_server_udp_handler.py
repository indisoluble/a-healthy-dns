#!/usr/bin/env python3

"""UDP DNS server request handler.

Handles incoming DNS queries over UDP, processes them against the configured
zone, and returns appropriate DNS responses with authoritative answers.
"""

import logging
import socketserver

import dns.exception
import dns.flags
import dns.message
import dns.name
import dns.opcode
import dns.rcode
import dns.rdataclass
import dns.rdatatype
import dns.rrset
import dns.versioned
import dns.zone

from typing import List

from indisoluble.a_healthy_dns.records.zone_origins import ZoneOrigins


def _describe_parse_error(ex: dns.exception.DNSException) -> str:
    if isinstance(ex, dns.message.ShortHeader):
        return "packet is shorter than the 12-byte DNS header"
    if isinstance(ex, dns.message.TrailingJunk):
        return "packet has trailing bytes after a complete DNS message"
    if isinstance(ex, dns.name.BadLabelType):
        return "packet uses an unsupported DNS label encoding"
    if isinstance(ex, dns.name.BadPointer):
        return "packet contains an invalid DNS compression pointer"
    if isinstance(ex, dns.exception.FormError):
        return "packet does not match the DNS message wire format"

    return "packet could not be parsed as DNS wire format"


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
) -> None:
    relative_name = zone_origins.relativize(query_name)
    if relative_name is None:
        logging.warning(
            "Refused DNS query outside hosted or alias zones: qname=%s qtype=%s",
            query_name,
            dns.rdatatype.to_text(query_type),
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
            logging.warning(
                "DNS owner name is not present in the active zone; returning NXDOMAIN: qname=%s qtype=%s",
                query_name,
                dns.rdatatype.to_text(query_type),
            )
            rcode = dns.rcode.NXDOMAIN
            authority = _build_authority_with_apex_soa(zone, txn)

    response.set_rcode(rcode)
    response.authority.extend(authority)
    response.answer.extend(answer)


class DnsServerUdpHandler(socketserver.BaseRequestHandler):
    """UDP request handler for DNS queries with health-aware responses."""

    def handle(self) -> None:
        """Handle incoming DNS query and send appropriate response."""
        data, sock = self.request

        try:
            query = dns.message.from_wire(data)
        except dns.message.ShortHeader as ex:
            # Payload too short to contain a DNS header - no transaction ID to
            # recover, drop silently (RFC 1035 §4.1.1).
            logging.warning(
                "Ignoring malformed DNS packet: source=%s:%d bytes=%d problem=%s",
                self.client_address[0],
                self.client_address[1],
                len(data),
                _describe_parse_error(ex),
            )
            logging.debug("Stack trace for malformed DNS packet", exc_info=True)
            return
        except dns.exception.DNSException as ex:
            # Header is readable but message is malformed - recover the
            # transaction ID and respond with FORMERR (RFC 1035 §4.1.1).
            msg_id = int.from_bytes(data[:2], "big")
            logging.warning(
                "Malformed DNS query; replying FORMERR: source=%s:%d id=%d bytes=%d problem=%s",
                self.client_address[0],
                self.client_address[1],
                msg_id,
                len(data),
                _describe_parse_error(ex),
            )
            logging.debug("Stack trace for malformed DNS query", exc_info=True)

            formerr = dns.message.Message(id=msg_id)
            formerr.flags = dns.flags.QR
            formerr.set_rcode(dns.rcode.FORMERR)

            sock.sendto(formerr.to_wire(), self.client_address)
            return

        try:
            response = dns.message.make_response(query)
        except dns.exception.FormError as ex:
            if query.flags & dns.flags.QR:
                logging.warning(
                    "Ignoring DNS response packet received on query socket: source=%s:%d id=%d bytes=%d problem=response flag is set",
                    self.client_address[0],
                    self.client_address[1],
                    query.id,
                    len(data),
                )
            else:
                logging.warning(
                    "Unable to build DNS response; dropping packet: source=%s:%d id=%d bytes=%d problem=%s",
                    self.client_address[0],
                    self.client_address[1],
                    query.id,
                    len(data),
                    ex,
                )
            logging.debug(
                "Stack trace for DNS response construction failure", exc_info=True
            )
            return

        response.flags |= dns.flags.AA  # Authoritative Answer

        if query.opcode() != dns.opcode.QUERY:
            logging.warning(
                "DNS query uses unsupported opcode; returning NOTIMP: source=%s:%d id=%d opcode=%s expected=QUERY",
                self.client_address[0],
                self.client_address[1],
                query.id,
                dns.opcode.to_text(query.opcode()),
            )
            response.set_rcode(dns.rcode.NOTIMP)
        elif len(query.question) != 1:
            logging.warning(
                "DNS query has invalid question count; returning FORMERR: source=%s:%d id=%d qdcount=%d expected=1",
                self.client_address[0],
                self.client_address[1],
                query.id,
                len(query.question),
            )
            response.set_rcode(dns.rcode.FORMERR)
        else:
            question = query.question[0]
            if question.rdclass != dns.rdataclass.IN:
                logging.warning(
                    "Refused DNS query with unsupported class: source=%s:%d id=%d qname=%s qtype=%s qclass=%s expected=IN",
                    self.client_address[0],
                    self.client_address[1],
                    query.id,
                    question.name,
                    dns.rdatatype.to_text(question.rdtype),
                    dns.rdataclass.to_text(question.rdclass),
                )
                response.set_rcode(dns.rcode.REFUSED)
            else:
                _update_response(
                    response,
                    question.name,
                    question.rdtype,
                    self.server.zone,
                    self.server.zone_origins,
                )

        # Send the response back to the client
        sock.sendto(response.to_wire(), self.client_address)
