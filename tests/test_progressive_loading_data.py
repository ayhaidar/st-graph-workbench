from copy import deepcopy

import pytest

from examples.progressive_loading_data import (
    bfs_result_rows,
    graph_through,
    location_nodes,
    record_batch,
)
from st_graph_workbench import (
    add_elements_command,
    apply_graph_command,
    validate_elements,
)


@pytest.mark.parametrize("cross_locations", [False, True])
def test_progressive_pages_match_source_without_moving_existing_records(
    cross_locations,
):
    graph = {"nodes": location_nodes(), "edges": []}
    for start in range(0, 600, 60):
        before = deepcopy(graph)
        batch = record_batch(start, start + 60, cross_locations=cross_locations)
        graph = apply_graph_command(
            graph, add_elements_command(f"page-{start}", **batch)
        )
        validate_elements(graph)
        assert graph == graph_through(start + 60, cross_locations=cross_locations)
        assert graph["nodes"][: len(before["nodes"])] == before["nodes"]
        assert graph["edges"][: len(before["edges"])] == before["edges"]


@pytest.mark.parametrize("stop,extra_edges", [(60, 0), (120, 1), (180, 2), (600, 2)])
def test_cross_location_sightings_arrive_with_their_vehicle(stop, extra_edges):
    graph = graph_through(stop, cross_locations=True)
    assert len(graph["nodes"]) == stop + 3
    assert len(graph["edges"]) == stop + extra_edges
    sightings = [
        edge["data"] for edge in graph["edges"] if edge["data"]["label"] == "SEEN_AT"
    ]
    assert len(sightings) == extra_edges
    if extra_edges:
        assert (sightings[0]["source"], sightings[0]["target"]) == (
            "vehicle-0061",
            "location-central",
        )
    if extra_edges == 2:
        assert (sightings[1]["source"], sightings[1]["target"]) == (
            "vehicle-0122",
            "location-south",
        )


@pytest.mark.parametrize("stop", [100, 600, 1_000, 5_000, 10_000])
def test_scale_activity_has_predictable_node_and_edge_counts(stop):
    graph = graph_through(stop)
    assert len(graph["nodes"]) == stop + 3
    assert len(graph["edges"]) == stop
    assert graph["nodes"][0]["data"]["id"] == "location-north"
    assert graph["nodes"][-1]["data"]["id"] == f"vehicle-{stop:04d}"


def test_bfs_rows_follow_discovery_edges_in_either_direction_without_mutation():
    graph = {
        "nodes": [{"data": {"id": node_id, "label": "RECORD"}} for node_id in "abcd"],
        "edges": [
            {"data": {"id": edge_id, "source": source, "target": target}}
            for edge_id, source, target in [
                ("ab", "a", "b"),
                ("ca", "c", "a"),
                ("bd", "b", "d"),
                ("dc", "d", "c"),
            ]
        ],
    }
    result = {"root_id": "a", "node_ids": list("abcd"), "edge_ids": ["ab", "ca", "bd"]}
    original = deepcopy((graph, result))
    rows = bfs_result_rows(graph, result)
    assert [row["hops"] for row in rows] == [0, 1, 1, 2]
    assert [row["discovered_from"] for row in rows] == [None, "a", "a", "b"]
    assert [row["visit_order"] for row in rows] == [1, 2, 3, 4]
    assert (graph, result) == original
    assert (
        bfs_result_rows(graph, {"root_id": "d", "node_ids": ["d"], "edge_ids": []})[0][
            "hops"
        ]
        == 0
    )
