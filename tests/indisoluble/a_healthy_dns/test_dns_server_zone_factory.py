#!/usr/bin/env python3

import json

from unittest.mock import patch

import dns.name
import dns.rdatatype
import dns.versioned

import indisoluble.a_healthy_dns.dns_server_zone_factory as dszf


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
                },
                "api": {
                    dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.2.1"],
                },
            }
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    zone = dszf.make_zone(args)

    assert zone is not None
    assert isinstance(zone, dns.versioned.Zone)

    # Check zone origin
    assert zone.origin == dns.name.from_text("dev.example.com.")

    with zone.reader() as txn:
        # Check SOA record
        soa_rdataset = txn.get("dev.example.com.", dns.rdatatype.SOA)
        assert soa_rdataset is not None
        assert soa_rdataset.ttl == 300

        soa_rdata = soa_rdataset[0]
        assert str(soa_rdata.mname) == "ns1.example.com."
        assert str(soa_rdata.rname) == "hostmaster.dev.example.com."
        assert soa_rdata.serial == 1234567890
        assert soa_rdata.refresh == 7200
        assert soa_rdata.retry == 3600
        assert soa_rdata.expire == 1209600
        assert soa_rdata.minimum == 300

        # Check NS records
        ns_rdataset = txn.get("dev.example.com.", dns.rdatatype.NS)
        assert ns_rdataset is not None
        assert ns_rdataset.ttl == 86400
        assert len(ns_rdataset) == 2
        ns_names = sorted([str(rdata.target) for rdata in ns_rdataset])
        assert ns_names == ["ns1.example.com.", "ns2.example.com."]

        # Check A records for www subdomain
        www_a_rdataset = txn.get("www.dev.example.com.", dns.rdatatype.A)
        assert www_a_rdataset is not None
        assert www_a_rdataset.ttl == 300
        assert len(www_a_rdataset) == 2
        www_ips = sorted([rdata.address for rdata in www_a_rdataset])
        assert www_ips == ["192.168.1.1", "192.168.1.2"]

        # Check A records for api subdomain
        api_a_rdataset = txn.get("api.dev.example.com.", dns.rdatatype.A)
        assert api_a_rdataset is not None
        assert api_a_rdataset.ttl == 300
        assert len(api_a_rdataset) == 1
        assert api_a_rdataset[0].address == "192.168.2.1"


def test_make_zone_invalid_hosted_zone():
    args = {
        dszf.HOSTED_ZONE_ARG: "",  # Invalid empty hosted zone
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {"www": {dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"]}}
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    zone = dszf.make_zone(args)
    assert zone is None


def test_make_zone_invalid_hosted_zone_chars():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example@.com",  # Invalid character in domain
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {"www": {dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"]}}
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    zone = dszf.make_zone(args)
    assert zone is None


def test_make_zone_invalid_json_name_servers():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: "invalid json",  # Invalid JSON
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {"www": {dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"]}}
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    zone = dszf.make_zone(args)
    assert zone is None


def test_make_zone_wrong_type_name_servers():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(
            {"ns": "ns1.example.com"}
        ),  # Wrong type (dict instead of list)
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {"www": {dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"]}}
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    zone = dszf.make_zone(args)
    assert zone is None


def test_make_zone_empty_name_servers():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps([]),  # Empty list
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {"www": {dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"]}}
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    zone = dszf.make_zone(args)
    assert zone is None


def test_make_zone_invalid_name_server():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(
            ["ns1.example@.com"]
        ),  # Invalid character in name server
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {"www": {dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"]}}
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    zone = dszf.make_zone(args)
    assert zone is None


def test_make_zone_negative_ttl_a():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {"www": {dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"]}}
        ),
        dszf.TTL_A_ARG: -300,  # Negative TTL
        dszf.TTL_NS_ARG: 86400,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    zone = dszf.make_zone(args)
    assert zone is None


def test_make_zone_negative_ttl_ns():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {"www": {dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"]}}
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: -86400,  # Negative TTL
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    zone = dszf.make_zone(args)
    assert zone is None


def test_make_zone_negative_soa_refresh():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {"www": {dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"]}}
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.SOA_REFRESH_ARG: -7200,  # Negative refresh
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    zone = dszf.make_zone(args)
    assert zone is None


def test_make_zone_negative_soa_retry():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {"www": {dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"]}}
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: -3600,  # Negative retry
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    zone = dszf.make_zone(args)
    assert zone is None


def test_make_zone_negative_soa_expire():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {"www": {dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"]}}
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: -1209600,  # Negative expire
    }

    zone = dszf.make_zone(args)
    assert zone is None


def test_make_zone_invalid_json_resolutions():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: "invalid json",  # Invalid JSON
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    zone = dszf.make_zone(args)
    assert zone is None


def test_make_zone_wrong_type_resolutions():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            ["192.168.1.1"]
        ),  # Wrong type (list instead of dict)
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    zone = dszf.make_zone(args)
    assert zone is None


def test_make_zone_empty_resolutions():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps({}),  # Empty dict
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    zone = dszf.make_zone(args)
    assert zone is None


def test_make_zone_invalid_subdomain():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {"www@": {dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.1"]}}  # Invalid subdomain
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    zone = dszf.make_zone(args)
    assert zone is None


def test_make_zone_wrong_type_subdomain_config():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {"www": ["192.168.1.1"]}  # Wrong type (list instead of dict)
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    zone = dszf.make_zone(args)
    assert zone is None


def test_make_zone_wrong_type_ip_list():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {dszf.SUBDOMAIN_IP_LIST_ARG: "192.168.1.1"}
            }  # Wrong type (string instead of list)
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    zone = dszf.make_zone(args)
    assert zone is None


def test_make_zone_empty_ip_list():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {"www": {dszf.SUBDOMAIN_IP_LIST_ARG: []}}  # Empty list
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    zone = dszf.make_zone(args)
    assert zone is None


def test_make_zone_invalid_ip():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1.300"]}
            }  # Invalid IP (octet > 255)
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    zone = dszf.make_zone(args)
    assert zone is None


def test_make_zone_malformed_ip():
    args = {
        dszf.HOSTED_ZONE_ARG: "dev.example.com",
        dszf.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dszf.ZONE_RESOLUTIONS_ARG: json.dumps(
            {
                "www": {dszf.SUBDOMAIN_IP_LIST_ARG: ["192.168.1"]}
            }  # Malformed IP (missing octet)
        ),
        dszf.TTL_A_ARG: 300,
        dszf.TTL_NS_ARG: 86400,
        dszf.SOA_REFRESH_ARG: 7200,
        dszf.SOA_RETRY_ARG: 3600,
        dszf.SOA_EXPIRE_ARG: 1209600,
    }

    zone = dszf.make_zone(args)
    assert zone is None
