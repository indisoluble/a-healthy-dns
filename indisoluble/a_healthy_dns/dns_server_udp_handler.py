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
import dns.node
import dns.opcode
import dns.rcode
import dns.rdata
import dns.rdataclass
import dns.rdataset
import dns.rdatatype
import dns.rrset
import dns.zone

from typing import List, NamedTuple, Optional, Tuple

from indisoluble.a_healthy_dns.records.zone_origins import ZoneOrigins


class _ApexSOA(NamedTuple):
    rdata: dns.rdata.Rdata
    ttl: int


class _ResponseOutcome(NamedTuple):
    rcode: int
    is_authoritative: bool
    answer: Tuple[dns.rrset.RRset, ...]
    authority: Tuple[dns.rrset.RRset, ...]


_CLASSIC_UDP_PAYLOAD_SIZE = 512
_DNS_HEADER_LENGTH = 12
_DNS_OPCODE_MASK = 0x7800
_DNS_TRAFFIC_JUNK = "dns_traffic=junk"
_DNS_TRAFFIC_NOISE = "dns_traffic=noise"
_DNS_TRAFFIC_NORMAL = "dns_traffic=normal"
_DNS_TRAFFIC_SUSPICIOUS = "dns_traffic=suspicious"
_PARSE_ERROR_DESCRIPTIONS = {
    dns.exception.FormError: "packet does not match the DNS message wire format",
    dns.message.ShortHeader: "packet is shorter than the 12-byte DNS header",
    dns.message.TrailingJunk: "packet has trailing bytes after a complete DNS message",
    dns.name.BadLabelType: "packet uses an unsupported DNS label encoding",
    dns.name.BadPointer: "packet contains an invalid DNS compression pointer",
}
_RFC8482_HINFO_CPU = "RFC8482"
_RFC8482_HINFO_OS = ""


class _DropQuery(Exception):
    """Stop processing the current DNS request without sending a response."""


class _QuestionRejected(Exception):
    """Stop question handling and set the response rcode."""

    def __init__(self, rcode: int) -> None:
        super().__init__(dns.rcode.to_text(rcode))
        self.rcode = rcode


class _RespondWith(Exception):
    """Stop request processing and send the provided DNS response."""

    def __init__(self, response: dns.message.Message) -> None:
        super().__init__("respond with DNS message")
        self.response = response


def _apply_response_outcome(
    response: dns.message.Message, outcome: _ResponseOutcome
) -> None:
    if outcome.is_authoritative:
        response.flags |= dns.flags.AA  # Authoritative Answer

    response.set_rcode(outcome.rcode)
    response.authority.extend(outcome.authority)
    response.answer.extend(outcome.answer)


def _build_answer(
    query_name: dns.name.Name, rdataset: dns.rdataset.Rdataset
) -> List[dns.rrset.RRset]:
    rrset = dns.rrset.RRset(query_name, rdataset.rdclass, rdataset.rdtype)
    rrset.ttl = rdataset.ttl
    for rdata in rdataset:
        rrset.add(rdata)

    return [rrset]


def _build_apex_soa(
    txn: dns.zone.Transaction,
) -> Optional[_ApexSOA]:
    soa_rdataset = txn.get(dns.name.empty, dns.rdatatype.SOA)
    if soa_rdataset is None:
        return None

    soa_rdata = next(iter(soa_rdataset), None)
    if soa_rdata is None:
        return None

    return _ApexSOA(rdata=soa_rdata, ttl=min(soa_rdataset.ttl, soa_rdata.minimum))


def _build_authority_with_apex_soa(
    apex_name: dns.name.Name, txn: dns.zone.Transaction
) -> List[dns.rrset.RRset]:
    soa_authority = _build_apex_soa(txn)
    if soa_authority is None:
        return []

    soa_rrset = dns.rrset.RRset(apex_name, dns.rdataclass.IN, dns.rdatatype.SOA)
    soa_rrset.ttl = soa_authority.ttl
    soa_rrset.add(soa_authority.rdata)

    return [soa_rrset]


def _build_rfc8482_hinfo_answer(
    query_name: dns.name.Name, txn: dns.zone.Transaction
) -> List[dns.rrset.RRset]:
    soa_authority = _build_apex_soa(txn)
    ttl = soa_authority.ttl if soa_authority is not None else 0

    rdataset = dns.rdataset.from_text(
        dns.rdataclass.IN,
        dns.rdatatype.HINFO,
        ttl,
        f'"{_RFC8482_HINFO_CPU}" "{_RFC8482_HINFO_OS}"',
    )

    return _build_answer(query_name, rdataset)


def _classify_empty_non_terminal_query(
    question: dns.rrset.RRset,
    query_id: int,
    origin_name: dns.name.Name,
    txn: dns.zone.Transaction,
    client_address: Tuple[str, int],
) -> _ResponseOutcome:
    if question.rdtype == dns.rdatatype.ANY:
        return _make_answer_outcome(
            question,
            query_id,
            _build_rfc8482_hinfo_answer(question.name, txn),
            "Answered RFC 8482 ANY query for empty non-terminal with synthesized HINFO",
            client_address,
        )

    return _make_soa_authority_outcome(
        question,
        query_id,
        origin_name,
        txn,
        dns.rcode.NOERROR,
        "DNS owner name is an empty non-terminal in the active zone; returning NODATA",
        client_address,
    )


def _classify_existing_node_query(
    question: dns.rrset.RRset,
    query_id: int,
    origin_name: dns.name.Name,
    txn: dns.zone.Transaction,
    node: dns.node.Node,
    zone_rdclass: dns.rdataclass.RdataClass,
    client_address: Tuple[str, int],
) -> _ResponseOutcome:
    query_name = question.name
    query_type = question.rdtype

    if query_type == dns.rdatatype.ANY:
        return _make_answer_outcome(
            question,
            query_id,
            _build_rfc8482_hinfo_answer(query_name, txn),
            "Answered RFC 8482 ANY query with synthesized HINFO",
            client_address,
        )

    rdataset = node.get_rdataset(zone_rdclass, query_type)
    if rdataset:
        return _make_answer_outcome(
            question,
            query_id,
            _build_answer(query_name, rdataset),
            "Answered DNS query from hosted zone",
            client_address,
        )

    return _make_soa_authority_outcome(
        question,
        query_id,
        origin_name,
        txn,
        dns.rcode.NOERROR,
        "DNS owner name exists but has no requested records; returning NODATA",
        client_address,
    )


def _classify_query(
    question: dns.rrset.RRset,
    query_id: int,
    zone: dns.zone.Zone,
    zone_origins: ZoneOrigins,
    client_address: Tuple[str, int],
) -> _ResponseOutcome:
    query_name = question.name

    origin_name = zone_origins.origin_for(query_name)
    if origin_name is None:
        return _make_refused_outcome(question, query_id, client_address)

    relative_name = zone_origins.relativize(query_name)

    with zone.reader() as txn:
        node = txn.get_node(relative_name)
        if node:
            return _classify_existing_node_query(
                question,
                query_id,
                origin_name,
                txn,
                node,
                zone.rdclass,
                client_address,
            )

        if _is_empty_non_terminal(relative_name, txn):
            return _classify_empty_non_terminal_query(
                question, query_id, origin_name, txn, client_address
            )

        return _make_soa_authority_outcome(
            question,
            query_id,
            origin_name,
            txn,
            dns.rcode.NXDOMAIN,
            "DNS owner name is not present in the active zone; returning NXDOMAIN",
            client_address,
        )


def _describe_parse_error(ex: dns.exception.DNSException) -> str:
    return _PARSE_ERROR_DESCRIPTIONS.get(type(ex), "packet could not be parsed as DNS wire format")


def _drop_inbound_response_packet(
    data: bytes, client_address: Tuple[str, int]
) -> bool:
    if len(data) >= _DNS_HEADER_LENGTH:
        header_flags = int.from_bytes(data[2:4], "big")
        if header_flags & dns.flags.QR:
            logging.warning(
                "%s Ignoring DNS response packet received on query socket: source=%s:%d id=%d bytes=%d problem=response flag is set",
                _DNS_TRAFFIC_SUSPICIOUS,
                client_address[0],
                client_address[1],
                int.from_bytes(data[:2], "big"),
                len(data),
            )
            return True

    return False


def _is_empty_non_terminal(
    query_name: dns.name.Name, txn: dns.zone.Transaction
) -> bool:
    """Return True when *query_name* exists only via descendants (empty non-terminal).

    See `docs/RFC-conformance.md#3-level-1-protocol-target` for the
    empty non-terminal response contract (RFC 4592 / RFC 8020).
    """

    return any(name.is_subdomain(query_name) for name in txn.iterate_names())


def _log_query(
    question: dns.rrset.RRset,
    query_id: int,
    traffic_marker: str,
    description: str,
    client_address: Tuple[str, int],
    answer_count: Optional[int] = None,
) -> None:
    message = "%s %s: source=%s:%d id=%d qname=%s qtype=%s"
    args = (
        traffic_marker,
        description,
        client_address[0],
        client_address[1],
        query_id,
        question.name,
        dns.rdatatype.to_text(question.rdtype),
    )
    if answer_count is not None:
        message += " answers=%d"
        args = args + (answer_count,)

    logging.info(message, *args)


def _make_answer_outcome(
    question: dns.rrset.RRset,
    query_id: int,
    answer: List[dns.rrset.RRset],
    description: str,
    client_address: Tuple[str, int],
) -> _ResponseOutcome:
    _log_query(
        question,
        query_id,
        _DNS_TRAFFIC_NORMAL,
        description,
        client_address,
        answer_count=len(answer),
    )
    return _make_response_outcome(
        rcode=dns.rcode.NOERROR,
        is_authoritative=True,
        answer=answer,
    )


def _make_formerr_response_from_header(data: bytes) -> dns.message.Message:
    request_flags = int.from_bytes(data[2:4], "big")
    formerr = dns.message.Message(id=int.from_bytes(data[:2], "big"))
    formerr.flags = dns.flags.QR | (request_flags & (_DNS_OPCODE_MASK | dns.flags.RD))
    formerr.set_rcode(dns.rcode.FORMERR)

    return formerr


def _make_refused_outcome(
    question: dns.rrset.RRset,
    query_id: int,
    client_address: Tuple[str, int],
) -> _ResponseOutcome:
    _log_query(
        question,
        query_id,
        _DNS_TRAFFIC_NOISE,
        "Refused DNS query outside hosted or alias zones",
        client_address,
    )
    return _make_response_outcome(
        rcode=dns.rcode.REFUSED,
        is_authoritative=False,
    )


def _make_response_message(
    query: dns.message.Message,
    data_length: int,
    client_address: Tuple[str, int],
) -> Optional[dns.message.Message]:
    try:
        return dns.message.make_response(query)
    except dns.exception.FormError as ex:
        logging.info(
            "%s Unable to build DNS response; dropping packet: source=%s:%d id=%d bytes=%d problem=%s",
            _DNS_TRAFFIC_JUNK,
            client_address[0],
            client_address[1],
            query.id,
            data_length,
            ex,
        )
        logging.debug(
            "%s Stack trace for DNS response construction failure: source=%s:%d id=%d bytes=%d",
            _DNS_TRAFFIC_JUNK,
            client_address[0],
            client_address[1],
            query.id,
            data_length,
            exc_info=True,
        )
        return None


def _make_response_outcome(
    rcode: int,
    is_authoritative: bool,
    answer: Optional[List[dns.rrset.RRset]] = None,
    authority: Optional[List[dns.rrset.RRset]] = None,
) -> _ResponseOutcome:
    return _ResponseOutcome(
        rcode=rcode,
        is_authoritative=is_authoritative,
        answer=tuple(answer or ()),
        authority=tuple(authority or ()),
    )


def _make_soa_authority_outcome(
    question: dns.rrset.RRset,
    query_id: int,
    origin_name: dns.name.Name,
    txn: dns.zone.Transaction,
    rcode: int,
    description: str,
    client_address: Tuple[str, int],
) -> _ResponseOutcome:
    _log_query(
        question,
        query_id,
        _DNS_TRAFFIC_NORMAL,
        description,
        client_address,
    )
    return _make_response_outcome(
        rcode=rcode,
        is_authoritative=True,
        authority=_build_authority_with_apex_soa(origin_name, txn),
    )


def _parse_query(
    data: bytes, client_address: Tuple[str, int]
) -> dns.message.Message:
    try:
        return dns.message.from_wire(data)
    except dns.message.ShortHeader as ex:
        # Payload too short to contain a DNS header - no transaction ID to
        # recover, drop without a DNS response (RFC 1035 §4.1.1).
        logging.info(
            "%s Ignoring malformed DNS packet: source=%s:%d bytes=%d problem=%s",
            _DNS_TRAFFIC_JUNK,
            client_address[0],
            client_address[1],
            len(data),
            _describe_parse_error(ex),
        )
        logging.debug(
            "%s Stack trace for malformed DNS packet: source=%s:%d bytes=%d",
            _DNS_TRAFFIC_JUNK,
            client_address[0],
            client_address[1],
            len(data),
            exc_info=True,
        )
        raise _DropQuery from ex
    except dns.exception.DNSException as ex:
        # Header is readable but message is malformed - recover the
        # transaction ID and respond with FORMERR (RFC 1035 §4.1.1).
        msg_id = int.from_bytes(data[:2], "big")
        logging.info(
            "%s Malformed DNS query; replying FORMERR: source=%s:%d id=%d bytes=%d problem=%s",
            _DNS_TRAFFIC_JUNK,
            client_address[0],
            client_address[1],
            msg_id,
            len(data),
            _describe_parse_error(ex),
        )
        logging.debug(
            "%s Stack trace for malformed DNS query: source=%s:%d id=%d bytes=%d",
            _DNS_TRAFFIC_JUNK,
            client_address[0],
            client_address[1],
            msg_id,
            len(data),
            exc_info=True,
        )

        raise _RespondWith(_make_formerr_response_from_header(data)) from ex


def _response_to_udp_wire(response: dns.message.Message) -> bytes:
    return response.to_wire(max_size=_CLASSIC_UDP_PAYLOAD_SIZE, prefer_truncation=True)


def _validated_question(
    query: dns.message.Message, client_address: Tuple[str, int]
) -> dns.rrset.RRset:
    if query.opcode() != dns.opcode.QUERY:
        logging.warning(
            "%s DNS query uses unsupported opcode; returning NOTIMP: source=%s:%d id=%d opcode=%s expected=QUERY",
            _DNS_TRAFFIC_SUSPICIOUS,
            client_address[0],
            client_address[1],
            query.id,
            dns.opcode.to_text(query.opcode()),
        )
        raise _QuestionRejected(dns.rcode.NOTIMP)

    if len(query.question) != 1:
        logging.info(
            "%s DNS query has invalid question count; returning FORMERR: source=%s:%d id=%d qdcount=%d expected=1",
            _DNS_TRAFFIC_JUNK,
            client_address[0],
            client_address[1],
            query.id,
            len(query.question),
        )
        raise _QuestionRejected(dns.rcode.FORMERR)

    question = query.question[0]
    if question.rdclass != dns.rdataclass.IN:
        logging.info(
            "%s Refused DNS query with unsupported class: source=%s:%d id=%d qname=%s qtype=%s qclass=%s expected=IN",
            _DNS_TRAFFIC_NOISE,
            client_address[0],
            client_address[1],
            query.id,
            question.name,
            dns.rdatatype.to_text(question.rdtype),
            dns.rdataclass.to_text(question.rdclass),
        )
        raise _QuestionRejected(dns.rcode.REFUSED)

    return question


class DnsServerUdpHandler(socketserver.BaseRequestHandler):
    """UDP request handler for DNS queries with health-aware responses."""

    def _update_response(
        self,
        response: dns.message.Message,
        question: dns.rrset.RRset,
        query_id: int,
    ) -> None:
        outcome = _classify_query(
            question,
            query_id,
            self.server.zone,
            self.server.zone_origins,
            self.client_address,
        )
        _apply_response_outcome(response, outcome)

    # Implements socketserver.BaseRequestHandler inheritance contract.
    def handle(self) -> None:
        """Handle incoming DNS query and send appropriate response."""
        data, sock = self.request

        if _drop_inbound_response_packet(data, self.client_address):
            return

        try:
            query = _parse_query(data, self.client_address)
        except _DropQuery:
            return
        except _RespondWith as ex:
            sock.sendto(_response_to_udp_wire(ex.response), self.client_address)
            return

        response = _make_response_message(query, len(data), self.client_address)
        if response is None:
            return

        try:
            question = _validated_question(query, self.client_address)
        except _QuestionRejected as ex:
            response.set_rcode(ex.rcode)
        else:
            self._update_response(response, question, query.id)

        sock.sendto(_response_to_udp_wire(response), self.client_address)
