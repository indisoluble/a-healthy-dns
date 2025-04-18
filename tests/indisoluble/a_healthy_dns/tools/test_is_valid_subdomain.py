#!/usr/bin/env python3

import pytest

from indisoluble.a_healthy_dns.tools.is_valid_subdomain import is_valid_subdomain


def test_valid_subdomains():
    valid_subdomains = [
        "example",
        "sub-domain",
        "sub.domain",
        "sub-domain.example",
        "123.example",
        "example123",
        "a",
        "1",
        "a-1-b",
        "a.b.c.d",
    ]

    for subdomain in valid_subdomains:
        result, message = is_valid_subdomain(subdomain)
        assert result is True
        assert message == ""


@pytest.mark.parametrize(
    "invalid_subdomain,expected_message",
    [
        ("", "It cannot be empty"),
        (
            "domain@example",
            "Labels must contain only alphanumeric characters or hyphens",
        ),
        (
            "domain_example",
            "Labels must contain only alphanumeric characters or hyphens",
        ),
        (
            "domain.example!",
            "Labels must contain only alphanumeric characters or hyphens",
        ),
        (
            "domain..example",
            "Labels must contain only alphanumeric characters or hyphens",
        ),
        (".domain", "Labels must contain only alphanumeric characters or hyphens"),
        ("domain.", "Labels must contain only alphanumeric characters or hyphens"),
        (
            "domain example",
            "Labels must contain only alphanumeric characters or hyphens",
        ),
    ],
)
def test_invalid_subdomains(invalid_subdomain, expected_message):
    result, message = is_valid_subdomain(invalid_subdomain)
    assert result is False
    assert message == expected_message


def test_subdomain_with_whitespace():
    result, message = is_valid_subdomain(" example")
    assert result is False
    assert "Labels must contain only alphanumeric characters or hyphens" == message

    result, message = is_valid_subdomain("example ")
    assert result is False
    assert "Labels must contain only alphanumeric characters or hyphens" == message

    result, message = is_valid_subdomain("sub domain")
    assert result is False
    assert "Labels must contain only alphanumeric characters or hyphens" == message


def test_subdomain_special_cases():
    # Test with hyphens
    result, message = is_valid_subdomain("sub-domain")
    assert result is True
    assert message == ""

    # Test with numbers
    result, message = is_valid_subdomain("123domain456")
    assert result is True
    assert message == ""

    # Test with multiple dots
    result, message = is_valid_subdomain("a.b.c.d.e")
    assert result is True
    assert message == ""
