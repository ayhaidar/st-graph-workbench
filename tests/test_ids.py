import math

import pytest

from st_graph_workbench.component._ids import normalize_id, normalize_id_list


@pytest.mark.parametrize(
    ("value", "expected"),
    [("vehicle", "vehicle"), (7, "7"), (2.5, "2.5"), (True, "True")],
)
def test_scalar_identifiers_normalize_consistently(value, expected: str) -> None:
    assert normalize_id(value, option_name="element_id") == expected
    assert normalize_id_list(value, option_name="element_ids") == [expected]


def test_identifier_iterables_preserve_input_order() -> None:
    assert normalize_id_list(["vehicle", 7, 2.5, False], option_name="element_ids") == [
        "vehicle",
        "7",
        "2.5",
        "False",
    ]


@pytest.mark.parametrize(
    "value",
    [None, "", b"bytes", math.nan, math.inf, {"id": "vehicle"}, ["nested"]],
)
def test_invalid_identifier_values_fail_with_a_clear_error(value) -> None:
    with pytest.raises(TypeError, match="element_id"):
        normalize_id(value, option_name="element_id")


def test_nested_identifier_containers_are_rejected() -> None:
    with pytest.raises(TypeError, match="element_ids"):
        normalize_id_list(["vehicle", ["nested"]], option_name="element_ids")
