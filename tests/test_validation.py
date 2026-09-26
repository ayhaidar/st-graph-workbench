import pytest

from st_graph_workbench.component.styles import EdgeStyle, NodeStyle, StyleRule
from st_graph_workbench.component.validation import (
    ElementValidationError,
    validate_elements,
)


VALID_ELEMENTS = {
    "nodes": [
        {"data": {"id": "company", "label": "COMPANY"}},
        {"data": {"id": "person", "label": "PERSON", "parent": "company"}},
    ],
    "edges": [
        {
            "data": {
                "id": "works_at",
                "label": "WORKS_AT",
                "source": "person",
                "target": "company",
            }
        }
    ],
}


def test_validate_elements_accepts_valid_graph():
    validate_elements(VALID_ELEMENTS)


def test_validate_elements_rejects_missing_node_id():
    elements = {"nodes": [{"data": {"label": "PERSON"}}], "edges": []}

    with pytest.raises(ElementValidationError, match="nodes\\[0\\].data.id"):
        validate_elements(elements)


def test_validate_elements_rejects_duplicate_ids_after_string_conversion():
    elements = {
        "nodes": [
            {"data": {"id": 1, "label": "A"}},
            {"data": {"id": "1", "label": "B"}},
        ],
        "edges": [],
    }

    with pytest.raises(ElementValidationError, match="duplicate element id `1`"):
        validate_elements(elements)


def test_validate_elements_rejects_missing_edge_source():
    elements = {
        "nodes": [{"data": {"id": "a", "label": "PERSON"}}],
        "edges": [{"data": {"id": "e", "source": "a", "target": "missing"}}],
    }

    with pytest.raises(ElementValidationError, match="target `missing`"):
        validate_elements(elements)


def test_validate_elements_rejects_malformed_expansion_metadata():
    elements = {
        "nodes": [
            {
                "data": {
                    "id": "a",
                    "label": "PERSON",
                    "expansion": {"state": "open", "next_count": -1},
                }
            }
        ],
        "edges": [],
    }

    with pytest.raises(ElementValidationError, match="expansion `state`"):
        validate_elements(elements)


@pytest.mark.parametrize("count", [float("nan"), float("inf"), float("-inf")])
def test_validate_elements_rejects_non_finite_expansion_counts(count):
    elements = {
        "nodes": [
            {
                "data": {
                    "id": "vehicle",
                    "label": "VEHICLE",
                    "expansion": {"state": "collapsed", "next_count": count},
                }
            }
        ],
        "edges": [],
    }

    with pytest.raises(ElementValidationError, match="finite number"):
        validate_elements(elements)


def test_validate_elements_rejects_invalid_compound_parent():
    elements = {
        "nodes": [
            {"data": {"id": "a", "label": "PERSON", "parent": "missing"}},
        ],
        "edges": [],
    }

    with pytest.raises(ElementValidationError, match="compound parent `missing`"):
        validate_elements(elements)


def test_extended_node_style_keeps_old_fields_and_adds_raw_style():
    style = NodeStyle(
        "PERSON",
        "#123456",
        "name",
        "person",
        size=42,
        shape="diamond",
        border_color="#ffffff",
        border_width=2,
        opacity=0.8,
        label_position="center",
        text_size=8,
        raw_style={"text-wrap": "wrap"},
    ).dump()

    assert style["selector"] == "node[label='PERSON']"
    assert style["style"]["background-color"] == "#123456"
    assert style["style"]["label"] == "data(name)"
    assert style["style"]["background-image"] == "./icons/person.svg"
    assert style["style"]["width"] == 42
    assert style["style"]["height"] == 42
    assert style["style"]["shape"] == "diamond"
    assert style["style"]["border-color"] == "#ffffff"
    assert style["style"]["border-width"] == 2
    assert style["style"]["opacity"] == 0.8
    assert style["style"]["text-valign"] == "center"
    assert style["style"]["font-size"] == 8
    assert style["style"]["text-wrap"] == "wrap"


def test_extended_edge_style_and_style_rule_dump():
    edge_style = EdgeStyle(
        "WORKS_AT",
        "#654321",
        "label",
        directed=True,
        width=3,
        line_style="dashed",
        opacity=0.7,
        source_arrow="circle",
        target_arrow="vee",
        raw_style={"text-margin-y": -4},
    ).dump()
    rule = StyleRule("node:selected", {"overlay-opacity": 0.2}).dump()

    assert edge_style["style"]["target-arrow-shape"] == "vee"
    assert edge_style["style"]["source-arrow-shape"] == "circle"
    assert edge_style["style"]["width"] == 3
    assert edge_style["style"]["line-style"] == "dashed"
    assert edge_style["style"]["opacity"] == 0.7
    assert edge_style["style"]["text-margin-y"] == -4
    assert rule == {
        "selector": "node:selected",
        "style": {"overlay-opacity": 0.2},
    }
