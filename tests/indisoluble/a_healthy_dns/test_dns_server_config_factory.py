#!/usr/bin/env python3

import json

import dns.dnssectypes
import dns.name
import pytest

from typing import Any, Dict
from unittest.mock import patch

from dns.dnssecalgs.rsa import PrivateRSASHA256

from indisoluble.a_healthy_dns import dns_server_config_factory as dscf
from indisoluble.a_healthy_dns.records.a_healthy_ip import AHealthyIp
from indisoluble.a_healthy_dns.records.zone_origins import ZoneOrigins

_DNSSEC_KEY_PATH = "test/path/to/private_key.pem"
_LOAD_DNSSEC_PRIVATE_KEY = (
    "indisoluble.a_healthy_dns.dns_server_config_factory._load_dnssec_private_key"
)


@pytest.fixture
def valid_args() -> Dict[str, Any]:
    return {
        dscf.ARG_HOSTED_ZONE: "dev.example.com",
        dscf.ARG_ALIAS_ZONES: json.dumps(["dev.alias-one.com", "dev.alias-two.com"]),
        dscf.ARG_NAME_SERVERS: json.dumps(
            ["ns1.dns.example.net", "ns2.dns.example.net"]
        ),
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
                    dscf.ARG_SUBDOMAIN_IP_LIST: [
                        "10.16.2.1",
                        "10.16.2.1",
                        "10.16.2.1",
                    ],
                    dscf.ARG_SUBDOMAIN_HEALTH_PORT: 8082,
                },
                "zeros": {
                    dscf.ARG_SUBDOMAIN_IP_LIST: [
                        "192.0168.000.020",
                        "0102.018.001.01",
                    ],
                    dscf.ARG_SUBDOMAIN_HEALTH_PORT: 8083,
                },
            }
        ),
        dscf.ARG_DNSSEC_PRIVATE_KEY_PATH: None,
        dscf.ARG_DNSSEC_ALGORITHM: "RSASHA256",
    }


@pytest.fixture
def args_with_dnssec(valid_args: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **valid_args,
        dscf.ARG_DNSSEC_PRIVATE_KEY_PATH: _DNSSEC_KEY_PATH,
    }


def _a_records_by_subdomain(config):
    return {record.subdomain: record.healthy_ips for record in config.a_records}


def _subdomain_name(config, subdomain):
    return dns.name.from_text(subdomain, origin=config.zone_origins.primary)


def _dnssec_private_key_pem():
    return PrivateRSASHA256.generate(key_size=2048).to_pem()


class TestMakeConfigSuccess:
    def test_builds_zone_name_servers_and_health_checked_a_records(self, valid_args):
        config = dscf.make_config(valid_args)

        assert config is not None
        assert config.ext_private_key is None
        assert config.zone_origins == ZoneOrigins(
            "dev.example.com", ["dev.alias-one.com", "dev.alias-two.com"]
        )
        assert config.name_servers == frozenset(
            ["ns1.dns.example.net.", "ns2.dns.example.net."]
        )
        assert config.primary_name_server == "ns1.dns.example.net."
        assert _a_records_by_subdomain(config) == {
            _subdomain_name(config, "www"): frozenset(
                [
                    AHealthyIp("192.168.1.1", 8080, False),
                    AHealthyIp("192.168.1.2", 8080, False),
                ]
            ),
            _subdomain_name(config, "api"): frozenset(
                [AHealthyIp("192.168.2.1", 8081, False)]
            ),
            _subdomain_name(config, "repeated"): frozenset(
                [AHealthyIp("10.16.2.1", 8082, False)]
            ),
            _subdomain_name(config, "zeros"): frozenset(
                [
                    AHealthyIp("102.18.1.1", 8083, False),
                    AHealthyIp("192.168.0.20", 8083, False),
                ]
            ),
        }

    def test_builds_standard_static_a_records_without_health_ports(self, valid_args):
        valid_args[dscf.ARG_ZONE_RESOLUTIONS] = json.dumps(
            {"standard-static": ["10.0.0.1", "10.0.0.2"]}
        )

        config = dscf.make_config(valid_args)

        assert config is not None
        assert _a_records_by_subdomain(config) == {
            _subdomain_name(config, "standard-static"): frozenset(
                [
                    AHealthyIp("10.0.0.1", None, False),
                    AHealthyIp("10.0.0.2", None, False),
                ]
            )
        }


class TestMakeConfigDnssec:
    @patch(_LOAD_DNSSEC_PRIVATE_KEY)
    def test_loads_extended_private_key_when_key_path_is_configured(
        self, mock_load_key, args_with_dnssec
    ):
        mock_load_key.return_value = _dnssec_private_key_pem()

        config = dscf.make_config(args_with_dnssec)

        assert config is not None
        mock_load_key.assert_called_once_with(_DNSSEC_KEY_PATH)
        assert config.ext_private_key is not None
        assert config.ext_private_key.private_key is not None
        assert isinstance(config.ext_private_key.private_key, PrivateRSASHA256)
        assert config.ext_private_key.dnskey is not None
        assert (
            config.ext_private_key.dnskey.algorithm
            == dns.dnssectypes.Algorithm.RSASHA256
        )
        assert config.zone_origins is not None
        assert config.name_servers is not None
        assert config.a_records is not None

    @patch(_LOAD_DNSSEC_PRIVATE_KEY)
    def test_returns_none_when_private_key_cannot_be_loaded(
        self, mock_load_key, args_with_dnssec
    ):
        mock_load_key.return_value = None

        assert dscf.make_config(args_with_dnssec) is None
        mock_load_key.assert_called_once_with(_DNSSEC_KEY_PATH)

    @patch(_LOAD_DNSSEC_PRIVATE_KEY)
    def test_returns_none_when_dnssec_algorithm_is_invalid(
        self, mock_load_key, args_with_dnssec
    ):
        mock_load_key.return_value = _dnssec_private_key_pem()
        args_with_dnssec[dscf.ARG_DNSSEC_ALGORITHM] = "INVALID_ALG"

        assert dscf.make_config(args_with_dnssec) is None
        mock_load_key.assert_called_once_with(_DNSSEC_KEY_PATH)


class TestMakeConfigInputValidation:
    @pytest.mark.parametrize(
        "invalid_zone",
        [
            "",
            "dev.example@.com",
        ],
    )
    def test_returns_none_when_hosted_zone_is_invalid(self, invalid_zone, valid_args):
        valid_args[dscf.ARG_HOSTED_ZONE] = invalid_zone

        assert dscf.make_config(valid_args) is None

    @pytest.mark.parametrize(
        "invalid_alias_zones",
        [
            "invalid json",
            json.dumps({"alias": "dev.alias-one.com"}),
            json.dumps([""]),
            json.dumps(["dev.alias-one.com", "dev.alias-@.com"]),
        ],
        ids=["not-json", "not-list", "empty-alias", "invalid-alias"],
    )
    def test_returns_none_when_alias_zones_are_invalid(
        self, invalid_alias_zones, valid_args
    ):
        valid_args[dscf.ARG_ALIAS_ZONES] = invalid_alias_zones

        assert dscf.make_config(valid_args) is None

    @pytest.mark.parametrize(
        "invalid_name_servers",
        [
            "invalid json",
            json.dumps({"ns": "ns1.dns.example.net"}),
            json.dumps([]),
            json.dumps([123]),
            json.dumps([""]),
            json.dumps(["ns1"]),
            json.dumps(["ns1.example@.com"]),
        ],
        ids=[
            "not-json",
            "not-list",
            "empty-list",
            "non-string",
            "empty-name",
            "not-fqdn",
            "invalid-character",
        ],
    )
    def test_returns_none_when_name_servers_are_invalid(
        self, invalid_name_servers, valid_args
    ):
        valid_args[dscf.ARG_NAME_SERVERS] = invalid_name_servers

        assert dscf.make_config(valid_args) is None

    @pytest.mark.parametrize(
        "invalid_resolution",
        [
            "invalid json",
            json.dumps(["192.168.1.1", 8080]),
            json.dumps({}),
            json.dumps(
                {
                    "": {
                        dscf.ARG_SUBDOMAIN_IP_LIST: ["192.168.1.1"],
                        dscf.ARG_SUBDOMAIN_HEALTH_PORT: 8080,
                    }
                }
            ),
            json.dumps(
                {
                    "www@": {
                        dscf.ARG_SUBDOMAIN_IP_LIST: ["192.168.1.1"],
                        dscf.ARG_SUBDOMAIN_HEALTH_PORT: 8080,
                    }
                }
            ),
            json.dumps({"www": ["192.168.1.1", 8080]}),
            json.dumps({"www": {}}),
            json.dumps(
                {
                    "www": {
                        dscf.ARG_SUBDOMAIN_HEALTH_PORT: 8080,
                    }
                }
            ),
            json.dumps(
                {
                    "www": {
                        dscf.ARG_SUBDOMAIN_IP_LIST: None,
                        dscf.ARG_SUBDOMAIN_HEALTH_PORT: 8080,
                    }
                }
            ),
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
                        dscf.ARG_SUBDOMAIN_IP_LIST: ["192.168.1.1"],
                        dscf.ARG_SUBDOMAIN_HEALTH_PORT: None,
                    }
                }
            ),
            json.dumps({"www": []}),
            json.dumps(
                {
                    "www": {
                        dscf.ARG_SUBDOMAIN_IP_LIST: ["192.168.1.1"],
                    }
                }
            ),
            json.dumps(
                {
                    "www": {
                        dscf.ARG_SUBDOMAIN_IP_LIST: [123],
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
        ids=[
            "not-json",
            "not-dict",
            "empty-dict",
            "empty-subdomain",
            "invalid-subdomain",
            "standard-static-invalid-ip-type",
            "empty-subconfig",
            "missing-ip-list",
            "null-ip-list",
            "ip-list-not-list",
            "empty-ip-list",
            "null-health-port",
            "standard-static-empty-ip-list",
            "missing-health-port",
            "ip-not-string",
            "ip-octet-too-large",
            "incomplete-ip",
            "health-port-not-int",
            "negative-health-port",
            "health-port-too-large",
        ],
    )
    def test_returns_none_when_zone_resolution_is_invalid(
        self, invalid_resolution, valid_args
    ):
        valid_args[dscf.ARG_ZONE_RESOLUTIONS] = invalid_resolution

        assert dscf.make_config(valid_args) is None
