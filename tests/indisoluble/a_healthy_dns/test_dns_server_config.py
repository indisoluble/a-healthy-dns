#!/usr/bin/env python3

import pytest
import json

from unittest.mock import patch

import indisoluble.a_healthy_dns.dns_server_config as dsc


def test_valid_config():
    config = dsc.DNSServerConfig(
        hosted_zone="dev.example.com",
        name_servers=["ns1.example.com", "ns2.example.com"],
        resolutions={"www": ["192.168.1.1", "192.168.1.2"]},
        ttl_a=300,
        ttl_ns=86400,
        soa_serial=1234567890,
        soa_refresh=7200,
        soa_retry=3600,
        soa_expire=1209600,
    )

    assert config.abs_hosted_zone == "dev.example.com."
    assert config.primary_abs_name_server == "ns1.example.com."
    assert config.abs_name_servers == ["ns1.example.com.", "ns2.example.com."]
    assert config.ttl_a == 300
    assert config.ttl_ns == 86400
    assert config.soa_serial == 1234567890
    assert config.soa_refresh == 7200
    assert config.soa_retry == 3600
    assert config.soa_expire == 1209600


def test_config_ips():
    config = dsc.DNSServerConfig(
        hosted_zone="dev.example.com",
        name_servers=["ns1.example.com", "ns2.example.com"],
        resolutions={"www": ["192.168.1.1", "192.168.1.2"]},
        ttl_a=300,
        ttl_ns=86400,
        soa_serial=1234567890,
        soa_refresh=7200,
        soa_retry=3600,
        soa_expire=1209600,
    )

    assert config.ips("www.dev.example.com.") == ["192.168.1.1", "192.168.1.2"]
    assert not config.ips("www2.dev.example.com.")


def test_invalid_hosted_zone():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="invalid domain!",
            name_servers=["ns1.example.com"],
            resolutions={"www": ["192.168.1.1"]},
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "not a valid FQDN" in str(excinfo.value)


def test_empty_name_servers():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="dev.example.com",
            name_servers=[],
            resolutions={"www": ["192.168.1.1"]},
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "Name server list cannot be empty" in str(excinfo.value)


def test_invalid_name_server():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="dev.example.com",
            name_servers=["invalid$nameserver"],
            resolutions={"www": ["192.168.1.1"]},
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "not a valid FQDN" in str(excinfo.value)


def test_no_list_name_server():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="dev.example.com",
            name_servers="ns1.example.com",
            resolutions={"www": ["192.168.1.1"]},
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "Name servers must be a list" in str(excinfo.value)


def test_empty_resolutions():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="dev.example.com",
            name_servers=["ns1.example.com"],
            resolutions={},
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "Zone resolutions cannot be empty" in str(excinfo.value)


def test_invalid_subdomain():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="dev.example.com",
            name_servers=["ns1.example.com"],
            resolutions={"invalid*subdomain": ["192.168.1.1"]},
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "not valid" in str(excinfo.value)


def test_no_dict_resolutions():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="dev.example.com",
            name_servers=["ns1.example.com"],
            resolutions="not a dict",
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "Zone resolutions must be a dictionary" in str(excinfo.value)


def test_empty_ip_list():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="example.com",
            name_servers=["ns1.example.com"],
            resolutions={"www": []},
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "IP list for 'www' cannot be empty" in str(excinfo.value)


def test_invalid_ip_address():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="example.com",
            name_servers=["ns1.example.com"],
            resolutions={"www": ["192.168.1.300"]},
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "Invalid IP address" in str(excinfo.value)


def test_no_list_ip():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="example.com",
            name_servers=["ns1.example.com"],
            resolutions={"www": "192.168.1.300"},
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "IP list for 'www' must be a list" in str(excinfo.value)


def test_invalid_ttl_a():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="example.com",
            name_servers=["ns1.example.com"],
            resolutions={"www": ["192.168.1.1"]},
            ttl_a=0,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "TTL for A records must be positive" in str(excinfo.value)


def test_invalid_ttl_ns():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="example.com",
            name_servers=["ns1.example.com"],
            resolutions={"www": ["192.168.1.1"]},
            ttl_a=300,
            ttl_ns=-1,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "TTL for NS records must be positive" in str(excinfo.value)


def test_invalid_soa_serial():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="example.com",
            name_servers=["ns1.example.com"],
            resolutions={"www": ["192.168.1.1"]},
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=0,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "SOA serial must be positive" in str(excinfo.value)


def test_invalid_soa_refresh():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="example.com",
            name_servers=["ns1.example.com"],
            resolutions={"www": ["192.168.1.1"]},
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=0,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "SOA refresh value must be positive" in str(excinfo.value)


def test_invalid_soa_retry():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="example.com",
            name_servers=["ns1.example.com"],
            resolutions={"www": ["192.168.1.1"]},
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=-10,
            soa_expire=1209600,
        )
    assert "SOA retry value must be positive" in str(excinfo.value)


def test_invalid_soa_expire():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="example.com",
            name_servers=["ns1.example.com"],
            resolutions={"www": ["192.168.1.1"]},
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=0,
        )
    assert "SOA expire value must be positive" in str(excinfo.value)


@patch("time.time")
def test_make_config(mock_time):
    mock_time.return_value = 1234567890

    args = {
        dsc.HOSTED_ZONE_ARG: "dev.example.com",
        dsc.NAME_SERVERS_ARG: json.dumps(["ns1.example.com", "ns2.example.com"]),
        dsc.ZONE_RESOLUTIONS_ARG: json.dumps({"www": ["192.168.1.1"]}),
        dsc.TTL_A_ARG: 300,
        dsc.TTL_NS_ARG: 86400,
        dsc.SOA_REFRESH_ARG: 7200,
        dsc.SOA_RETRY_ARG: 3600,
        dsc.SOA_EXPIRE_ARG: 1209600,
    }

    config = dsc.DNSServerConfig.make_config(args)

    assert config is not None
    assert config.abs_hosted_zone == "dev.example.com."
    assert config.soa_serial == 1234567890


def test_make_config_invalid_json_name_servers():
    args = {
        dsc.HOSTED_ZONE_ARG: "dev.example.com",
        dsc.NAME_SERVERS_ARG: "invalid json",
        dsc.ZONE_RESOLUTIONS_ARG: json.dumps({"www": ["192.168.1.1"]}),
        dsc.TTL_A_ARG: 300,
        dsc.TTL_NS_ARG: 86400,
        dsc.SOA_REFRESH_ARG: 7200,
        dsc.SOA_RETRY_ARG: 3600,
        dsc.SOA_EXPIRE_ARG: 1209600,
    }

    config = dsc.DNSServerConfig.make_config(args)
    assert config is None


def test_make_config_invalid_json_resolutions():
    args = {
        dsc.HOSTED_ZONE_ARG: "dev.example.com",
        dsc.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dsc.ZONE_RESOLUTIONS_ARG: "invalid json",
        dsc.TTL_A_ARG: 300,
        dsc.TTL_NS_ARG: 86400,
        dsc.SOA_REFRESH_ARG: 7200,
        dsc.SOA_RETRY_ARG: 3600,
        dsc.SOA_EXPIRE_ARG: 1209600,
    }

    config = dsc.DNSServerConfig.make_config(args)
    assert config is None


def test_make_config_invalid_config():
    args = {
        dsc.HOSTED_ZONE_ARG: "",  # Invalid hosted zone
        dsc.NAME_SERVERS_ARG: json.dumps(["ns1.example.com"]),
        dsc.ZONE_RESOLUTIONS_ARG: json.dumps({"www": ["192.168.1.1"]}),
        dsc.TTL_A_ARG: 300,
        dsc.TTL_NS_ARG: 86400,
        dsc.SOA_REFRESH_ARG: 7200,
        dsc.SOA_RETRY_ARG: 3600,
        dsc.SOA_EXPIRE_ARG: 1209600,
    }

    config = dsc.DNSServerConfig.make_config(args)
    assert config is None
