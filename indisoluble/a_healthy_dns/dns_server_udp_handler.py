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


class _ApexSOA(NamedTuple):
    rdata: dns.rdata.Rdata
    ttl: int


class _QueryParseResult(NamedTuple):
    success: bool
    query: Optional[dns.message.Message]
    response: Optional[dns.message.Message]


class _QuestionValidationResult(NamedTuple):
    question: Optional[dns.rrset.RRset]
    rcode: Optional[int]


class _LogEvent(NamedTuple):
    level: int
    message: str
    args: Tuple[object, ...]


class _ResponseOutcome(NamedTuple):
    rcode: int
    is_authoritative: bool
    answer: Tuple[dns.rrset.RRset, ...]
    authority: Tuple[dns.rrset.RRset, ...]
    log_event: Optional[_LogEvent]


_DNS_HEADER_LENGTH = 12
_DNS_OPCODE_MASK = 0x7800
_CLASSIC_UDP_PAYLOAD_SIZE = 512
_DNS_TRAFFIC_JUNK = "dns_traffic=junk"
_DNS_TRAFFIC_NOISE = "dns_traffic=noise"
_DNS_TRAFFIC_NORMAL = "dns_traffic=normal"
_DNS_TRAFFIC_SUSPICIOUS = "dns_traffic=suspicious"
_RFC8482_HINFO_CPU = "RFC8482"
_RFC8482_HINFO_OS = ""


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


def _build_answer(
    query_name: dns.name.Name, rdataset: dns.rdataset.Rdataset
) -> List[dns.rrset.RRset]:
    rrset = dns.rrset.RRset(query_name, rdataset.rdclass, rdataset.rdtype)
    rrset.ttl = rdataset.ttl
    for rdata in rdataset:
        rrset.add(rdata)

    return [rrset]


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


def _is_empty_non_terminal(
    query_name: dns.name.Name, txn: dns.zone.Transaction
) -> bool:
    """Return True when *query_name* exists only via descendants (empty non-terminal).

    See `docs/RFC-conformance.md#3-level-1-protocol-target` for the
    empty non-terminal response contract (RFC 4592 / RFC 8020).
    """

    return any(name.is_subdomain(query_name) for name in txn.iterate_names())


def _make_formerr_response_from_header(data: bytes) -> dns.message.Message:
    request_flags = int.from_bytes(data[2:4], "big")
    formerr = dns.message.Message(id=int.from_bytes(data[:2], "big"))
    formerr.flags = dns.flags.QR | (request_flags & (_DNS_OPCODE_MASK | dns.flags.RD))
    formerr.set_rcode(dns.rcode.FORMERR)

    return formerr


def _response_to_udp_wire(response: dns.message.Message) -> bytes:
    return response.to_wire(max_size=_CLASSIC_UDP_PAYLOAD_SIZE, prefer_truncation=True)


class DnsServerUdpHandler(socketserver.BaseRequestHandler):
    """UDP request handler for DNS queries with health-aware responses."""

    def _drop_inbound_response_packet(self, data: bytes) -> bool:
        if len(data) >= _DNS_HEADER_LENGTH:
            header_flags = int.from_bytes(data[2:4], "big")
            if header_flags & dns.flags.QR:
                logging.warning(
                    "%s Ignoring DNS response packet received on query socket: source=%s:%d id=%d bytes=%d problem=response flag is set",
                    _DNS_TRAFFIC_SUSPICIOUS,
                    self.client_address[0],
                    self.client_address[1],
                    int.from_bytes(data[:2], "big"),
                    len(data),
                )
                return True

        return False

    def _parse_query(self, data: bytes) -> _QueryParseResult:
        try:
            return _QueryParseResult(
                success=True, query=dns.message.from_wire(data), response=None
            )
        except dns.message.ShortHeader as ex:
            # Payload too short to contain a DNS header - no transaction ID to
            # recover, drop without a DNS response (RFC 1035 §4.1.1).
            logging.info(
                "%s Ignoring malformed DNS packet: source=%s:%d bytes=%d problem=%s",
                _DNS_TRAFFIC_JUNK,
                self.client_address[0],
                self.client_address[1],
                len(data),
                _describe_parse_error(ex),
            )
            logging.debug(
                "%s Stack trace for malformed DNS packet: source=%s:%d bytes=%d",
                _DNS_TRAFFIC_JUNK,
                self.client_address[0],
                self.client_address[1],
                len(data),
                exc_info=True,
            )
            return _QueryParseResult(success=False, query=None, response=None)
        except dns.exception.DNSException as ex:
            # Header is readable but message is malformed - recover the
            # transaction ID and respond with FORMERR (RFC 1035 §4.1.1).
            msg_id = int.from_bytes(data[:2], "big")
            logging.info(
                "%s Malformed DNS query; replying FORMERR: source=%s:%d id=%d bytes=%d problem=%s",
                _DNS_TRAFFIC_JUNK,
                self.client_address[0],
                self.client_address[1],
                msg_id,
                len(data),
                _describe_parse_error(ex),
            )
            logging.debug(
                "%s Stack trace for malformed DNS query: source=%s:%d id=%d bytes=%d",
                _DNS_TRAFFIC_JUNK,
                self.client_address[0],
                self.client_address[1],
                msg_id,
                len(data),
                exc_info=True,
            )

            return _QueryParseResult(
                success=False,
                query=None,
                response=_make_formerr_response_from_header(data),
            )

    def _make_response(
        self, query: dns.message.Message, data_length: int
    ) -> Optional[dns.message.Message]:
        try:
            return dns.message.make_response(query)
        except dns.exception.FormError as ex:
            logging.info(
                "%s Unable to build DNS response; dropping packet: source=%s:%d id=%d bytes=%d problem=%s",
                _DNS_TRAFFIC_JUNK,
                self.client_address[0],
                self.client_address[1],
                query.id,
                data_length,
                ex,
            )
            logging.debug(
                "%s Stack trace for DNS response construction failure: source=%s:%d id=%d bytes=%d",
                _DNS_TRAFFIC_JUNK,
                self.client_address[0],
                self.client_address[1],
                query.id,
                data_length,
                exc_info=True,
            )
            return None

    def _validate_question(
        self, query: dns.message.Message
    ) -> _QuestionValidationResult:
        if query.opcode() != dns.opcode.QUERY:
            logging.warning(
                "%s DNS query uses unsupported opcode; returning NOTIMP: source=%s:%d id=%d opcode=%s expected=QUERY",
                _DNS_TRAFFIC_SUSPICIOUS,
                self.client_address[0],
                self.client_address[1],
                query.id,
                dns.opcode.to_text(query.opcode()),
            )
            return _QuestionValidationResult(question=None, rcode=dns.rcode.NOTIMP)

        if len(query.question) != 1:
            logging.info(
                "%s DNS query has invalid question count; returning FORMERR: source=%s:%d id=%d qdcount=%d expected=1",
                _DNS_TRAFFIC_JUNK,
                self.client_address[0],
                self.client_address[1],
                query.id,
                len(query.question),
            )
            return _QuestionValidationResult(question=None, rcode=dns.rcode.FORMERR)

        question = query.question[0]
        if question.rdclass != dns.rdataclass.IN:
            logging.info(
                "%s Refused DNS query with unsupported class: source=%s:%d id=%d qname=%s qtype=%s qclass=%s expected=IN",
                _DNS_TRAFFIC_NOISE,
                self.client_address[0],
                self.client_address[1],
                query.id,
                question.name,
                dns.rdatatype.to_text(question.rdtype),
                dns.rdataclass.to_text(question.rdclass),
            )
            return _QuestionValidationResult(question=None, rcode=dns.rcode.REFUSED)

        return _QuestionValidationResult(question=question, rcode=None)

    def _make_query_log_event(
        self,
        question: dns.rrset.RRset,
        query_id: int,
        traffic_marker: str,
        description: str,
        answer_count: Optional[int] = None,
    ) -> _LogEvent:
        message = f"%s {description}: source=%s:%d id=%d qname=%s qtype=%s"
        args = (
            traffic_marker,
            self.client_address[0],
            self.client_address[1],
            query_id,
            question.name,
            dns.rdatatype.to_text(question.rdtype),
        )
        if answer_count is None:
            return _LogEvent(level=logging.INFO, message=message, args=args)

        return _LogEvent(
            level=logging.INFO,
            message=f"{message} answers=%d",
            args=args + (answer_count,),
        )

    def _make_response_outcome(
        self,
        rcode: int,
        is_authoritative: bool,
        log_event: _LogEvent,
        answer: Optional[List[dns.rrset.RRset]] = None,
        authority: Optional[List[dns.rrset.RRset]] = None,
    ) -> _ResponseOutcome:
        return _ResponseOutcome(
            rcode=rcode,
            is_authoritative=is_authoritative,
            answer=tuple(answer or ()),
            authority=tuple(authority or ()),
            log_event=log_event,
        )

    def _make_refused_outcome(
        self, question: dns.rrset.RRset, query_id: int
    ) -> _ResponseOutcome:
        return self._make_response_outcome(
            rcode=dns.rcode.REFUSED,
            is_authoritative=False,
            log_event=self._make_query_log_event(
                question,
                query_id,
                _DNS_TRAFFIC_NOISE,
                "Refused DNS query outside hosted or alias zones",
            ),
        )

    def _make_answer_outcome(
        self,
        question: dns.rrset.RRset,
        query_id: int,
        answer: List[dns.rrset.RRset],
        description: str,
    ) -> _ResponseOutcome:
        return self._make_response_outcome(
            rcode=dns.rcode.NOERROR,
            is_authoritative=True,
            answer=answer,
            log_event=self._make_query_log_event(
                question,
                query_id,
                _DNS_TRAFFIC_NORMAL,
                description,
                answer_count=len(answer),
            ),
        )

    def _make_soa_authority_outcome(
        self,
        question: dns.rrset.RRset,
        query_id: int,
        origin_name: dns.name.Name,
        txn: dns.zone.Transaction,
        rcode: int,
        description: str,
    ) -> _ResponseOutcome:
        return self._make_response_outcome(
            rcode=rcode,
            is_authoritative=True,
            authority=_build_authority_with_apex_soa(origin_name, txn),
            log_event=self._make_query_log_event(
                question,
                query_id,
                _DNS_TRAFFIC_NORMAL,
                description,
            ),
        )

    def _classify_existing_node_query(
        self,
        question: dns.rrset.RRset,
        query_id: int,
        origin_name: dns.name.Name,
        txn: dns.zone.Transaction,
        node: dns.node.Node,
    ) -> _ResponseOutcome:
        query_name = question.name
        query_type = question.rdtype
        zone = self.server.zone

        if query_type == dns.rdatatype.ANY:
            return self._make_answer_outcome(
                question,
                query_id,
                _build_rfc8482_hinfo_answer(query_name, txn),
                "Answered RFC 8482 ANY query with synthesized HINFO",
            )

        rdataset = node.get_rdataset(zone.rdclass, query_type)
        if rdataset:
            return self._make_answer_outcome(
                question,
                query_id,
                _build_answer(query_name, rdataset),
                "Answered DNS query from hosted zone",
            )

        return self._make_soa_authority_outcome(
            question,
            query_id,
            origin_name,
            txn,
            dns.rcode.NOERROR,
            "DNS owner name exists but has no requested records; returning NODATA",
        )

    def _classify_empty_non_terminal_query(
        self,
        question: dns.rrset.RRset,
        query_id: int,
        origin_name: dns.name.Name,
        txn: dns.zone.Transaction,
    ) -> _ResponseOutcome:
        if question.rdtype == dns.rdatatype.ANY:
            return self._make_answer_outcome(
                question,
                query_id,
                _build_rfc8482_hinfo_answer(question.name, txn),
                "Answered RFC 8482 ANY query for empty non-terminal with synthesized HINFO",
            )

        return self._make_soa_authority_outcome(
            question,
            query_id,
            origin_name,
            txn,
            dns.rcode.NOERROR,
            "DNS owner name is an empty non-terminal in the active zone; returning NODATA",
        )

    def _classify_query(
        self,
        question: dns.rrset.RRset,
        query_id: int,
    ) -> _ResponseOutcome:
        query_name = question.name
        zone = self.server.zone
        zone_origins = self.server.zone_origins

        origin_name = zone_origins.origin_for(query_name)
        if origin_name is None:
            return self._make_refused_outcome(question, query_id)

        relative_name = zone_origins.relativize(query_name)

        with zone.reader() as txn:
            node = txn.get_node(relative_name)
            if node:
                return self._classify_existing_node_query(
                    question, query_id, origin_name, txn, node
                )

            if _is_empty_non_terminal(relative_name, txn):
                return self._classify_empty_non_terminal_query(
                    question, query_id, origin_name, txn
                )

            return self._make_soa_authority_outcome(
                question,
                query_id,
                origin_name,
                txn,
                dns.rcode.NXDOMAIN,
                "DNS owner name is not present in the active zone; returning NXDOMAIN",
            )

    def _log_response_outcome(self, outcome: _ResponseOutcome) -> None:
        if outcome.log_event is not None:
            logging.log(
                outcome.log_event.level,
                outcome.log_event.message,
                *outcome.log_event.args,
            )

    def _apply_response_outcome(
        self, response: dns.message.Message, outcome: _ResponseOutcome
    ) -> None:
        if outcome.is_authoritative:
            response.flags |= dns.flags.AA  # Authoritative Answer

        response.set_rcode(outcome.rcode)
        response.authority.extend(outcome.authority)
        response.answer.extend(outcome.answer)

    def _update_response(
        self,
        response: dns.message.Message,
        question: dns.rrset.RRset,
        query_id: int,
    ) -> None:
        outcome = self._classify_query(question, query_id)
        self._log_response_outcome(outcome)
        self._apply_response_outcome(response, outcome)

    # Implements socketserver.BaseRequestHandler inheritance contract.
    def handle(self) -> None:
        """Handle incoming DNS query and send appropriate response."""
        data, sock = self.request

        if self._drop_inbound_response_packet(data):
            return

        parse_result = self._parse_query(data)
        if not parse_result.success:
            if parse_result.response is not None:
                sock.sendto(
                    _response_to_udp_wire(parse_result.response), self.client_address
                )
            return

        query = parse_result.query
        if query is None:
            return

        response = self._make_response(query, len(data))
        if response is None:
            return

        question_result = self._validate_question(query)
        if question_result.rcode is not None:
            response.set_rcode(question_result.rcode)
        elif question_result.question is not None:
            self._update_response(response, question_result.question, query.id)

        sock.sendto(_response_to_udp_wire(response), self.client_address)
