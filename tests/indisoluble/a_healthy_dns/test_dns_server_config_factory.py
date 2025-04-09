#!/usr/bin/env python3

import json

from unittest.mock import patch

import indisoluble.a_healthy_dns.dns_server_config_factory as dscf


@patch("time.time")
def test_make_config(mock_time):
    mock_time.return_value = 1234567890

    args = {
        dscf.HOSTED_ZONE_ARG: "dev.example.com",
        dscf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com", "ns2.example.com"]),
        dscf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dscf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"],
                    dscf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }
        ),
        dscf.TTL_A_ARG: 300,
        dscf.TTL_NS_ARG: 86400,
        dscf.SOA_REFRESH_ARG: 7200,
        dscf.SOA_RETRY_ARG: 3600,
        dscf.SOA_EXPIRE_ARG: 1209600,
    }

    config = dscf.make_config(args)

    assert config is not None
    assert config.abs_hosted_zone == "dev.example.com."
    assert config.soa_serial == 1234567890


def test_make_config_invalid_json_name_servers():
    args = {
        dscf.HOSTED_ZONE_ARG: "dev.example.com",
        dscf.NAME_SERVERS_ARG: "invalid json",
        dscf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dscf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"],
                    dscf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }
        ),
        dscf.TTL_A_ARG: 300,
        dscf.TTL_NS_ARG: 86400,
        dscf.SOA_REFRESH_ARG: 7200,
        dscf.SOA_RETRY_ARG: 3600,
        dscf.SOA_EXPIRE_ARG: 1209600,
    }

    config = dscf.make_config(args)
    assert config is None


def test_make_config_wrong_type_name_servers():
    args = {
        dscf.HOSTED_ZONE_ARG: "dev.example.com",
        dscf.NAME_SERVERS_ARG: json.dumps({"ns": "ns1.example.com"}),
        dscf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dscf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"],
                    dscf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }
        ),
        dscf.TTL_A_ARG: 300,
        dscf.TTL_NS_ARG: 86400,
        dscf.SOA_REFRESH_ARG: 7200,
        dscf.SOA_RETRY_ARG: 3600,
        dscf.SOA_EXPIRE_ARG: 1209600,
    }

    config = dscf.make_config(args)
    assert config is None


def test_make_config_invalid_json_resolutions():
    args = {
        dscf.HOSTED_ZONE_ARG: "dev.example.com",
        dscf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dscf.ZONE_RESOLUTIONS_ARG: "invalid json",
        dscf.TTL_A_ARG: 300,
        dscf.TTL_NS_ARG: 86400,
        dscf.SOA_REFRESH_ARG: 7200,
        dscf.SOA_RETRY_ARG: 3600,
        dscf.SOA_EXPIRE_ARG: 1209600,
    }

    config = dscf.make_config(args)
    assert config is None


def test_make_config_wrong_type_json_resolutions():
    args = {
        dscf.HOSTED_ZONE_ARG: "dev.example.com",
        dscf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dscf.ZONE_RESOLUTIONS_ARG: json.dumps(["192.168.1.1", 8080]),
        dscf.TTL_A_ARG: 300,
        dscf.TTL_NS_ARG: 86400,
        dscf.SOA_REFRESH_ARG: 7200,
        dscf.SOA_RETRY_ARG: 3600,
        dscf.SOA_EXPIRE_ARG: 1209600,
    }

    config = dscf.make_config(args)
    assert config is None


def test_make_config_wrong_type_json_resolutions_subdomain():
    args = {
        dscf.HOSTED_ZONE_ARG: "dev.example.com",
        dscf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dscf.ZONE_RESOLUTIONS_ARG: json.dumps({"www": ["192.168.1.1", 8080]}),
        dscf.TTL_A_ARG: 300,
        dscf.TTL_NS_ARG: 86400,
        dscf.SOA_REFRESH_ARG: 7200,
        dscf.SOA_RETRY_ARG: 3600,
        dscf.SOA_EXPIRE_ARG: 1209600,
    }

    config = dscf.make_config(args)
    assert config is None


def test_make_config_wrong_type_json_resolutions_subdomain_ips():
    args = {
        dscf.HOSTED_ZONE_ARG: "dev.example.com",
        dscf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com", "ns2.example.com"]),
        dscf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dscf.SUBDOMAIN_IP_LIST_ARG: {"ip": "192.168.1.1"},
                    dscf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }
        ),
        dscf.TTL_A_ARG: 300,
        dscf.TTL_NS_ARG: 86400,
        dscf.SOA_REFRESH_ARG: 7200,
        dscf.SOA_RETRY_ARG: 3600,
        dscf.SOA_EXPIRE_ARG: 1209600,
    }

    config = dscf.make_config(args)
    assert config is None


def test_make_config_invalid_ip_json_resolutions_subdomain_ips():
    args = {
        dscf.HOSTED_ZONE_ARG: "dev.example.com",
        dscf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com", "ns2.example.com"]),
        dscf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dscf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.300"],
                    dscf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }
        ),
        dscf.TTL_A_ARG: 300,
        dscf.TTL_NS_ARG: 86400,
        dscf.SOA_REFRESH_ARG: 7200,
        dscf.SOA_RETRY_ARG: 3600,
        dscf.SOA_EXPIRE_ARG: 1209600,
    }

    config = dscf.make_config(args)
    assert config is None


def test_make_config_invalid_config():
    args = {
        dscf.HOSTED_ZONE_ARG: "",  # Invalid hosted zone
        dscf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dscf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dscf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"],
                    dscf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }
        ),
        dscf.TTL_A_ARG: 300,
        dscf.TTL_NS_ARG: 86400,
        dscf.SOA_REFRESH_ARG: 7200,
        dscf.SOA_RETRY_ARG: 3600,
        dscf.SOA_EXPIRE_ARG: 1209600,
    }

    config = dscf.make_config(args)
    assert config is None
