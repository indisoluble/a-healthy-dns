#!/usr/bin/env python3

"""Tests for multi-domain config factory functionality."""

import dns.name

import pytest

from indisoluble.a_healthy_dns.dns_server_config_factory import (
    ARG_ALIAS_ZONES,
    ARG_DNSSEC_PRIVATE_KEY_PATH,
    ARG_HOSTED_ZONE,
    ARG_NAME_SERVERS,
    ARG_ZONE_RESOLUTIONS,
    make_config,
)


def test_make_config_with_alias_zones():
    """Test that alias zones are properly parsed and included in config."""
    args = {
        ARG_HOSTED_ZONE: "primary.com",
        ARG_ALIAS_ZONES: '["alias1.com", "alias2.com"]',
        ARG_ZONE_RESOLUTIONS: '{"www": {"ips": ["192.168.1.1"], "health_port": 8080}}',
        ARG_NAME_SERVERS: '["ns1.primary.com"]',
        ARG_DNSSEC_PRIVATE_KEY_PATH: None,
    }
    
    config = make_config(args)
    
    assert config is not None
    assert len(config.alias_zones) == 2
    assert dns.name.from_text("alias1.com.") in config.alias_zones
    assert dns.name.from_text("alias2.com.") in config.alias_zones


def test_make_config_without_alias_zones():
    """Test that config works without alias zones."""
    args = {
        ARG_HOSTED_ZONE: "primary.com",
        ARG_ZONE_RESOLUTIONS: '{"www": {"ips": ["192.168.1.1"], "health_port": 8080}}',
        ARG_NAME_SERVERS: '["ns1.primary.com"]',
        ARG_DNSSEC_PRIVATE_KEY_PATH: None,
    }
    
    config = make_config(args)
    
    assert config is not None
    assert len(config.alias_zones) == 0


def test_make_config_with_empty_alias_zones():
    """Test that empty alias zones list is handled correctly."""
    args = {
        ARG_HOSTED_ZONE: "primary.com",
        ARG_ALIAS_ZONES: '[]',
        ARG_ZONE_RESOLUTIONS: '{"www": {"ips": ["192.168.1.1"], "health_port": 8080}}',
        ARG_NAME_SERVERS: '["ns1.primary.com"]',
        ARG_DNSSEC_PRIVATE_KEY_PATH: None,
    }
    
    config = make_config(args)
    
    assert config is not None
    assert len(config.alias_zones) == 0


def test_make_config_with_invalid_alias_zone():
    """Test that invalid alias zones are skipped with a warning."""
    args = {
        ARG_HOSTED_ZONE: "primary.com",
        ARG_ALIAS_ZONES: '["alias1.com", "invalid@domain"]',
        ARG_ZONE_RESOLUTIONS: '{"www": {"ips": ["192.168.1.1"], "health_port": 8080}}',
        ARG_NAME_SERVERS: '["ns1.primary.com"]',
        ARG_DNSSEC_PRIVATE_KEY_PATH: None,
    }
    
    config = make_config(args)
    
    assert config is not None
    # Only the valid alias zone should be included
    assert len(config.alias_zones) == 1
    assert dns.name.from_text("alias1.com.") in config.alias_zones


def test_make_config_with_invalid_json_alias_zones():
    """Test that invalid JSON for alias zones is handled gracefully."""
    args = {
        ARG_HOSTED_ZONE: "primary.com",
        ARG_ALIAS_ZONES: 'invalid json',
        ARG_ZONE_RESOLUTIONS: '{"www": {"ips": ["192.168.1.1"], "health_port": 8080}}',
        ARG_NAME_SERVERS: '["ns1.primary.com"]',
        ARG_DNSSEC_PRIVATE_KEY_PATH: None,
    }
    
    config = make_config(args)
    
    # Config should still be created with empty alias zones
    assert config is not None
    assert len(config.alias_zones) == 0


def test_make_config_with_non_list_alias_zones():
    """Test that non-list alias zones are handled gracefully."""
    args = {
        ARG_HOSTED_ZONE: "primary.com",
        ARG_ALIAS_ZONES: '{"zone": "alias1.com"}',
        ARG_ZONE_RESOLUTIONS: '{"www": {"ips": ["192.168.1.1"], "health_port": 8080}}',
        ARG_NAME_SERVERS: '["ns1.primary.com"]',
        ARG_DNSSEC_PRIVATE_KEY_PATH: None,
    }
    
    config = make_config(args)
    
    # Config should still be created with empty alias zones
    assert config is not None
    assert len(config.alias_zones) == 0
