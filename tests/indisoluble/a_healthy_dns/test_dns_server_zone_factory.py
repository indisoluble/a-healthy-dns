#!/usr/bin/env python3

import json

import dns.dnssectypes
import dns.name
import pytest

import indisoluble.a_healthy_dns.dns_server_zone_factory as dszf

from dns.dnssecalgs.rsa import PrivateRSASHA256

from indisoluble.a_healthy_dns.healthy_ip import HealthyIp


@pytest.fixture
def args():
    return {
        dszf.ARG_HOSTED_ZONE: "dev.example.com",
        dszf.ARG_NAME_SERVERS: json.dumps(["ns1.example.com", "ns2.example.com"]),
        dszf.ARG_ZONE_RESOLUTIONS: json.dumps(
            {
                "www": {
                    dszf.ARG_SUBDOMAIN_IP_LIST: ["192.168.1.1", "192.168.1.2"],
                    dszf.ARG_SUBDOMAIN_HEALTH_PORT: 8080,
                },
                "api": {
                    dszf.ARG_SUBDOMAIN_IP_LIST: ["192.168.2.1"],
                    dszf.ARG_SUBDOMAIN_HEALTH_PORT: 8081,
                },
                "repeated": {
                    dszf.ARG_SUBDOMAIN_IP_LIST: ["10.16.2.1", "10.16.2.1", "10.16.2.1"],
                    dszf.ARG_SUBDOMAIN_HEALTH_PORT: 8082,
                },
                "zeros": {
                    dszf.ARG_SUBDOMAIN_IP_LIST: ["192.0168.000.020", "0102.018.001.01"],
                    dszf.ARG_SUBDOMAIN_HEALTH_PORT: 8083,
                },
            }
        ),
        dszf.ARG_TTL_A: 300,
        dszf.ARG_TTL_NS: 86400,
        dszf.ARG_TTL_SOA: 301,
        dszf.ARG_SOA_REFRESH: 7200,
        dszf.ARG_SOA_RETRY: 3600,
        dszf.ARG_SOA_EXPIRE: 1209600,
        dszf.ARG_SOA_MIN_TTL: 601,
        dszf.ARG_DNSSEC_PRIVATE_KEY_PEM: None,
        dszf.ARG_DNSSEC_ALGORITHM: "RSASHA256",
        dszf.ARG_DNSSEC_LIFETIME: 1209600,
        dszf.ARG_DNSSEC_TTL_DNSKEY: 86400,
    }


@pytest.fixture
def args_with_dnssec(args):
    args[dszf.ARG_DNSSEC_PRIVATE_KEY_PEM] = PrivateRSASHA256.generate(
        key_size=2048
    ).to_pem()

    return args


def test_make_zone_success(args):
    ext_zone = dszf.make_zone(args)
    assert ext_zone is not None

    # Check private key
    assert ext_zone.ext_priv_key is None

    # Check zone origin
    assert ext_zone.zone.origin == dns.name.from_text("dev.example.com.")

    # Check NS records
    assert ext_zone.ns_rec.ttl == 86400
    assert len(ext_zone.ns_rec) == 2
    ns_names = sorted([str(rdata.target) for rdata in ext_zone.ns_rec])
    assert ns_names == ["ns1.example.com.", "ns2.example.com."]

    # Check SOA record
    assert ext_zone.soa_rec.ttl == 301

    soa_rdata = ext_zone.soa_rec[0]
    assert str(soa_rdata.mname) == "ns1.example.com."
    assert str(soa_rdata.rname) == "hostmaster.dev.example.com."
    assert soa_rdata.serial == 0
    assert soa_rdata.refresh == 7200
    assert soa_rdata.retry == 3600
    assert soa_rdata.expire == 1209600
    assert soa_rdata.minimum == 601

    # Check A records
    assert len(ext_zone.a_recs) == 4

    healthy_ips_by_subdomain = {}
    for record in ext_zone.a_recs:
        healthy_ips_by_subdomain[record.subdomain] = (record.ttl_a, record.healthy_ips)

    # Check www subdomain
    www_name = dns.name.from_text("www", origin=ext_zone.zone.origin)
    assert www_name in healthy_ips_by_subdomain
    assert healthy_ips_by_subdomain[www_name][0] == 300
    assert healthy_ips_by_subdomain[www_name][1] == frozenset(
        [HealthyIp("192.168.1.1", 8080, False), HealthyIp("192.168.1.2", 8080, False)]
    )

    # Check api subdomain
    api_name = dns.name.from_text("api", origin=ext_zone.zone.origin)
    assert api_name in healthy_ips_by_subdomain
    assert healthy_ips_by_subdomain[api_name][0] == 300
    assert healthy_ips_by_subdomain[api_name][1] == frozenset(
        [HealthyIp("192.168.2.1", 8081, False)]
    )

    # Check repeated subdomain
    repeated_name = dns.name.from_text("repeated", origin=ext_zone.zone.origin)
    assert repeated_name in healthy_ips_by_subdomain
    assert healthy_ips_by_subdomain[repeated_name][0] == 300
    assert healthy_ips_by_subdomain[repeated_name][1] == frozenset(
        [HealthyIp("10.16.2.1", 8082, False)]
    )

    # Check zeros subdomain
    zeros_name = dns.name.from_text("zeros", origin=ext_zone.zone.origin)
    assert zeros_name in healthy_ips_by_subdomain
    assert healthy_ips_by_subdomain[zeros_name][0] == 300
    assert healthy_ips_by_subdomain[zeros_name][1] == frozenset(
        [HealthyIp("102.18.1.1", 8083, False), HealthyIp("192.168.0.20", 8083, False)]
    )


def test_make_zone_success_with_dnssec(args_with_dnssec):
    ext_zone = dszf.make_zone(args_with_dnssec)
    assert ext_zone is not None

    # Check private key
    assert ext_zone.ext_priv_key is not None
    assert ext_zone.ext_priv_key.private_key is not None
    assert isinstance(ext_zone.ext_priv_key.private_key, PrivateRSASHA256)
    assert ext_zone.ext_priv_key.dnskey is not None
    assert ext_zone.ext_priv_key.dnskey.algorithm == dns.dnssectypes.Algorithm.RSASHA256
    assert ext_zone.ext_priv_key.dnskey_ttl == 86400
    assert ext_zone.ext_priv_key.rrsig_lifetime == 1209600


def test_make_zone_invalid_hosted_zone(args):
    args[dszf.ARG_HOSTED_ZONE] = ""  # Invalid empty hosted zone

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_invalid_hosted_zone_chars(args):
    args[dszf.ARG_HOSTED_ZONE] = "dev.example@.com"  # Invalid character in domain

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_invalid_json_name_servers(args):
    args[dszf.ARG_NAME_SERVERS] = "invalid json"  # Invalid JSON

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_wrong_type_name_servers(args):
    args[dszf.ARG_NAME_SERVERS] = json.dumps(
        {"ns": "ns1.example.com"}
    )  # Wrong type (dict instead of list)

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_empty_name_servers(args):
    args[dszf.ARG_NAME_SERVERS] = json.dumps([])  # Empty list

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_invalid_name_server(args):
    args[dszf.ARG_NAME_SERVERS] = json.dumps(
        ["ns1.example@.com"]
    )  # Invalid character in name server

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_negative_ttl_a(args):
    args[dszf.ARG_TTL_A] = -300  # Negative TTL

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_negative_ttl_ns(args):
    args[dszf.ARG_TTL_NS] = -86400  # Negative TTL

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_negative_ttl_soa(args):
    args[dszf.ARG_TTL_SOA] = -301  # Negative TTL

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_negative_soa_refresh(args):
    args[dszf.ARG_SOA_REFRESH] = -7200  # Negative refresh

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_negative_soa_retry(args):
    args[dszf.ARG_SOA_RETRY] = -3600  # Negative retry

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_negative_soa_expire(args):
    args[dszf.ARG_SOA_EXPIRE] = -1209600  # Negative expire

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_negative_soa_min_ttl(args):
    args[dszf.ARG_SOA_MIN_TTL] = -601  # Negative minimum TTL

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_invalid_json_resolutions(args):
    args[dszf.ARG_ZONE_RESOLUTIONS] = "invalid json"  # Invalid JSON

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_wrong_type_resolutions(args):
    args[dszf.ARG_ZONE_RESOLUTIONS] = json.dumps(
        ["192.168.1.1", 8080]
    )  # Wrong type (list instead of dict)

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_empty_resolutions(args):
    args[dszf.ARG_ZONE_RESOLUTIONS] = json.dumps({})  # Empty dict

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_invalid_subdomain(args):
    args[dszf.ARG_ZONE_RESOLUTIONS] = json.dumps(
        {
            "www@": {
                dszf.ARG_SUBDOMAIN_IP_LIST: ["192.168.1.1"],
                dszf.ARG_SUBDOMAIN_HEALTH_PORT: 8080,
            }
        }
    )  # Invalid subdomain

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_wrong_type_subdomain_config(args):
    args[dszf.ARG_ZONE_RESOLUTIONS] = json.dumps(
        {"www": ["192.168.1.1", 8080]}
    )  # Wrong type (list instead of dict)

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_wrong_type_ip_list(args):
    args[dszf.ARG_ZONE_RESOLUTIONS] = json.dumps(
        {
            "www": {
                dszf.ARG_SUBDOMAIN_IP_LIST: "192.168.1.1",
                dszf.ARG_SUBDOMAIN_HEALTH_PORT: 8080,
            }
        }
    )  # Wrong type (string instead of list)

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_empty_ip_list(args):
    args[dszf.ARG_ZONE_RESOLUTIONS] = json.dumps(
        {"www": {dszf.ARG_SUBDOMAIN_IP_LIST: [], dszf.ARG_SUBDOMAIN_HEALTH_PORT: 8080}}
    )  # Empty list

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_invalid_ip(args):
    args[dszf.ARG_ZONE_RESOLUTIONS] = json.dumps(
        {
            "www": {
                dszf.ARG_SUBDOMAIN_IP_LIST: ["192.168.1.300"],
                dszf.ARG_SUBDOMAIN_HEALTH_PORT: 8080,
            }
        }
    )  # Invalid IP (octet > 255)

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_malformed_ip(args):
    args[dszf.ARG_ZONE_RESOLUTIONS] = json.dumps(
        {
            "www": {
                dszf.ARG_SUBDOMAIN_IP_LIST: ["192.168.1"],
                dszf.ARG_SUBDOMAIN_HEALTH_PORT: 8080,
            }
        }
    )  # Malformed IP (missing octet)

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_wrong_type_health_port(args):
    args[dszf.ARG_ZONE_RESOLUTIONS] = json.dumps(
        {
            "www": {
                dszf.ARG_SUBDOMAIN_IP_LIST: ["192.168.1.1"],
                dszf.ARG_SUBDOMAIN_HEALTH_PORT: "8080",
            }
        }
    )  # String instead of int

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_negative_health_port(args):
    args[dszf.ARG_ZONE_RESOLUTIONS] = json.dumps(
        {
            "www": {
                dszf.ARG_SUBDOMAIN_IP_LIST: ["192.168.1.1"],
                dszf.ARG_SUBDOMAIN_HEALTH_PORT: -8080,
            }
        }
    )  # Negative port

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_invalid_port_range(args):
    args[dszf.ARG_ZONE_RESOLUTIONS] = json.dumps(
        {
            "www": {
                dszf.ARG_SUBDOMAIN_IP_LIST: ["192.168.1.1"],
                dszf.ARG_SUBDOMAIN_HEALTH_PORT: 65536,
            }
        }
    )  # Port > 65535 (invalid)

    ext_zone = dszf.make_zone(args)

    assert ext_zone is None


def test_make_zone_invalid_dnskey_ttl(args_with_dnssec):
    args_with_dnssec[dszf.ARG_DNSSEC_TTL_DNSKEY] = -86400  # Negative TTL

    ext_zone = dszf.make_zone(args_with_dnssec)

    assert ext_zone is None


def test_make_zone_invalid_rrsig_lifetime(args_with_dnssec):
    args_with_dnssec[dszf.ARG_DNSSEC_LIFETIME] = -1209600  # Negative lifetime

    ext_zone = dszf.make_zone(args_with_dnssec)

    assert ext_zone is None


def test_make_zone_invalid_dnssec_algorithm(args_with_dnssec):
    args_with_dnssec[dszf.ARG_DNSSEC_ALGORITHM] = "INVALID_ALG"  # Invalid algorithm

    ext_zone = dszf.make_zone(args_with_dnssec)

    assert ext_zone is None
