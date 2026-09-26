import copy

import pytest

from st_graph_workbench import (
    delete_elements,
    get_element,
    update_element_data,
    upsert_elements,
)
from st_graph_workbench.component.component import (
    _normalize_connected_drag,
    _normalize_toolbar,
    _normalize_height,
    _normalize_option_values,
    _normalize_progressive_loading,
    _normalize_viewport_options,
    _validate_option_values,
)
from st_graph_workbench.component.validation import ElementValidationError


BASE_ELEMENTS = {
    "nodes": [
        {"data": {"id": "case", "label": "CASE", "name": "Case 1"}},
        {"data": {"id": "company", "label": "COMPANY", "name": "Northwind"}},
    ],
    "edges": [
        {
            "data": {
                "id": "case-company",
                "label": "INVESTIGATES",
                "source": "case",
                "target": "company",
            }
        }
    ],
}


def test_crud_actions_validate_known_and_unknown_values():
    _validate_option_values(
        ["expand"],
        ["create_node", "request_node_data"],
        ["add_node", "undo"],
        ["save_viewport", "restore_viewport"],
        "single",
        [],
        "default",
        "always",
        "graph-key",
    )

    with pytest.raises(ValueError, match="Unknown CRUD action"):
        _validate_option_values(
            [],
            ["bad_action"],
            [],
            [],
            "single",
            [],
            "default",
            "always",
            "graph-key",
        )

    with pytest.raises(ValueError, match="Unknown edit action"):
        _validate_option_values(
            [],
            [],
            ["bad_action"],
            [],
            "single",
            [],
            "default",
            "always",
            "graph-key",
        )

    with pytest.raises(ValueError, match="Unknown viewport action"):
        _validate_option_values(
            [],
            [],
            [],
            ["bad_action"],
            "single",
            [],
            "default",
            "always",
            "graph-key",
        )

    with pytest.raises(ValueError, match="requires a stable `key`"):
        _validate_option_values(
            [], [], [], [], "single", [], "default", "initial", None
        )


@pytest.mark.parametrize(
    ("option_index", "bad_value"),
    [
        (0, "expand"),
        (1, "create_node"),
        (2, "add_node"),
        (3, "save_viewport"),
        (5, "degree"),
        (0, ""),
        (1, ""),
        (2, ""),
        (3, ""),
        (5, ""),
        (0, 123),
    ],
)
def test_action_options_reject_bare_strings_and_non_iterables(option_index, bad_value):
    values = [
        [],
        [],
        [],
        [],
        "single",
        [],
        "default",
        "always",
        "graph-key",
    ]
    values[option_index] = bad_value

    with pytest.raises(ValueError, match="must be a list or iterable"):
        _validate_option_values(*values)


def test_action_option_normalization_materializes_iterables_once():
    values = (value for value in ["expand", "show_neighbors"])

    assert _normalize_option_values("node_actions", values) == [
        "expand",
        "show_neighbors",
    ]


def test_height_normalization_accepts_positive_integer_pixels():
    assert _normalize_height(640) == 640


@pytest.mark.parametrize("bad_height", [0, -1, True, False, "500px", 12.5, None])
def test_height_normalization_rejects_invalid_values(bad_height):
    with pytest.raises(ValueError, match="positive integer pixel height"):
        _normalize_height(bad_height)


def test_viewport_option_normalization_accepts_finite_numeric_values():
    assert _normalize_viewport_options(0.25, 3, 0.4) == (0.25, 3.0, 0.4)
    assert _normalize_viewport_options(None, None, None) == (None, None, None)


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), True, "1"])
def test_viewport_option_normalization_rejects_non_finite_numbers(bad_value):
    with pytest.raises(ValueError, match="min_zoom"):
        _normalize_viewport_options(bad_value, None, None)


def test_viewport_option_normalization_rejects_inverted_zoom_bounds():
    with pytest.raises(ValueError, match="min_zoom.*max_zoom"):
        _normalize_viewport_options(4, 2, None)


def test_progressive_loading_normalizes_defaults_and_counts():
    assert (
        _normalize_progressive_loading({"acknowledged_request_id": "request-1"})[
            "acknowledged_request_id"
        ]
        == "request-1"
    )
    assert _normalize_progressive_loading({"total_count": 250}) == {
        "page_size": 100,
        "loaded_count": 0,
        "total_count": 250,
        "has_more": True,
        "cursor": None,
        "acknowledged_request_id": None,
    }
    assert (
        _normalize_progressive_loading(
            {
                "page_size": 50,
                "loaded_count": 250,
                "total_count": 250,
                "cursor": "finished",
            }
        )["has_more"]
        is False
    )


@pytest.mark.parametrize(
    ("config", "message"),
    [
        ({"page_size": 0}, "greater than zero"),
        ({"loaded_count": -1}, "non-negative integer"),
        ({"loaded_count": 4, "total_count": 3}, "cannot exceed"),
        ({"has_more": "yes"}, "must be a boolean"),
        ({"cursor": {"page": 2}}, "finite JSON scalar"),
        ({"acknowledged_request_id": ""}, "non-empty string"),
        ({"acknowledged_request_id": "   "}, "non-empty string"),
        ({"acknowledged_request_id": 4}, "non-empty string"),
        ({"unknown": 1}, "Unknown `progressive_loading` field"),
    ],
)
def test_progressive_loading_rejects_invalid_configuration(config, message):
    with pytest.raises((TypeError, ValueError), match=message):
        _normalize_progressive_loading(config)


def test_connected_drag_normalizes_defaults():
    assert _normalize_connected_drag({}) == {
        "enabled": False,
        "depth": 1,
        "max_depth": 3,
        "max_nodes": 100,
    }


def test_connected_drag_normalizes_explicit_values():
    assert _normalize_connected_drag(
        {"enabled": True, "depth": 2, "max_depth": 2, "max_nodes": 25}
    ) == {
        "enabled": True,
        "depth": 2,
        "max_depth": 2,
        "max_nodes": 25,
    }
    assert _normalize_connected_drag(None) is None


@pytest.mark.parametrize(
    ("config", "message"),
    [
        ([], "must be a mapping"),
        ({"enabled": 1}, "enabled.*boolean"),
        ({"depth": 0}, "depth.*1, 2, or 3"),
        ({"depth": 4}, "depth.*1, 2, or 3"),
        ({"max_depth": 2.0}, "max_depth.*1, 2, or 3"),
        ({"depth": 3, "max_depth": 2}, "cannot exceed"),
        ({"max_nodes": 0}, "positive integer"),
        ({"max_nodes": True}, "positive integer"),
        ({"unknown": True}, "Unknown `connected_drag` field"),
    ],
)
def test_connected_drag_rejects_invalid_configuration(config, message):
    with pytest.raises((TypeError, ValueError), match=message):
        _normalize_connected_drag(config)


def test_toolbar_normalizes_defaults_and_explicit_values():
    assert _normalize_toolbar(None) == {
        "mode": "adaptive",
        "position": "top",
        "collapsible": True,
        "sticky": True,
    }
    assert _normalize_toolbar(
        {
            "mode": "compact",
            "position": "top",
            "collapsible": False,
            "sticky": False,
        }
    ) == {
        "mode": "compact",
        "position": "top",
        "collapsible": False,
        "sticky": False,
    }


@pytest.mark.parametrize(
    ("config", "message"),
    [
        ("adaptive", "must be a mapping"),
        ({"unknown": True}, "Unknown `toolbar` field"),
        ({"mode": "wide"}, "`toolbar.mode`"),
        ({"position": "bottom"}, "`toolbar.position`"),
        ({"collapsible": 1}, "`toolbar.collapsible`"),
        ({"sticky": "yes"}, "`toolbar.sticky`"),
    ],
)
def test_toolbar_rejects_invalid_configuration(config, message):
    with pytest.raises((TypeError, ValueError), match=message):
        _normalize_toolbar(config)


@pytest.mark.parametrize("bad_sensitivity", [0, -0.2])
def test_viewport_option_normalization_rejects_nonpositive_wheel_sensitivity(
    bad_sensitivity,
):
    with pytest.raises(ValueError, match="wheel_sensitivity"):
        _normalize_viewport_options(None, None, bad_sensitivity)


def test_get_element_returns_copy():
    element = get_element(BASE_ELEMENTS, "company")

    assert element == {
        "data": {"id": "company", "label": "COMPANY", "name": "Northwind"}
    }
    assert element is not BASE_ELEMENTS["nodes"][1]


def test_upsert_elements_adds_nodes_and_edges_without_mutating_input():
    original = copy.deepcopy(BASE_ELEMENTS)

    result = upsert_elements(
        BASE_ELEMENTS,
        nodes={"data": {"id": "alice", "label": "PERSON", "name": "Alice"}},
        edges={
            "data": {
                "id": "company-alice",
                "label": "DIRECTOR",
                "source": "company",
                "target": "alice",
            }
        },
    )

    assert BASE_ELEMENTS == original
    assert get_element(result, "alice")["data"]["name"] == "Alice"
    assert get_element(result, "company-alice")["data"]["target"] == "alice"


def test_upsert_elements_merges_existing_data_when_replace_is_false():
    result = upsert_elements(
        BASE_ELEMENTS,
        nodes={"data": {"id": "company", "risk": 9}},
        replace=False,
    )

    assert get_element(result, "company")["data"] == {
        "id": "company",
        "label": "COMPANY",
        "name": "Northwind",
        "risk": 9,
    }


def test_update_element_data_replaces_or_merges_data():
    merged = update_element_data(BASE_ELEMENTS, "company", {"risk": 7})
    replaced = update_element_data(
        BASE_ELEMENTS,
        "company",
        {"id": "company", "label": "ORG"},
        merge=False,
    )

    assert get_element(merged, "company")["data"]["risk"] == 7
    assert get_element(merged, "company")["data"]["name"] == "Northwind"
    assert get_element(replaced, "company")["data"] == {
        "id": "company",
        "label": "ORG",
    }


def test_update_element_data_rejects_element_id_changes():
    with pytest.raises(ValueError, match="data.id cannot be changed"):
        update_element_data(BASE_ELEMENTS, "company", {"id": "renamed_company"})

    with pytest.raises(ValueError, match="data.id cannot be changed"):
        update_element_data(
            BASE_ELEMENTS,
            "case-company",
            {
                "id": "renamed_edge",
                "source": "case",
                "target": "company",
            },
            merge=False,
        )


def test_update_element_data_requires_matching_id_when_replacing_data():
    with pytest.raises(ValueError, match="must include a matching `id`"):
        update_element_data(
            BASE_ELEMENTS,
            "company",
            {"label": "ORG"},
            merge=False,
        )


def test_delete_elements_removes_incident_edges_by_default():
    result = delete_elements(BASE_ELEMENTS, node_ids=["company"])

    assert get_element(result, "company") is None
    assert get_element(result, "case-company") is None


def test_delete_elements_treats_string_ids_as_single_ids():
    node_result = delete_elements(BASE_ELEMENTS, node_ids="company")
    edge_result = delete_elements(BASE_ELEMENTS, edge_ids="case-company")

    assert get_element(node_result, "company") is None
    assert get_element(node_result, "case-company") is None
    assert get_element(edge_result, "company") is not None
    assert get_element(edge_result, "case-company") is None


@pytest.mark.parametrize("node_id", [7, 2.5, True])
def test_delete_elements_accepts_scalar_numeric_and_boolean_ids(node_id):
    elements = {
        "nodes": [{"data": {"id": node_id, "label": "ENTITY"}}],
        "edges": [],
    }

    assert delete_elements(elements, node_ids=node_id) == {"nodes": [], "edges": []}


@pytest.mark.parametrize("bad_ids", [{"company": True}, ["company", {"bad": True}]])
def test_delete_elements_rejects_container_id_inputs(bad_ids):
    with pytest.raises(TypeError, match="node_ids/edge_ids"):
        delete_elements(BASE_ELEMENTS, node_ids=bad_ids)


def test_delete_elements_can_reject_dangling_edges():
    with pytest.raises(ElementValidationError, match="target `company`"):
        delete_elements(
            BASE_ELEMENTS,
            node_ids=["company"],
            remove_incident_edges=False,
        )


def test_upsert_elements_rejects_string_and_scalar_element_inputs():
    with pytest.raises(TypeError, match="Element inputs must be dicts"):
        upsert_elements(BASE_ELEMENTS, nodes="bad")

    with pytest.raises(TypeError, match="Element inputs must be dicts"):
        upsert_elements(BASE_ELEMENTS, edges=123)

    with pytest.raises(TypeError, match="Element inputs must be dicts"):
        upsert_elements(BASE_ELEMENTS, nodes=[{"data": {"id": "valid"}}, "bad"])


def test_upsert_elements_rejects_edges_pointing_to_missing_nodes():
    with pytest.raises(ElementValidationError, match="target `missing`"):
        upsert_elements(
            BASE_ELEMENTS,
            edges={
                "data": {
                    "id": "bad-edge",
                    "label": "BAD",
                    "source": "case",
                    "target": "missing",
                }
            },
        )
