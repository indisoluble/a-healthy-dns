#!/usr/bin/env python3

import json

import dns.name
import dns.rdatatype

import indisoluble.a_healthy_dns.dns_server_zone_factory as dszf

from unittest.mock import patch

from indisoluble.a_healthy_dns.healthy_ip import HealthyIp


@patch("time.time")
def test_make_zone_success(mock_time):
    mock_time.return_value = 1234567890

    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com", "ns2.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1", "192.168.1.2"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                },
                "api": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.2.1"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 8081,
                },
                "repeated": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["10.16.2.1", "10.16.2.1", "10.16.2.1"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 8082,
                },
                "zeros": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.0168.000.020", "0102.018.001.01"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 8083,
                },
            }
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)

    assert ext_zone is not None
    assert isinstance(ext_zone, dszf.ExtendedZone)

    # Check zone origin
    assert ext_zone.zone.origin == dns.name.from_text("dev.example.com.")

    assert len(ext_zone.a_records) == 4

    healthy_ips_by_subdomain = {}
    for record in ext_zone.a_records:
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

    with ext_zone.zone.reader() as txn:
        # Check SOA record
        soa_rdataset = txn.get("dev.example.com.", dns.rdatatype.SOA)
        assert soa_rdataset is not None
        assert soa_rdataset.ttl == 301

        soa_rdata = soa_rdataset[0]
        assert str(soa_rdata.mname) == "ns1.example.com."
        assert str(soa_rdata.rname) == "hostmaster.dev.example.com."
        assert soa_rdata.serial == 1234567890
        assert soa_rdata.refresh == 7200
        assert soa_rdata.retry == 3600
        assert soa_rdata.expire == 1209600
        assert soa_rdata.minimum == 301

        # Check NS records
        ns_rdataset = txn.get("dev.example.com.", dns.rdatatype.NS)
        assert ns_rdataset is not None
        assert ns_rdataset.ttl == 86400
        assert len(ns_rdataset) == 2
        ns_names = sorted([str(rdata.target) for rdata in ns_rdataset])
        assert ns_names == ["ns1.example.com.", "ns2.example.com."]


def test_make_zone_invalid_hosted_zone():
    args = {
        dszf.HOSTED_ZONE_ARG: "",  # Invalid empty hosted zone
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_invalid_hosted_zone_chars():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example@.com",  # Invalid character in domain
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_invalid_json_name_servers():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: "invalid json",  # Invalid JSON
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_wrong_type_name_servers():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(
            {"ns": "ns1.example.com"}
        ),  # Wrong type (dict instead of list)
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_empty_name_servers():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps([]),  # Empty list
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_invalid_name_server():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(
            ["ns1.example@.com"]
        ),  # Invalid character in name server
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_negative_ttl_a():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }
        ),
        dszf.TTL_A_ARG: -300,  # Negative TTL
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_negative_ttl_ns():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: -86400,  # Negative TTL
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_negative_ttl_soa():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: -301,  # Negative TTL
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_negative_soa_refresh():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: -7200,  # Negative refresh
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_negative_soa_retry():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: -3600,  # Negative retry
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_negative_soa_expire():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: -1209600,  # Negative expire
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_invalid_json_resolutions():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: "invalid json",  # Invalid JSON
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_wrong_type_resolutions():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            ["192.168.1.1", 8080]
        ),  # Wrong type (list instead of dict)
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_empty_resolutions():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps({}),  # Empty dict
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_invalid_subdomain():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www@": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }  # Invalid subdomain
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_wrong_type_subdomain_config():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {"www": ["192.168.1.1", 8080]}  # Wrong type (list instead of dict)
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_wrong_type_ip_list():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: "192.168.1.1",
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }  # Wrong type (string instead of list)
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_empty_ip_list():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: [],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }  # Empty list
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_invalid_ip():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.300"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }  # Invalid IP (octet > 255)
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_malformed_ip():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 8080,
                }
            }  # Malformed IP (missing octet)
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_wrong_type_health_port():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: "8080",  # String instead of int
                }
            }
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_negative_health_port():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: -8080,  # Negative port
                }
            }
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None


def test_make_zone_invalid_port_range():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"],
                    dszf.SUBDOMAIN_HEALTH_PORT_ARG: 65536,  # Port > 65535 (invalid)
                }
            }
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.TTL_SOA_ARG: 301,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    ext_zone = dszf.make_zone(args)
    assert ext_zone is None
