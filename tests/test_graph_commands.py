import copy

import pytest

from st_graph_workbench import (
    GraphCommandValidationError,
    add_elements_command,
    apply_graph_command,
    apply_graph_commands,
    clear_graph_command,
    delete_elements_command,
    get_element,
    graph_workbench,
    set_elements_command,
    update_data_command,
    upsert_elements_command,
    validate_graph_commands,
    viewport_command,
)


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


def test_upsert_command_updates_python_graph_without_mutating_input():
    original = copy.deepcopy(BASE_ELEMENTS)
    command = upsert_elements_command(
        "load-company-1",
        nodes={"data": {"id": "invoice", "label": "DOCUMENT", "name": "INV-1"}},
        edges={
            "data": {
                "id": "company-invoice",
                "label": "ISSUED",
                "source": "company",
                "target": "invoice",
            }
        },
    )

    result = apply_graph_command(BASE_ELEMENTS, command)

    assert BASE_ELEMENTS == original
    assert get_element(result, "invoice")["data"]["name"] == "INV-1"
    assert get_element(result, "company-invoice")["data"]["source"] == "company"


def test_update_and_delete_commands_apply_in_order():
    commands = [
        update_data_command(
            "update-company-1",
            "company",
            {"id": "company", "label": "COMPANY", "risk": 9},
            merge=True,
        ),
        delete_elements_command("delete-company-1", node_ids=["company"]),
    ]

    result = apply_graph_commands(BASE_ELEMENTS, commands)

    assert get_element(result, "company") is None
    assert get_element(result, "case-company") is None


def test_command_validation_tracks_nodes_added_earlier_in_batch():
    commands = [
        add_elements_command(
            "add-location-1",
            nodes={"data": {"id": "location", "label": "PLACE"}},
        ),
        add_elements_command(
            "add-company-location-1",
            edges={
                "data": {
                    "id": "company-location",
                    "label": "SEEN_AT",
                    "source": "company",
                    "target": "location",
                }
            },
        ),
    ]

    validate_graph_commands(commands, elements=BASE_ELEMENTS)
    result = apply_graph_commands(BASE_ELEMENTS, commands)

    assert get_element(result, "location")["data"]["label"] == "PLACE"
    assert get_element(result, "company-location")["data"]["target"] == "location"


def test_command_validation_tracks_nodes_deleted_earlier_in_batch():
    commands = [
        delete_elements_command("delete-company-1", node_ids=["company"]),
        add_elements_command(
            "add-stale-edge-1",
            edges={
                "data": {
                    "id": "case-company-again",
                    "label": "STALE",
                    "source": "case",
                    "target": "company",
                }
            },
        ),
    ]

    with pytest.raises(GraphCommandValidationError, match="target `company`"):
        validate_graph_commands(commands, elements=BASE_ELEMENTS)


def test_delete_command_rejects_dangling_incident_edges_when_not_removing_them():
    command = delete_elements_command(
        "delete-company-keep-edges",
        node_ids=["company"],
        remove_incident_edges=False,
    )

    with pytest.raises(GraphCommandValidationError, match="incident edge"):
        validate_graph_commands([command], elements=BASE_ELEMENTS)


def test_delete_command_can_keep_incident_edge_removal_explicit():
    command = delete_elements_command(
        "delete-company-and-edge",
        node_ids=["company"],
        edge_ids=["case-company"],
        remove_incident_edges=False,
    )

    validate_graph_commands([command], elements=BASE_ELEMENTS)
    result = apply_graph_command(BASE_ELEMENTS, command)

    assert get_element(result, "company") is None
    assert get_element(result, "case-company") is None


@pytest.mark.parametrize("element_id", [7, 2.5, True])
def test_delete_command_accepts_scalar_numeric_and_boolean_ids(element_id):
    command = delete_elements_command("delete-scalar-id", node_ids=element_id)

    assert command["node_ids"] == [str(element_id)]


@pytest.mark.parametrize("bad_ids", [{"company": True}, ["company", {"bad": True}]])
def test_delete_command_rejects_container_id_inputs(bad_ids):
    with pytest.raises(GraphCommandValidationError, match="node_ids/edge_ids"):
        delete_elements_command("delete-bad-ids", node_ids=bad_ids)

    with pytest.raises(GraphCommandValidationError, match="node_ids/edge_ids"):
        validate_graph_commands(
            [
                {
                    "command_id": "delete-bad-ids-raw",
                    "operation": "delete_elements",
                    "node_ids": bad_ids,
                }
            ]
        )


def test_update_data_command_rejects_missing_edge_endpoint():
    command = update_data_command(
        "retarget-edge-bad",
        "case-company",
        {"source": "case", "target": "missing"},
    )

    with pytest.raises(GraphCommandValidationError, match="target `missing`"):
        validate_graph_commands([command], elements=BASE_ELEMENTS)


def test_update_data_command_can_target_node_added_earlier_in_batch():
    commands = [
        add_elements_command(
            "add-location-1",
            nodes={"data": {"id": "location", "label": "PLACE"}},
        ),
        update_data_command(
            "retarget-edge-1",
            "case-company",
            {"source": "case", "target": "location"},
        ),
    ]

    validate_graph_commands(commands, elements=BASE_ELEMENTS)
    result = apply_graph_commands(BASE_ELEMENTS, commands)

    assert get_element(result, "case-company")["data"]["target"] == "location"


def test_replace_edge_data_requires_endpoints_when_not_merging():
    command = update_data_command(
        "replace-edge-bad",
        "case-company",
        {"id": "case-company", "label": "Replaced"},
        merge=False,
    )

    with pytest.raises(GraphCommandValidationError, match="source.*target"):
        validate_graph_commands([command], elements=BASE_ELEMENTS)


def test_replace_data_requires_matching_id_when_not_merging():
    with pytest.raises(GraphCommandValidationError, match="matching `id`"):
        update_data_command(
            "replace-node-bad",
            "company",
            {"label": "COMPANY", "name": "Renamed"},
            merge=False,
        )


def test_update_data_command_rejects_element_id_changes():
    with pytest.raises(GraphCommandValidationError, match="cannot change `data.id`"):
        update_data_command(
            "rename-node-bad",
            "company",
            {"id": "renamed-company", "label": "COMPANY"},
        )

    with pytest.raises(GraphCommandValidationError, match="cannot change `data.id`"):
        update_data_command(
            "rename-edge-bad",
            "case-company",
            {"id": "renamed-edge", "source": "case", "target": "company"},
        )


def test_update_data_command_rejects_missing_element_when_elements_are_known():
    command = update_data_command(
        "missing-update-1",
        "missing-element",
        {"label": "UNKNOWN"},
    )

    with pytest.raises(GraphCommandValidationError, match="missing-element"):
        validate_graph_commands([command], elements=BASE_ELEMENTS)


def test_command_validation_forgets_incident_edges_after_node_delete():
    commands = [
        delete_elements_command("delete-company-1", node_ids=["company"]),
        update_data_command(
            "update-deleted-edge-1",
            "case-company",
            {"source": "case", "target": "missing"},
        ),
    ]

    with pytest.raises(GraphCommandValidationError, match="case-company"):
        validate_graph_commands(commands, elements=BASE_ELEMENTS)


def test_set_and_clear_commands_replace_python_graph():
    replacement = {
        "nodes": [{"data": {"id": "only", "label": "NODE"}}],
        "edges": [],
    }

    replaced = apply_graph_command(
        BASE_ELEMENTS, set_elements_command("reset-1", replacement)
    )
    cleared = apply_graph_command(replaced, clear_graph_command("clear-1"))

    assert [node["data"]["id"] for node in replaced["nodes"]] == ["only"]
    assert cleared == {"nodes": [], "edges": []}


def test_add_command_rejects_duplicate_python_ids():
    command = add_elements_command(
        "add-company-1",
        nodes={"data": {"id": "company", "label": "COMPANY"}},
    )

    with pytest.raises(KeyError, match="already exists"):
        apply_graph_command(BASE_ELEMENTS, command)


def test_command_validation_rejects_bad_shape_and_edge_refs():
    with pytest.raises(GraphCommandValidationError, match="command_id"):
        validate_graph_commands([{"operation": "fit"}])

    with pytest.raises(GraphCommandValidationError, match="unknown operation"):
        validate_graph_commands([{"command_id": "bad-1", "operation": "bad"}])

    with pytest.raises(GraphCommandValidationError, match="target `missing`"):
        validate_graph_commands(
            [
                upsert_elements_command(
                    "bad-edge-1",
                    edges={
                        "data": {
                            "id": "bad-edge",
                            "label": "BAD",
                            "source": "case",
                            "target": "missing",
                        }
                    },
                )
            ],
            elements=BASE_ELEMENTS,
        )


@pytest.mark.parametrize("validate", [True, False])
def test_graph_workbench_rejects_empty_dict_graph_commands(validate):
    with pytest.raises(GraphCommandValidationError, match="graph_commands"):
        graph_workbench(
            BASE_ELEMENTS,
            graph_commands={},
            validate=validate,
            key=f"bad-commands-{validate}",
        )


def test_graph_workbench_rejects_invalid_height_before_mounting():
    with pytest.raises(ValueError, match="positive integer pixel height"):
        graph_workbench(BASE_ELEMENTS, height=0, key="bad-height")


def test_viewport_command_is_valid_and_non_mutating():
    command = viewport_command("fit-1", "fit", padding=80)
    result = apply_graph_command(BASE_ELEMENTS, command)

    assert command == {"command_id": "fit-1", "operation": "fit", "padding": 80}
    assert result == BASE_ELEMENTS
    assert result is not BASE_ELEMENTS


def test_viewport_commands_validate_navigation_options():
    validate_graph_commands(
        [
            viewport_command("zoom-1", "zoom", level=1.5),
            viewport_command(
                "zoom-anchor",
                "zoom",
                level=1.25,
                renderedPosition={"x": 120, "y": 80},
                duration=120,
            ),
            viewport_command("pan-1", "pan", pan={"x": 10, "y": -20}),
            viewport_command(
                "viewport-1", "set_viewport", zoom=0.8, pan={"x": 1, "y": 2}
            ),
            viewport_command("fit-animated", "fit", padding=0, duration=90),
            viewport_command("bounds-1", "set_zoom_bounds", min_zoom=0.2, max_zoom=3),
            viewport_command("viewport-default-zoom", "set_viewport", zoom=None),
            viewport_command(
                "bounds-defaults", "set_zoom_bounds", min_zoom=None, max_zoom=None
            ),
        ]
    )

    with pytest.raises(GraphCommandValidationError, match="numeric"):
        validate_graph_commands(
            [{"command_id": "bad-zoom", "operation": "zoom", "level": "far"}]
        )

    with pytest.raises(GraphCommandValidationError, match="pan"):
        validate_graph_commands(
            [{"command_id": "bad-pan", "operation": "pan", "pan": {"x": 1}}]
        )

    with pytest.raises(GraphCommandValidationError, match="finite numeric"):
        viewport_command("bad-nan-zoom", "zoom", level=float("nan"))

    with pytest.raises(GraphCommandValidationError, match="zero or greater"):
        viewport_command("bad-duration", "center", duration=-1)

    with pytest.raises(GraphCommandValidationError, match="zero or greater"):
        viewport_command("bad-padding", "fit", padding=-1)

    with pytest.raises(GraphCommandValidationError, match="renderedPosition"):
        viewport_command("bad-anchor", "zoom", level=1.2, renderedPosition={"x": 1})

    with pytest.raises(GraphCommandValidationError, match="min_zoom"):
        viewport_command("bad-bounds", "set_zoom_bounds", min_zoom=4, max_zoom=2)


def test_run_layout_commands_accept_named_and_dictionary_layouts():
    named = viewport_command("circle-layout", "run_layout", layout="circle")
    configured = viewport_command(
        "dagre-layout",
        "run_layout",
        layout={"name": "dagre", "rankDir": "LR", "fit": False},
    )

    assert named["layout"] == "circle"
    assert configured["layout"]["name"] == "dagre"


@pytest.mark.parametrize(
    "layout",
    [
        {"fit": True},
        {"name": "not-registered"},
        "not-registered",
    ],
)
def test_run_layout_commands_reject_invalid_layouts(layout):
    with pytest.raises(GraphCommandValidationError, match="layout"):
        viewport_command("bad-layout", "run_layout", layout=layout)
