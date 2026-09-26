"""Deterministic lesson checkpoints, shared with the feature-lab sample data."""

from copy import deepcopy
import math

from demos.demo_helpers import SIGHTING_RECORDS, build_sighting_graph
from st_graph_workbench import delete_elements, upsert_elements


CRUD_NODE_TYPES = {
    "PLACE": "Location",
    "VEHICLE": "Vehicle",
    "PERSON": "Person",
    "PHONE": "Phone",
    "CAMERA": "Camera",
    "TIME": "Time",
    "CHECKPOINT": "Checkpoint",
}


def first_graph():
    """Return fresh input records so one lesson cannot mutate another's data."""
    return {
        # id is the stable identifier; label is the category used for styling.
        "nodes": [
            {"data": {"id": "ABC123", "label": "VEHICLE", "name": "ABC123"}},
            {"data": {"id": "location_1", "label": "PLACE", "name": "Location 1"}},
        ],
        "edges": [
            {
                "data": {
                    "id": "sighting-1",
                    # Endpoints refer to node IDs, not their display names.
                    "source": "ABC123",
                    "target": "location_1",
                    "label": "Seen At",
                    # Application properties stay inside data alongside the ID.
                    "Time": SIGHTING_RECORDS[0]["Time"],
                }
            }
        ],
    }


def checkpoint():
    graph = build_sighting_graph(SIGHTING_RECORDS)
    positions = {
        "ALPHA": (80, 50),
        "BETA": (440, 50),
        "ABC123": (260, 150),
        "location_1": (80, 150),
        "location_2": (440, 150),
        "12VEC": (260, 300),
        "location_3": (440, 300),
    }
    for node in graph["nodes"]:
        x, y = positions[node["data"]["id"]]
        node["position"] = {"x": x, "y": y}
    return graph


def related_records():
    return {
        "nodes": [
            {
                "data": {"id": "camera-7", "label": "CAMERA", "name": "Camera 7"},
                "position": {"x": 600, "y": 200},
            },
            {
                "data": {"id": "time-0814", "label": "TIME", "name": "08:14"},
                "position": {"x": 600, "y": 350},
            },
        ],
        "edges": [
            {
                "data": {
                    "id": "captured-7",
                    "source": "ABC123",
                    "target": "camera-7",
                    "label": "Related",
                }
            },
            {
                "data": {
                    "id": "recorded-0814",
                    "source": "camera-7",
                    "target": "time-0814",
                    "label": "Related",
                }
            },
        ],
    }


def expansion_graph(elements, expanded=False):
    graph = deepcopy(elements)
    available = related_records()
    visible = {node["data"]["id"] for node in graph["nodes"]}
    missing = sum(node["data"]["id"] not in visible for node in available["nodes"])
    for node in graph["nodes"]:
        if node["data"]["id"] == "ABC123":
            node["data"]["expansion"] = (
                {"state": "expanded", "collapse_count": 2 - missing}
                if expanded
                else {"state": "collapsed", "next_count": missing}
            )
    return graph


def toggle_related(elements, expanded):
    if expanded:
        return delete_elements(elements, node_ids=["camera-7", "time-0814"])
    return upsert_elements(elements, **related_records())


def fleet_graph(count, *, compound=False):
    """Keep positions fixed as counts grow; location hubs are never duplicated."""
    graph = {"nodes": [], "edges": []}
    if compound:
        # A parent must exist as a node before children can refer to its ID.
        graph["nodes"].append(
            {"data": {"id": "fleet", "label": "GROUP", "name": "Fleet"}}
        )
    for index in range(3):
        graph["nodes"].append(
            {
                "data": {
                    "id": f"hub-{index}",
                    "label": "PLACE",
                    "name": f"Location {index + 1}",
                },
                "position": {"x": index * 450, "y": 200},
            }
        )
    for index in range(count):
        # Coordinates depend only on the index, not on the requested total count.
        angle = index * 2.4
        radius = 55 + (index // 3) ** 0.5 * 18
        data = {
            "id": f"vehicle-{index}",
            "label": "VEHICLE",
            "name": f"Vehicle {index}",
            "time": f"{6 + index % 16:02}:00",
        }
        if compound:
            # Containment uses data.parent; it does not create an extra edge.
            data["parent"] = "fleet"
        graph["nodes"].append(
            {
                "data": data,
                "position": {
                    "x": index % 3 * 450 + math.cos(angle) * radius,
                    "y": 200 + math.sin(angle) * radius,
                },
            }
        )
        graph["edges"].append(
            {
                "data": {
                    "id": f"visit-{index}",
                    "source": data["id"],
                    "target": f"hub-{index % 3}",
                    "label": "Seen At",
                }
            }
        )
    return graph
