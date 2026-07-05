# GPL-3.0-or-later
# Unit tests for the bpy-free value/payload helpers in values.py.

from _loader import load_module, run_tests

values = load_module("phynodes_values", "values.py")


# -- parse_payload ----------------------------------------------------------

def test_parse_none_is_zero():
    assert values.parse_payload(None) == 0.0


def test_parse_json_scalar():
    assert values.parse_payload("42") == 42.0
    assert values.parse_payload(" 3.5 ") == 3.5


def test_parse_json_array():
    assert values.parse_payload("[1, 2, 3]") == [1, 2, 3]


def test_parse_json_nested_array():
    assert values.parse_payload("[[1, 2], [3, 4]]") == [[1, 2], [3, 4]]


def test_parse_json_object():
    assert values.parse_payload('{"x": 1.5}') == {"x": 1.5}


def test_parse_csv():
    assert values.parse_payload("1,2,3") == [1.0, 2.0, 3.0]


def test_parse_csv_mixed_tokens():
    assert values.parse_payload("a,2") == ["a", 2.0]


def test_parse_semicolon_groups():
    assert values.parse_payload("1,2;3,4") == [[1.0, 2.0], [3.0, 4.0]]


def test_parse_single_value_with_trailing_comma_is_not_array():
    # fewer than 2 items -> not treated as CSV; "5," is not a number either,
    # so it falls all the way through to the raw string
    assert values.parse_payload("5,") == "5,"


def test_parse_plain_string():
    assert values.parse_payload("hello") == "hello"


# -- format_for_mqtt --------------------------------------------------------

def test_format_array_is_json():
    assert values.format_for_mqtt([1, 2]) == "[1, 2]"


def test_format_bool_is_numeric():
    assert values.format_for_mqtt(True) == "1"
    assert values.format_for_mqtt(False) == "0"


def test_format_scalar():
    assert values.format_for_mqtt(1.5) == "1.5"


def test_roundtrip_array():
    payload = values.format_for_mqtt([1.0, 2.5])
    assert values.parse_payload(payload) == [1.0, 2.5]


# -- coercions ---------------------------------------------------------------

def test_to_float_safe():
    assert values.to_float_safe(True) == 1.0
    assert values.to_float_safe("2.5") == 2.5
    assert values.to_float_safe("nope", default=7.0) == 7.0
    assert values.to_float_safe([3.0, 9.0]) == 3.0  # first element
    assert values.to_float_safe(None) == 0.0


def test_to_bool_safe():
    assert values.to_bool_safe("on") == 1.0
    assert values.to_bool_safe("TRUE") == 1.0
    assert values.to_bool_safe(0.4) == 0.0
    assert values.to_bool_safe(0.6) == 1.0


def test_flatten_array():
    assert values.flatten_array([1, [2, [3, 4]], 5]) == [1, 2, 3, 4, 5]


if __name__ == "__main__":
    run_tests(globals())
