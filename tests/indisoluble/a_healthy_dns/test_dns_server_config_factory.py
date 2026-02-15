#!/usr/bin/env python3

import json

import dns.dnssectypes
import dns.name
import pytest

import indisoluble.a_healthy_dns.dns_server_config_factory as dscf

from unittest.mock import patch

from dns.dnssecalgs.rsa import PrivateRSASHA256

from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp


@pytest.fixture
def args():
    return {
        dscf.ARG_HOSTED_ZONE: "dev.example.com",
        dscf.ARG_ALIAS_ZONES: json.dumps([]),
        dscf.ARG_NAME_SERVERS: json.dumps(["ns1.example.com", "ns2.example.com"]),
        dscf.ARG_ZONE_RESOLUTIONS: json.dumps(
            {
                "www": {
                    dscf.ARG_SUBDOMAIN_IP_LIST: ["192.168.1.1", "192.168.1.2"],
                    dscf.ARG_SUBDOMAIN_HEALTH_PORT: 8080,
                },
                "api": {
                    dscf.ARG_SUBDOMAIN_IP_LIST: ["192.168.2.1"],
                    dscf.ARG_SUBDOMAIN_HEALTH_PORT: 8081,
                },
                "repeated": {
                    dscf.ARG_SUBDOMAIN_IP_LIST: ["10.16.2.1", "10.16.2.1", "10.16.2.1"],
                    dscf.ARG_SUBDOMAIN_HEALTH_PORT: 8082,
                },
                "zeros": {
                    dscf.ARG_SUBDOMAIN_IP_LIST: ["192.0168.000.020", "0102.018.001.01"],
                    dscf.ARG_SUBDOMAIN_HEALTH_PORT: 8083,
                },
            }
        ),
        dscf.ARG_DNSSEC_PRIVATE_KEY_PATH: None,
        dscf.ARG_DNSSEC_ALGORITHM: "RSASHA256",
    }


@pytest.fixture
def args_with_dnssec(args):
    args[dscf.ARG_DNSSEC_PRIVATE_KEY_PATH] = "test/path/to/private_key.pem"

    return args


def test_make_config_success(args):
    config = dscf.make_config(args)
    assert config is not None

    # Check private key
    assert config.ext_private_key is None

    # Check zone origins
    assert config.zone_origins.primary == dns.name.from_text(
        "dev.example.com", origin=dns.name.root
    )

    # Check name servers
    assert config.name_servers == frozenset(["ns1.example.com.", "ns2.example.com."])

    # Check A records
    assert len(config.a_records) == 4

    healthy_ips_by_subdomain = {}
    for record in config.a_records:
        healthy_ips_by_subdomain[record.subdomain] = record.healthy_ips

    # Check www subdomain
    www_name = dns.name.from_text("www", origin=config.zone_origins.primary)
    assert www_name in healthy_ips_by_subdomain
    assert healthy_ips_by_subdomain[www_name] == frozenset(
        [AHealthyIp("192.168.1.1", 8080, False), AHealthyIp("192.168.1.2", 8080, False)]
    )

    # Check api subdomain
    api_name = dns.name.from_text("api", origin=config.zone_origins.primary)
    assert api_name in healthy_ips_by_subdomain
    assert healthy_ips_by_subdomain[api_name] == frozenset(
        [AHealthyIp("192.168.2.1", 8081, False)]
    )

    # Check repeated subdomain
    repeated_name = dns.name.from_text("repeated", origin=config.zone_origins.primary)
    assert repeated_name in healthy_ips_by_subdomain
    assert healthy_ips_by_subdomain[repeated_name] == frozenset(
        [AHealthyIp("10.16.2.1", 8082, False)]
    )

    # Check zeros subdomain
    zeros_name = dns.name.from_text("zeros", origin=config.zone_origins.primary)
    assert zeros_name in healthy_ips_by_subdomain
    assert healthy_ips_by_subdomain[zeros_name] == frozenset(
        [AHealthyIp("102.18.1.1", 8083, False), AHealthyIp("192.168.0.20", 8083, False)]
    )


@patch("indisoluble.a_healthy_dns.dns_server_config_factory._load_dnssec_private_key")
def test_make_zone_success_with_dnssec(mock_load_key, args_with_dnssec):
    mock_load_key.return_value = PrivateRSASHA256.generate(key_size=2048).to_pem()

    config = dscf.make_config(args_with_dnssec)
    assert config is not None

    # Check private key
    assert config.ext_private_key is not None
    assert config.ext_private_key.private_key is not None
    assert isinstance(config.ext_private_key.private_key, PrivateRSASHA256)
    assert config.ext_private_key.dnskey is not None
    assert (
        config.ext_private_key.dnskey.algorithm == dns.dnssectypes.Algorithm.RSASHA256
    )

    # Check others
    assert config.zone_origins is not None
    assert config.name_servers is not None
    assert config.a_records is not None


@pytest.mark.parametrize("invalid_zone", ["", "dev.example@.com"])
def test_make_zone_invalid_hosted_zone(invalid_zone, args):
    args[dscf.ARG_HOSTED_ZONE] = invalid_zone
    assert dscf.make_config(args) is None


@pytest.mark.parametrize(
    "invalid_ns",
    [
        "invalid json",
        json.dumps([]),
        json.dumps({"ns": "ns1.example.com"}),
        json.dumps(["ns1.example@.com"]),
    ],
)
def test_make_zone_invalid_json_name_servers(invalid_ns, args):
    args[dscf.ARG_NAME_SERVERS] = invalid_ns
    assert dscf.make_config(args) is None


@pytest.mark.parametrize(
    "invalid_resolution",
    [
        "invalid json",
        json.dumps({}),
        json.dumps(["192.168.1.1", 8080]),
        json.dumps(
            {
                "www@": {
                    dscf.ARG_SUBDOMAIN_IP_LIST: ["192.168.1.1"],
                    dscf.ARG_SUBDOMAIN_HEALTH_PORT: 8080,
                }
            }
        ),
        json.dumps({"www": ["192.168.1.1", 8080]}),
        json.dumps(
            {
                "www": {
                    dscf.ARG_SUBDOMAIN_IP_LIST: "192.168.1.1",
                    dscf.ARG_SUBDOMAIN_HEALTH_PORT: 8080,
                }
            }
        ),
        json.dumps(
            {
                "www": {
                    dscf.ARG_SUBDOMAIN_IP_LIST: [],
                    dscf.ARG_SUBDOMAIN_HEALTH_PORT: 8080,
                }
            }
        ),
        json.dumps(
            {
                "www": {
                    dscf.ARG_SUBDOMAIN_IP_LIST: ["192.168.1.300"],
                    dscf.ARG_SUBDOMAIN_HEALTH_PORT: 8080,
                }
            }
        ),
        json.dumps(
            {
                "www": {
                    dscf.ARG_SUBDOMAIN_IP_LIST: ["192.168.1"],
                    dscf.ARG_SUBDOMAIN_HEALTH_PORT: 8080,
                }
            }
        ),
        json.dumps(
            {
                "www": {
                    dscf.ARG_SUBDOMAIN_IP_LIST: ["192.168.1.1"],
                    dscf.ARG_SUBDOMAIN_HEALTH_PORT: "8080",
                }
            }
        ),
        json.dumps(
            {
                "www": {
                    dscf.ARG_SUBDOMAIN_IP_LIST: ["192.168.1.1"],
                    dscf.ARG_SUBDOMAIN_HEALTH_PORT: -8080,
                }
            }
        ),
        json.dumps(
            {
                "www": {
                    dscf.ARG_SUBDOMAIN_IP_LIST: ["192.168.1.1"],
                    dscf.ARG_SUBDOMAIN_HEALTH_PORT: 65536,
                }
            }
        ),
    ],
)
def test_make_zone_invalid_json_resolutions(invalid_resolution, args):
    args[dscf.ARG_ZONE_RESOLUTIONS] = invalid_resolution
    assert dscf.make_config(args) is None


@patch("indisoluble.a_healthy_dns.dns_server_config_factory._load_dnssec_private_key")
def test_make_zone_invalid_dnssec_algorithm(mock_load_key, args_with_dnssec):
    mock_load_key.return_value = PrivateRSASHA256.generate(key_size=2048).to_pem()

    args_with_dnssec[dscf.ARG_DNSSEC_ALGORITHM] = "INVALID_ALG"
    assert dscf.make_config(args_with_dnssec) is None
