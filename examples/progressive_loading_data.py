"""Deterministic pages and readable BFS results for the progressive-loading demo."""

import math

TOTAL_RECORDS = 600
INITIAL_RECORDS = 60
PAGE_SIZE = 60
LOCATIONS = (
    ("location-north", "North interchange", 300, 250),
    ("location-central", "Central depot", 650, 380),
    ("location-south", "South terminal", 980, 250),
)

# These extra sightings only arrive with their vehicle's page.
CROSS_LOCATION_SIGHTINGS = {
    60: ("location-central", "08:15"),
    121: ("location-south", "09:30"),
}


def location_nodes():
    return [
        {
            "data": {
                "id": location_id,
                "label": "LOCATION",
                "name": name,
                "region": name.split()[0],
            },
            "position": {"x": x, "y": y},
        }
        for location_id, name, x, y in LOCATIONS
    ]


def record_batch(start: int, stop: int, *, cross_locations: bool = False):
    """Return the half-open page [start, stop); never move previously loaded nodes."""
    nodes = []
    edges = []
    for index in range(start, stop):
        location_id, _, center_x, center_y = LOCATIONS[index % len(LOCATIONS)]
        ring = 1 + index // 36
        angle = math.radians((index * 137.5) % 360)
        radius = 70 + ring * 18
        record_id = f"vehicle-{index + 1:04d}"
        nodes.append(
            {
                "data": {
                    "id": record_id,
                    "label": "VEHICLE",
                    "name": f"Fleet vehicle {index + 1:04d}",
                    "route": f"R-{(index % 24) + 1:02d}",
                    "service_window": f"{6 + index % 16:02d}:00",
                },
                "position": {
                    "x": round(center_x + math.cos(angle) * radius, 2),
                    "y": round(center_y + math.sin(angle) * radius, 2),
                },
            }
        )
        edges.append(
            {
                "data": {
                    "id": f"assignment-{index + 1:04d}",
                    "label": "SERVES",
                    "source": record_id,
                    "target": location_id,
                    "sequence": index + 1,
                }
            }
        )
        if cross_locations and index in CROSS_LOCATION_SIGHTINGS:
            target, seen_at = CROSS_LOCATION_SIGHTINGS[index]
            edges.append(
                {
                    "data": {
                        "id": f"sighting-{index + 1:04d}",
                        "label": "SEEN_AT",
                        "source": record_id,
                        "target": target,
                        "seen_at": seen_at,
                    }
                }
            )
    return {"nodes": nodes, "edges": edges}


def graph_through(stop: int, *, cross_locations: bool = False):
    batch = record_batch(0, stop, cross_locations=cross_locations)
    return {"nodes": [*location_nodes(), *batch["nodes"]], "edges": batch["edges"]}


def bfs_result_rows(elements: dict, result: dict) -> list[dict]:
    """Join Cytoscape's visit order/tree edges to records, without rerunning BFS."""
    nodes = {node["data"]["id"]: node["data"] for node in elements["nodes"]}
    edges = {edge["data"]["id"]: edge["data"] for edge in elements["edges"]}
    depths = {result["root_id"]: 0}
    rows = []
    for order, node_id in enumerate(result["node_ids"]):
        parent = None
        if order:
            # Each non-root visit has one incoming discovery edge in the payload.
            edge = edges[result["edge_ids"][order - 1]]
            parent = edge["target"] if edge["source"] == node_id else edge["source"]
            depths[node_id] = depths[parent] + 1
        data = nodes[node_id]
        rows.append(
            {
                "visit_order": order + 1,
                "hops": depths[node_id],
                "id": node_id,
                "name": data.get("name", node_id),
                "type": data.get("label"),
                "discovered_from": parent,
                "route": data.get("route"),
                "service_window": data.get("service_window"),
            }
        )
    return rows
