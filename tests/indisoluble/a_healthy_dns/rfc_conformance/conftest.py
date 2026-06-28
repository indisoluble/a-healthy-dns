#!/usr/bin/env python3

import socketserver
import threading
import time

import dns.message
import dns.name
import dns.rdatatype
import pytest

from indisoluble.a_healthy_dns.dns_server_config_factory import DnsServerConfig
from indisoluble.a_healthy_dns.dns_server_udp_handler import DnsServerUdpHandler
from indisoluble.a_healthy_dns.dns_server_zone_updater import DnsServerZoneUpdater
from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp
from indisoluble.a_healthy_dns.records.a_healthy_record import AHealthyRecord
from indisoluble.a_healthy_dns.records.zone_origins import ZoneOrigins

from . import support as s


@pytest.fixture(scope="module")
def live_server():
    """Start a real local UDP server with a pre-populated in-memory zone."""
    zone_origins = ZoneOrigins(s.ZONE, [s.ALIAS_ZONE])

    a_record = AHealthyRecord(
        subdomain=dns.name.from_text(s.SUBDOMAIN, origin=zone_origins.primary),
        healthy_ips=[AHealthyIp(ip=s.SUBDOMAIN_IP, health_port=8080, is_healthy=True)],
    )
    nested_record = AHealthyRecord(
        subdomain=dns.name.from_text(s.NESTED_SUBDOMAIN, origin=zone_origins.primary),
        healthy_ips=[
            AHealthyIp(
                ip=s.NESTED_SUBDOMAIN_IP,
                health_port=8080,
                is_healthy=True,
            )
        ],
    )
    config = DnsServerConfig(
        zone_origins=zone_origins,
        primary_name_server=s.NS,
        name_servers=frozenset([s.NS]),
        a_records=frozenset([a_record, nested_record]),
        ext_private_key=None,
    )

    updater = DnsServerZoneUpdater(min_interval=30, connection_timeout=2, config=config)
    updater.initialize_zone()

    server = socketserver.UDPServer(("127.0.0.1", 0), DnsServerUdpHandler)
    server.zone = updater.zone
    server.zone_origins = zone_origins

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(s.SERVER_READY_WAIT)

    host, port = server.server_address
    yield host, port

    server.shutdown()
    thread.join(timeout=5)
    server.server_close()


@pytest.fixture
def zone_origins():
    return ZoneOrigins("example.com", [])


@pytest.fixture
def dns_response():
    return dns.message.make_response(dns.message.make_query("dummy", dns.rdatatype.A))


@pytest.fixture
def dns_client_address():
    return (s.TEST_SOURCE_HOST, s.TEST_SOURCE_PORT)


@pytest.fixture
def dns_request():
    query = dns.message.make_query("test.example.com.", dns.rdatatype.A)
    return s.make_request(query.to_wire())[0]


@pytest.fixture
def soa_rdataset():
    return s.make_soa_rdataset()
