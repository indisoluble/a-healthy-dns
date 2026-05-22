#!/usr/bin/env python3

import pytest

from indisoluble.a_healthy_dns.tools.is_valid_subdomain import (
    is_valid_fqdn,
    is_valid_subdomain,
)

_LABEL_ERROR = "Labels must contain only alphanumeric characters or hyphens"


def _assert_valid(result):
    success, message = result

    assert success is True
    assert message == ""


def _assert_invalid(result, expected_message):
    success, message = result

    assert success is False
    assert message == expected_message


class TestValidSubdomains:
    @pytest.mark.parametrize(
        "valid_subdomain",
        [
            "example",
            "sub-domain",
            "sub.domain",
            "sub-domain.example",
            "123.example",
            "example123",
            "123domain456",
            "a",
            "1",
            "a-1-b",
            "a.b.c.d",
            "a.b.c.d.e",
        ],
    )
    def test_accepts_subdomain(self, valid_subdomain):
        _assert_valid(is_valid_subdomain(valid_subdomain))


class TestInvalidSubdomains:
    @pytest.mark.parametrize(
        "invalid_subdomain",
        [
            None,
            123,
            1.5,
            [],
            {},
        ],
    )
    def test_rejects_non_string_values(self, invalid_subdomain):
        _assert_invalid(is_valid_subdomain(invalid_subdomain), "It must be a string")

    def test_rejects_empty_string(self):
        _assert_invalid(is_valid_subdomain(""), "It cannot be empty")

    @pytest.mark.parametrize(
        "invalid_subdomain",
        [
            "domain@example",
            "domain_example",
            "domain.example!",
            "domain..example",
            ".domain",
            "domain.",
            "domain example",
        ],
    )
    def test_rejects_invalid_labels(self, invalid_subdomain):
        _assert_invalid(is_valid_subdomain(invalid_subdomain), _LABEL_ERROR)

    @pytest.mark.parametrize(
        "invalid_subdomain",
        [
            " example",
            "example ",
            "sub domain",
        ],
    )
    def test_rejects_whitespace(self, invalid_subdomain):
        _assert_invalid(is_valid_subdomain(invalid_subdomain), _LABEL_ERROR)


class TestValidFqdns:
    @pytest.mark.parametrize(
        "valid_fqdn",
        [
            "ns1.example.com",
            "sub-domain.example",
            "a.b",
        ],
    )
    def test_accepts_dotted_hostname(self, valid_fqdn):
        _assert_valid(is_valid_fqdn(valid_fqdn))


class TestInvalidFqdns:
    def test_rejects_hostname_without_dot(self):
        _assert_invalid(
            is_valid_fqdn("ns1"),
            "It must be a fully-qualified hostname",
        )

    def test_rejects_empty_string(self):
        _assert_invalid(is_valid_fqdn(""), "It cannot be empty")

    def test_rejects_invalid_labels(self):
        _assert_invalid(is_valid_fqdn("ns1.example@.com"), _LABEL_ERROR)
