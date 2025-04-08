#!/usr/bin/env python3

import pytest

import indisoluble.a_healthy_dns.dns_server_config as dsc


def test_valid_config():
    config = dsc.DNSServerConfig(
        hosted_zone="dev.example.com",
        name_servers=["ns1.example.com", "ns2.example.com"],
        resolutions={
            "www": {"ips": ["192.168.1.1", "192.168.1.2"], "health_port": 8080}
        },
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
    assert config.healthy_ips("www.dev.example.com.") == ["192.168.1.1", "192.168.1.2"]


def test_config_healthy_ips():
    config = dsc.DNSServerConfig(
        hosted_zone="dev.example.com",
        name_servers=["ns1.example.com", "ns2.example.com"],
        resolutions={
            "www": {"ips": ["192.168.1.1", "192.168.1.2"], "health_port": 8080}
        },
        ttl_a=300,
        ttl_ns=86400,
        soa_serial=1234567890,
        soa_refresh=7200,
        soa_retry=3600,
        soa_expire=1209600,
    )

    assert not config.healthy_ips("www2.dev.example.com.")

    assert config.healthy_ips("www.dev.example.com.") == ["192.168.1.1", "192.168.1.2"]
    config.disable_ip("192.168.1.1", 8080)
    assert config.healthy_ips("www.dev.example.com.") == ["192.168.1.2"]
    config.disable_ip("192.168.1.2", 8080)
    assert not config.healthy_ips("www.dev.example.com.")
    config.enable_ip("192.168.1.1", 8080)
    assert config.healthy_ips("www.dev.example.com.") == ["192.168.1.1"]
    config.enable_ip("192.168.1.2", 9090)
    assert config.healthy_ips("www.dev.example.com.") == ["192.168.1.1"]


def test_invalid_hosted_zone():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="invalid domain!",
            name_servers=["ns1.example.com"],
            resolutions={"www": {"ips": ["192.168.1.1"], "health_port": 8080}},
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
            resolutions={"www": {"ips": ["192.168.1.1"], "health_port": 8080}},
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
            resolutions={"www": {"ips": ["192.168.1.1"], "health_port": 8080}},
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
            resolutions={"www": {"ips": ["192.168.1.1"], "health_port": 8080}},
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "Name servers must be a list" in str(excinfo.value)


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


def test_invalid_subdomain_in_resolutions():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="dev.example.com",
            name_servers=["ns1.example.com"],
            resolutions={
                "invalid*subdomain": {"ips": ["192.168.1.1"], "health_port": 8080}
            },
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "not valid" in str(excinfo.value)


def test_no_health_port_in_resolutions():
    with pytest.raises(KeyError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="dev.example.com",
            name_servers=["ns1.example.com"],
            resolutions={"www": {"ips": ["192.168.1.1"]}},
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "health_port" in str(excinfo.value)


def test_invalid_health_port_in_resolutions():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="dev.example.com",
            name_servers=["ns1.example.com"],
            resolutions={"www": {"ips": ["192.168.1.1"], "health_port": 70000}},
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "not valid" in str(excinfo.value)


def test_no_int_health_port_in_resolutions():
    with pytest.raises(TypeError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="dev.example.com",
            name_servers=["ns1.example.com"],
            resolutions={"www": {"ips": ["192.168.1.1"], "health_port": "8080"}},
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "not supported" in str(excinfo.value)


def test_no_ips_in_resolutions():
    with pytest.raises(KeyError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="dev.example.com",
            name_servers=["ns1.example.com"],
            resolutions={"www": {"health_port": 8080}},
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "ips" in str(excinfo.value)


def test_empty_ip_list_in_resolutions():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="example.com",
            name_servers=["ns1.example.com"],
            resolutions={"www": {"ips": [], "health_port": 8080}},
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "IP list for 'www' cannot be empty" in str(excinfo.value)


def test_invalid_ip_address_in_resolution():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="example.com",
            name_servers=["ns1.example.com"],
            resolutions={"www": {"ips": ["192.168.1.300"], "health_port": 8080}},
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=1209600,
        )
    assert "Invalid IP address" in str(excinfo.value)


def test_ips_no_list_type_in_resolutions():
    with pytest.raises(ValueError) as excinfo:
        dsc.DNSServerConfig(
            hosted_zone="example.com",
            name_servers=["ns1.example.com"],
            resolutions={"www": {"ips": "192.168.1.300", "health_port": 8080}},
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
            resolutions={"www": {"ips": ["192.168.1.1"], "health_port": 8080}},
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
            resolutions={"www": {"ips": ["192.168.1.1"], "health_port": 8080}},
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
            resolutions={"www": {"ips": ["192.168.1.1"], "health_port": 8080}},
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
            resolutions={"www": {"ips": ["192.168.1.1"], "health_port": 8080}},
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
            resolutions={"www": {"ips": ["192.168.1.1"], "health_port": 8080}},
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
            resolutions={"www": {"ips": ["192.168.1.1"], "health_port": 8080}},
            ttl_a=300,
            ttl_ns=86400,
            soa_serial=1234567890,
            soa_refresh=7200,
            soa_retry=3600,
            soa_expire=0,
        )
    assert "SOA expire value must be positive" in str(excinfo.value)
