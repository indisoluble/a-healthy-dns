#!/usr/bin/env python3

import dns.name
import pytest

from indisoluble.a_healthy_dns.records.zone_origins import ZoneOrigins

_PRIMARY = "example.com"
_ALIAS = "alias.com"


def _abs_name(name):
    return dns.name.from_text(name, origin=dns.name.root)


def _rel_name(name):
    return dns.name.from_text(name, origin=None)


def _origins(primary=_PRIMARY, aliases=None):
    aliases = [] if aliases is None else aliases
    return ZoneOrigins(primary, aliases)


class TestZoneOriginsValidation:
    @pytest.mark.parametrize(
        "invalid_primary",
        [
            None,
            123,
            1.5,
            [],
            {},
            "",
            "bad!primary",
            "example..com",
        ],
    )
    def test_init_raises_for_invalid_primary(self, invalid_primary):
        with pytest.raises(ValueError):
            ZoneOrigins(invalid_primary, [])

    @pytest.mark.parametrize(
        "invalid_alias",
        [
            None,
            123,
            1.5,
            [],
            {},
            "",
            "bad!alias",
            "alias..com",
        ],
    )
    def test_init_raises_for_invalid_alias(self, invalid_alias):
        with pytest.raises(ValueError):
            ZoneOrigins(_PRIMARY, [invalid_alias])


class TestZoneOriginsInitialization:
    def test_primary_is_parsed_as_absolute_name(self):
        origins = _origins()

        assert origins.primary == _abs_name(_PRIMARY)


class TestZoneOriginMatching:
    def test_relative_name_matches_primary_origin(self):
        origins = _origins(aliases=[_ALIAS])

        assert origins.origin_for(_rel_name("www")) == _abs_name(_PRIMARY)

    @pytest.mark.parametrize(
        "qname,expected_origin",
        [
            ("www.example.com", _PRIMARY),
            ("www.alias.com", _ALIAS),
            ("api.dev.example.com", "dev.example.com"),
        ],
    )
    def test_absolute_name_matches_hosted_or_alias_origin(self, qname, expected_origin):
        origins = _origins(aliases=[_ALIAS, "dev.example.com"])

        assert origins.origin_for(_abs_name(qname)) == _abs_name(expected_origin)

    def test_unmatched_absolute_name_returns_none(self):
        origins = _origins(aliases=[_ALIAS])

        assert origins.origin_for(_abs_name("www.other.com")) is None


class TestZoneOriginRelativization:
    def test_relative_name_is_returned_as_is(self):
        origins = _origins()
        relative_name = _rel_name("www")

        assert origins.relativize(relative_name) == relative_name

    @pytest.mark.parametrize(
        "qname,expected_relative_name",
        [
            ("www.example.com", "www"),
            ("www.alias.com", "www"),
            ("api.dev.example.com", "api"),
        ],
    )
    def test_absolute_name_under_hosted_or_alias_origin_is_relativized(
        self, qname, expected_relative_name
    ):
        origins = _origins(aliases=[_ALIAS, "dev.example.com"])

        assert origins.relativize(_abs_name(qname)) == _rel_name(expected_relative_name)

    def test_unmatched_absolute_name_returns_none(self):
        origins = _origins(aliases=[_ALIAS])

        assert origins.relativize(_abs_name("www.other.com")) is None


class TestZoneOriginsEqualityAndHashing:
    @pytest.mark.parametrize(
        "left,right",
        [
            (
                ZoneOrigins(_PRIMARY, ["alias1.com", "alias2.com"]),
                ZoneOrigins(_PRIMARY, ["alias1.com", "alias2.com"]),
            ),
            (
                ZoneOrigins(_PRIMARY, ["alias1.com", "alias2.com"]),
                ZoneOrigins(_PRIMARY, ["alias2.com", "alias1.com"]),
            ),
            (
                ZoneOrigins(_PRIMARY, ["alias1.com", "alias2.com", "alias1.com"]),
                ZoneOrigins(_PRIMARY, ["alias2.com", "alias1.com"]),
            ),
        ],
        ids=["identical", "different-alias-order", "duplicate-aliases"],
    )
    def test_equal_when_primary_and_alias_set_match(self, left, right):
        assert left == right
        assert hash(left) == hash(right)
        assert {left, right} == {left}

    @pytest.mark.parametrize(
        "other",
        [
            ZoneOrigins("other.com", []),
            ZoneOrigins(_PRIMARY, ["alias2.com"]),
            "not a ZoneOrigins",
        ],
    )
    def test_not_equal_when_identity_differs(self, other):
        assert _origins(aliases=["alias1.com"]) != other

    def test_hash_allows_use_in_set(self):
        origins = _origins(aliases=["alias1.com"])
        equivalent_origins = _origins(aliases=["alias1.com"])
        other_origins = ZoneOrigins("other.com", [])

        assert {origins, equivalent_origins, other_origins} == {
            origins,
            other_origins,
        }


class TestZoneOriginsRepresentation:
    def test_repr_shows_primary_and_aliases(self):
        origins = _origins(aliases=["alias1.com", "alias2.com"])

        result = repr(origins)

        assert "example.com." in result
        assert "alias1.com." in result
        assert "alias2.com." in result
        assert result.startswith("ZoneOrigins(")

    def test_repr_shows_no_aliases_when_empty(self):
        assert repr(_origins()) == "ZoneOrigins(primary='example.com.', aliases=[])"
