from __future__ import annotations

from datetime import datetime

import pytest

from pollution import randdata as rd


def test_random_date_uses_the_requested_date_range(monkeypatch):
    """randomDate should pass the requested bounds through to Faker."""
    captured = {}
    expected = datetime(2024, 5, 17, 12, 30)

    def fake_date_time_between_dates(*, datetime_start, datetime_end):
        captured["start"] = datetime_start
        captured["end"] = datetime_end
        return expected

    monkeypatch.setattr(rd.faker, "date_time_between_dates", fake_date_time_between_dates)

    result = rd.randomDate(datetime(2020, 1, 1), datetime(2020, 12, 31))

    assert result is expected
    assert captured["start"] == datetime(2020, 1, 1)
    assert captured["end"] == datetime(2020, 12, 31)


def test_random_date_string_formats_the_generated_datetime(monkeypatch):
    """randomDateStr should format the date with one of the configured patterns."""
    fixed_date = datetime(2024, 5, 17, 12, 30)
    monkeypatch.setattr(rd, "randomDate", lambda *args, **kwargs: fixed_date)
    monkeypatch.setattr(rd.random, "choice", lambda options: options[0])

    assert rd.randomDateStr() == "2024-05-17"


def test_random_int_uses_faker_integer_generation(monkeypatch):
    """randomInt should delegate to Faker's integer generator."""
    captured = {}

    def fake_random_int(*, min, max):
        captured["min"] = min
        captured["max"] = max
        return 42

    monkeypatch.setattr(rd.faker, "random_int", fake_random_int)

    assert rd.randomInt(min=10, max=20) == 42
    assert captured == {"min": 10, "max": 20}


def test_random_float_rounds_to_the_requested_precision(monkeypatch):
    """randomFloat should round the sampled value to the requested precision."""
    monkeypatch.setattr(rd.random, "uniform", lambda min_value, max_value: 12.3456789)

    assert rd.randomFloat(min_value=0.0, max_value=100.0, precision=3) == 12.346


def test_random_digit_text_returns_one_spelled_out_number(monkeypatch):
    """randomDigitText should return one of the spelled-out digits."""
    monkeypatch.setattr(rd.faker, "random_element", lambda elements: "seven")

    assert rd.randomDigitText() == "seven"


def test_random_currency_returns_one_currency_marker(monkeypatch):
    """randomCurrency should return one of the supported currency labels."""
    monkeypatch.setattr(rd.faker, "random_element", lambda elements: "€")

    assert rd.randomCurrency() == "€"


@pytest.mark.parametrize(
    ("chosen_case", "expected"),
    [
        (rd.NumberLike.INT, "17"),
        (rd.NumberLike.FLOAT, "3.5"),
        (rd.NumberLike.AS_TEXT, "one two"),
    ],
)
def test_random_number_like_handles_the_simple_cases(monkeypatch, chosen_case, expected):
    """randomNumberLike should handle the int, float, and text branches."""
    monkeypatch.setattr(rd.faker, "random_element", lambda elements: chosen_case)
    monkeypatch.setattr(rd, "randomInt", lambda: 17)
    monkeypatch.setattr(rd, "randomFloat", lambda: 3.5)
    monkeypatch.setattr(rd.random, "randint", lambda min_value, max_value: 2)

    if chosen_case is rd.NumberLike.AS_TEXT:
        digit_words = iter(["one", "two"])
        monkeypatch.setattr(rd, "randomDigitText", lambda: next(digit_words))
        assert rd.randomNumberLike() == expected
    else:
        monkeypatch.setattr(rd, "randomDigitText", lambda: "one")
        assert rd.randomNumberLike() == expected


def test_random_number_like_can_build_currency_prefixes(monkeypatch):
    """randomNumberLike should be able to place the currency before the value."""
    monkeypatch.setattr(rd.faker, "random_element", lambda elements: rd.NumberLike.CURRENCY)
    monkeypatch.setattr(rd.faker, "boolean", lambda: True)
    monkeypatch.setattr(rd, "randomInt", lambda: 17)
    monkeypatch.setattr(rd, "randomCurrency", lambda: "€")

    assert rd.randomNumberLike() == "€17"


def test_random_number_like_can_build_currency_suffixes(monkeypatch):
    """randomNumberLike should be able to place the currency after the value."""
    boolean_values = iter([False, False])
    monkeypatch.setattr(rd.faker, "random_element", lambda elements: rd.NumberLike.CURRENCY)
    monkeypatch.setattr(rd.faker, "boolean", lambda: next(boolean_values))
    monkeypatch.setattr(rd, "randomFloat", lambda: 3.5)
    monkeypatch.setattr(rd, "randomCurrency", lambda: "$")

    assert rd.randomNumberLike() == "3.5 $"


def test_random_string_uses_an_ascii_alphanumeric_alphabet(monkeypatch):
    """randomString should build a string with the requested length."""
    monkeypatch.setattr(rd.random, "randint", lambda min_length, max_length: 6)
    monkeypatch.setattr(rd.random, "choices", lambda alphabet, k: list("Ab12Cd"))

    assert rd.randomString(min_length=4, max_length=8) == "Ab12Cd"


def test_random_bool_str_returns_one_supported_boolean_string(monkeypatch):
    """randomBoolStr should return one of the known boolean text values."""
    monkeypatch.setattr(rd.faker, "random_element", lambda elements: "yes")

    assert rd.randomBoolStr() == "yes"


def test_random_null_returns_one_supported_null_string(monkeypatch):
    """randomNull should return one of the known null text values."""
    monkeypatch.setattr(rd.faker, "random_element", lambda elements: "NULL")

    assert rd.randomNull() == "NULL"


@pytest.mark.parametrize(
    ("chosen_type", "expected"),
    [
        (rd.RandomType.NUMBER, "99"),
        (rd.RandomType.DATE_STR, "2024-05-17"),
        (rd.RandomType.STRING, "sample-text"),
        (rd.RandomType.BOOL_STR, "false"),
        (rd.RandomType.NULL, "NaN"),
    ],
)
def test_random_type_routes_to_the_expected_generator(monkeypatch, chosen_type, expected):
    """randomType should delegate to the generator that matches the chosen type."""
    monkeypatch.setattr(rd.faker, "random_element", lambda elements: chosen_type)
    monkeypatch.setattr(rd, "randomNumberLike", lambda: "99")
    monkeypatch.setattr(rd, "randomDateStr", lambda *args, **kwargs: "2024-05-17")
    monkeypatch.setattr(rd, "randomString", lambda *args, **kwargs: "sample-text")
    monkeypatch.setattr(rd, "randomBoolStr", lambda: "false")
    monkeypatch.setattr(rd, "randomNull", lambda: "NaN")

    assert rd.randomType() == expected


def test_random_json_returns_a_primitive_when_the_depth_limit_is_reached(monkeypatch):
    """randomJson should stop recursing once it reaches max_depth."""
    monkeypatch.setattr(rd.random, "choice", lambda options: options[0])
    monkeypatch.setattr(rd.faker, "name", lambda: "Ada Lovelace")

    assert rd.randomJson(depth=1, max_depth=1) == "Ada Lovelace"


def test_random_json_can_build_a_small_array(monkeypatch):
    """randomJson should be able to build a list when the array branch is chosen."""
    def choose_array_branch(options):
        if options and isinstance(options[0], str) and set(options) == {"object", "array", "primitive"}:
            return "array"
        return options[0]

    monkeypatch.setattr(rd.random, "choice", choose_array_branch)
    monkeypatch.setattr(rd.random, "randint", lambda min_value, max_value: 2)
    monkeypatch.setattr(rd.faker, "name", lambda: "Ada")

    assert rd.randomJson(max_depth=1, max_array_size=2) == ["Ada", "Ada"]


def test_random_json_can_build_a_small_object(monkeypatch):
    """randomJson should be able to build a dict when the object branch is chosen."""
    key_values = iter(["left", "right"])

    def choose_object_branch(options):
        if options and isinstance(options[0], str) and set(options) == {"object", "array", "primitive"}:
            return "object"
        return options[0]

    monkeypatch.setattr(rd.random, "choice", choose_object_branch)
    monkeypatch.setattr(rd.random, "randint", lambda min_value, max_value: 2)
    monkeypatch.setattr(rd.faker, "word", lambda: next(key_values))
    monkeypatch.setattr(rd.faker, "name", lambda: "Ada")

    assert rd.randomJson(max_depth=1, max_object_size=2) == {"left": "Ada", "right": "Ada"}


def test_random_json_str_serializes_the_generated_object(monkeypatch):
    """randomJsonStr should JSON-encode whatever randomJson returns."""
    monkeypatch.setattr(rd, "randomJson", lambda **kwargs: {"hello": [1, 2, 3]})

    assert rd.randomJsonStr(max_depth=1) == '{"hello": [1, 2, 3]}'
