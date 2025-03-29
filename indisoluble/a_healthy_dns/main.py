#!/usr/bin/env python3

import argparse
import json
import logging
import socketserver

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
        logging.debug("Responded to query for %s with %s", qname, ips)

        rrset = dns.rrset.from_text(qname, self.server.ttl, "IN", "A", *ips)
        response.answer.append(rrset)

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
        "--zone-resolutions",
        type=str,
        required=True,
        help="List of subdomains with their respectives IPs as JSON string (ex. {sd1: [ip1, ip2, ...], ...})",
    )
    parser.add_argument(
        "--port", type=int, default=5053, help="DNS server port (default: 5053)"
    )
    parser.add_argument(
        "--ttl", type=int, default=60, help="TTL in seconds (default: 60)"
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
        server.resolutions = resolutions
        server.ttl = args.ttl

        logging.info("DNS server listening on port %d", server_address[1])
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logging.info("Shutting down DNS server")
