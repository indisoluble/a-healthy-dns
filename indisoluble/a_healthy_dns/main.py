#!/usr/bin/env python3

import argparse
import json
import logging
import socketserver

import dns.message
import dns.rdatatype
import dns.rrset


class DNSUDPHandler(socketserver.BaseRequestHandler):
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
            sock.sendto(response.to_wire(), self.client_address)
            return

        question = query.question[0]
        if question.rdtype != dns.rdatatype.A:
            logging.warning("Received unsupported query type: %s", question.rdtype)
            response.set_rcode(dns.rcode.NOTIMP)
            sock.sendto(response.to_wire(), self.client_address)
            return

        qname = question.name.to_text()
        if qname not in self.server.config:
            logging.warning("Received query for unknown domain: %s", qname)
            response.set_rcode(dns.rcode.NXDOMAIN)
            sock.sendto(response.to_wire(), self.client_address)
            return

        ips = self.server.config[qname]
        logging.debug("Responded to query for %s with %s", qname, ips)

        rrset = dns.rrset.from_text(qname, self.server.ttl, "IN", "A", *ips)
        response.answer.append(rrset)
        sock.sendto(response.to_wire(), self.client_address)


def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="DNS server")
    parser.add_argument(
        "--config", type=str, required=True, help="JSON string for config."
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

    # Load the configuration
    config = json.loads(args.config)

    # Launch DNS server
    server_address = ("", args.port)
    with socketserver.UDPServer(server_address, DNSUDPHandler) as server:
        server.config = config
        server.ttl = args.ttl

        logging.info("DNS server listening on port %d", server_address[1])
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logging.info("Shutting down DNS server")
