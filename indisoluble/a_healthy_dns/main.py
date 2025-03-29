#!/usr/bin/env python3

import argparse
import json
import logging
import socketserver
import time

import dns.message
import dns.rdatatype
import dns.rrset


class DNSUDPHandler(socketserver.BaseRequestHandler):
    def _response_for_a_record(self, response, qname):
        if qname not in self.server.resolutions:
            logging.warning("Received query for unknown domain: %s", qname)
            response.set_rcode(dns.rcode.NXDOMAIN)
            return

        ips = self.server.resolutions[qname]

        rrset = dns.rrset.from_text(
            qname, self.server.ttl_a, dns.rdataclass.IN, dns.rdatatype.A, *ips
        )
        response.answer.append(rrset)
        logging.debug("Responded to A query for %s with %s", qname, ips)

    def _response_for_ns_record(self, response, qname):
        if qname != self.server.hosted_zone:
            logging.warning("Received NS query for unknown zone: %s", qname)
            response.set_rcode(dns.rcode.NXDOMAIN)
            return

        rrset = dns.rrset.from_text(
            qname,
            self.server.ttl_ns,
            dns.rdataclass.IN,
            dns.rdatatype.NS,
            *self.server.name_servers,
        )
        response.answer.append(rrset)
        logging.debug(
            "Responded to NS query for %s with %s", qname, self.server.name_servers
        )

    def _response_for_soa_record(self, response, qname):
        if qname != self.server.hosted_zone:
            logging.warning("Received SOA query for unknown zone: %s", qname)
            response.set_rcode(dns.rcode.NXDOMAIN)
            return

        rrset = dns.rrset.from_text(
            qname,
            self.server.ttl_a,
            dns.rdataclass.IN,
            dns.rdatatype.SOA,
            " ".join(
                [
                    self.server.primary_name_server,
                    f"hostmaster.{self.server.hosted_zone}",
                    str(self.server.soa_serial),
                    str(self.server.soa_refresh),
                    str(self.server.soa_retry),
                    str(self.server.soa_expire),
                    str(self.server.ttl_a),
                ]
            ),
        )
        response.answer.append(rrset)
        logging.debug("Responded to SOA query for %s", qname)

    def handle(self):
        data, sock = self.request

        try:
            query = dns.message.from_wire(data)
        except dns.exception.DNSException as ex:
            logging.exception("Failed to parse DNS query: %s", ex)
            return

        response = dns.message.make_response(query)
        response.flags |= dns.flags.AA  # Authoritative Answer

        if not query.question:
            logging.warning("Received query without question section")
            response.set_rcode(dns.rcode.FORMERR)
        else:
            question = query.question[0]

            if question.rdtype == dns.rdatatype.A:
                self._response_for_a_record(response, question.name.to_text())
            elif question.rdtype == dns.rdatatype.NS:
                self._response_for_ns_record(response, question.name.to_text())
            elif question.rdtype == dns.rdatatype.SOA:
                self._response_for_soa_record(response, question.name.to_text())
            else:
                logging.warning("Received unsupported query type: %s", question.rdtype)
                response.set_rcode(dns.rcode.NOTIMP)

        sock.sendto(response.to_wire(), self.client_address)


def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="DNS server")
    parser.add_argument(
        "--hosted-zone", type=str, required=True, help="Hosted zone name"
    )
    parser.add_argument(
        "--name-servers",
        type=str,
        required=True,
        help="List of name servers as JSON string (ex. [fqdn1, fqdn2, ...])",
    )
    parser.add_argument(
        "--zone-resolutions",
        type=str,
        required=True,
        help="List of subdomains with their respectives IPs as JSON string (ex. {sd1: [ip1, ip2, ...], ...})",
    )
    parser.add_argument(
        "--port", type=int, default=5053, help="DNS server port (default: 5053)"
    )
    parser.add_argument(
        "--ttl-a",
        type=int,
        default=60,
        help="TTL in seconds for A records (default: 60)",
    )
    parser.add_argument(
        "--ttl-ns",
        type=int,
        default=86400,
        help="TTL in seconds for NS records (default: 86400)",
    )
    parser.add_argument(
        "--soa-refresh",
        type=int,
        default=3600,
        help="SOA refresh time in seconds (default: 3600)",
    )
    parser.add_argument(
        "--soa-retry",
        type=int,
        default=600,
        help="SOA retry time in seconds (default: 600)",
    )
    parser.add_argument(
        "--soa-expire",
        type=int,
        default=86400,
        help="SOA expire time in seconds (default: 86400)",
    )
    parser.add_argument(
        "--log-level", type=str, default="info", help="Logging level (default: info)"
    )
    args = parser.parse_args()

    # Set up logging
    numeric_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(levelname)s - %(module)s.%(funcName)s - %(message)s",
    )

    # Parse name servers
    try:
        raw_name_servers = json.loads(args.name_servers)
    except json.JSONDecodeError as ex:
        logging.exception("Failed to parse name servers: %s", ex)
        return

    name_servers = [f"{ns}." for ns in raw_name_servers]

    # Parse resolutions
    try:
        raw_resolutions = json.loads(args.zone_resolutions)
    except json.JSONDecodeError as ex:
        logging.exception("Failed to parse zone resolutions: %s", ex)
        return

    resolutions = {
        f"{subdomain}.{args.hosted_zone}.": ips
        for subdomain, ips in raw_resolutions.items()
    }

    # Launch DNS server
    server_address = ("", args.port)
    with socketserver.UDPServer(server_address, DNSUDPHandler) as server:
        server.hosted_zone = f"{args.hosted_zone}."
        server.primary_name_server = name_servers[0]
        server.name_servers = name_servers
        server.resolutions = resolutions
        server.ttl_a = args.ttl_a
        server.ttl_ns = args.ttl_ns
        server.soa_serial = int(time.time())
        server.soa_refresh = args.soa_refresh
        server.soa_retry = args.soa_retry
        server.soa_expire = args.soa_expire

        logging.info("DNS server listening on port %d", server_address[1])
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logging.info("Shutting down DNS server")
