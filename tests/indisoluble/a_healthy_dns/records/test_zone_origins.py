#!/usr/bin/env python3

import dns.name
import pytest

from indisoluble.a_healthy_dns.records.zone_origins import ZoneOrigins


def test_primary_is_parsed_as_absolute_name():
    origins = ZoneOrigins("example.com", [])

    assert origins.primary == dns.name.from_text("example.com", origin=dns.name.root)


def test_init_raises_for_invalid_primary():
    with pytest.raises(ValueError) as exc_info:
        ZoneOrigins("", [])

    assert str(exc_info.value) == "Invalid domain '': It cannot be empty"


def test_init_raises_for_invalid_alias():
    with pytest.raises(ValueError) as exc_info:
        ZoneOrigins("example.com", ["bad!alias"])

    assert (
        str(exc_info.value)
        == "Invalid domain 'bad!alias': Labels must contain only alphanumeric "
        "characters or hyphens"
    )


def test_relativize_keeps_relative_name_as_is():
    origins = ZoneOrigins("example.com", [])
    relative_name = dns.name.from_text("www", origin=None)

    result = origins.relativize(relative_name)

    assert result is relative_name


def test_relativize_absolute_name_under_primary():
    origins = ZoneOrigins("example.com", [])
    absolute_name = dns.name.from_text("www.example.com", origin=dns.name.root)

    result = origins.relativize(absolute_name)

    assert result == dns.name.from_text("www", origin=None)


def test_relativize_absolute_name_under_alias():
    origins = ZoneOrigins("example.com", ["alias.com"])
    absolute_name = dns.name.from_text("www.alias.com", origin=dns.name.root)

    result = origins.relativize(absolute_name)

    assert result == dns.name.from_text("www", origin=None)


def test_relativize_returns_none_for_unmatched_absolute_name():
    origins = ZoneOrigins("example.com", ["alias.com"])
    absolute_name = dns.name.from_text("www.unknown.com", origin=dns.name.root)

    result = origins.relativize(absolute_name)

    assert result is None


def test_relativize_prefers_most_specific_matching_origin():
    origins = ZoneOrigins("example.com", ["dev.example.com"])
    absolute_name = dns.name.from_text("api.dev.example.com", origin=dns.name.root)

    result = origins.relativize(absolute_name)

    assert result == dns.name.from_text("api", origin=None)


def test_eq_returns_true_for_identical_zone_origins():
    origins1 = ZoneOrigins("example.com", ["alias1.com", "alias2.com"])
    origins2 = ZoneOrigins("example.com", ["alias1.com", "alias2.com"])

    assert origins1 == origins2


def test_eq_returns_true_for_same_zones_different_order():
    origins1 = ZoneOrigins("example.com", ["alias1.com", "alias2.com"])
    origins2 = ZoneOrigins("example.com", ["alias2.com", "alias1.com"])

    assert origins1 == origins2


def test_eq_returns_false_for_different_primary():
    origins1 = ZoneOrigins("example.com", [])
    origins2 = ZoneOrigins("other.com", [])

    assert origins1 != origins2


def test_eq_returns_false_for_different_aliases():
    origins1 = ZoneOrigins("example.com", ["alias1.com"])
    origins2 = ZoneOrigins("example.com", ["alias2.com"])

    assert origins1 != origins2


def test_eq_returns_not_implemented_for_non_zone_origins():
    origins = ZoneOrigins("example.com", [])

    assert origins.__eq__("not a ZoneOrigins") == NotImplemented


def test_hash_is_consistent():
    origins1 = ZoneOrigins("example.com", ["alias1.com", "alias2.com"])
    origins2 = ZoneOrigins("example.com", ["alias2.com", "alias1.com"])

    assert hash(origins1) == hash(origins2)


def test_hash_allows_use_in_set():
    origins1 = ZoneOrigins("example.com", ["alias1.com"])
    origins2 = ZoneOrigins("example.com", ["alias1.com"])
    origins3 = ZoneOrigins("other.com", [])

    zone_set = {origins1, origins2, origins3}

    assert len(zone_set) == 2  # origins1 and origins2 are the same


def test_repr_shows_primary_and_aliases():
    origins = ZoneOrigins("example.com", ["alias1.com", "alias2.com"])

    result = repr(origins)

    assert "example.com." in result
    assert "alias1.com." in result
    assert "alias2.com." in result
    assert result.startswith("ZoneOrigins(")


def test_repr_shows_no_aliases_when_empty():
    origins = ZoneOrigins("example.com", [])

    result = repr(origins)

    assert "example.com." in result
    assert result == "ZoneOrigins(primary='example.com.', aliases=[])"
