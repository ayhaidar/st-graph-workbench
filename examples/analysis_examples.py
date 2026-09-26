from __future__ import annotations

from collections import deque
from typing import Any

from st_graph_workbench import Elements


def _node_ids(elements: Elements) -> list[str]:
    return [str(node["data"]["id"]) for node in elements.get("nodes", [])]


def _edge_rows(elements: Elements) -> list[dict[str, str]]:
    return [
        {
            "id": str(edge["data"]["id"]),
            "source": str(edge["data"]["source"]),
            "target": str(edge["data"]["target"]),
        }
        for edge in elements.get("edges", [])
    ]


def _adjacency(elements: Elements) -> dict[str, list[tuple[str, str]]]:
    graph = {node_id: [] for node_id in _node_ids(elements)}
    for edge in _edge_rows(elements):
        graph.setdefault(edge["source"], []).append((edge["target"], edge["id"]))
        graph.setdefault(edge["target"], []).append((edge["source"], edge["id"]))
    return graph


def _shortest_path(
    elements: Elements,
    source: str,
    target: str,
) -> dict[str, Any]:
    graph = _adjacency(elements)
    queue: deque[tuple[str, list[str], list[str]]] = deque([(source, [source], [])])
    seen = {source}

    while queue:
        node_id, node_path, edge_path = queue.popleft()
        if node_id == target:
            return {
                "analysis": "shortest_path",
                "source_id": source,
                "target_id": target,
                "distance": len(edge_path),
                "node_ids": sorted(node_path),
                "edge_ids": sorted(edge_path),
            }

        for neighbor_id, edge_id in graph.get(node_id, []):
            if neighbor_id in seen:
                continue
            seen.add(neighbor_id)
            queue.append(
                (
                    neighbor_id,
                    [*node_path, neighbor_id],
                    [*edge_path, edge_id],
                )
            )

    return {
        "analysis": "shortest_path",
        "source_id": source,
        "target_id": target,
        "distance": float("inf"),
        "node_ids": [],
        "edge_ids": [],
    }


def _traversal(elements: Elements, root: str, kind: str) -> dict[str, Any]:
    graph = _adjacency(elements)
    visited_nodes: list[str] = []
    visited_edges: list[str] = []
    seen: set[str] = set()

    if kind == "bfs":
        pending: deque[tuple[str, str | None]] = deque([(root, None)])
        pop_next = pending.popleft
        push_next = pending.append
    else:
        pending = deque([(root, None)])
        pop_next = pending.pop

        def push_next(item: tuple[str, str | None]) -> None:
            pending.append(item)

    while pending:
        node_id, via_edge_id = pop_next()
        if node_id in seen:
            continue
        seen.add(node_id)
        visited_nodes.append(node_id)
        if via_edge_id is not None:
            visited_edges.append(via_edge_id)

        neighbors = graph.get(node_id, [])
        if kind == "dfs":
            neighbors = list(reversed(neighbors))
        for neighbor_id, edge_id in neighbors:
            if neighbor_id not in seen:
                push_next((neighbor_id, edge_id))

    return {
        "analysis": kind,
        "root_id": root,
        "node_ids": visited_nodes,
        "edge_ids": visited_edges,
    }


def _connected_components(elements: Elements) -> dict[str, Any]:
    graph = _adjacency(elements)
    edge_rows = _edge_rows(elements)
    seen: set[str] = set()
    components: list[dict[str, list[str]]] = []

    for start_id in _node_ids(elements):
        if start_id in seen:
            continue
        pending = deque([start_id])
        component_nodes: set[str] = set()

        while pending:
            node_id = pending.popleft()
            if node_id in seen:
                continue
            seen.add(node_id)
            component_nodes.add(node_id)
            for neighbor_id, _edge_id in graph.get(node_id, []):
                if neighbor_id not in seen:
                    pending.append(neighbor_id)

        component_edges = [
            edge["id"]
            for edge in edge_rows
            if edge["source"] in component_nodes and edge["target"] in component_nodes
        ]
        components.append(
            {
                "node_ids": sorted(component_nodes),
                "edge_ids": sorted(component_edges),
            }
        )

    return {"analysis": "connected_components", "components": components}


def _degree(elements: Elements, node_id: str) -> dict[str, Any]:
    connected_edges = [
        edge
        for edge in _edge_rows(elements)
        if edge["source"] == node_id or edge["target"] == node_id
    ]
    return {
        "analysis": "degree",
        "node_id": node_id,
        "degree": len(connected_edges),
        "indegree": len(
            [edge for edge in connected_edges if edge["target"] == node_id]
        ),
        "outdegree": len(
            [edge for edge in connected_edges if edge["source"] == node_id]
        ),
        "edge_ids": sorted(edge["id"] for edge in connected_edges),
    }


def analysis_example_payloads(
    elements: Elements,
    *,
    shortest_path: tuple[str, str],
    traversal_root: str,
    degree_node: str,
) -> list[dict[str, Any]]:
    source_id, target_id = shortest_path
    return [
        {
            "title": "Shortest path",
            "selection": f"Select `{source_id}` and `{target_id}`.",
            "data": _shortest_path(elements, source_id, target_id),
        },
        {
            "title": "Breadth-first search",
            "selection": f"Select `{traversal_root}`.",
            "data": _traversal(elements, traversal_root, "bfs"),
        },
        {
            "title": "Depth-first search",
            "selection": f"Select `{traversal_root}`.",
            "data": _traversal(elements, traversal_root, "dfs"),
        },
        {
            "title": "Connected components",
            "selection": "No selection is required.",
            "data": _connected_components(elements),
        },
        {
            "title": "Degree",
            "selection": f"Select `{degree_node}`.",
            "data": _degree(elements, degree_node),
        },
    ]


def analysis_example_rows(examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for example in examples:
        data = example["data"]
        if data["analysis"] == "connected_components":
            components = data["components"]
            rows.append(
                {
                    "analysis action": data["analysis"],
                    "selection": example["selection"],
                    "result size": f"{len(components)} component(s)",
                    "main fields": "components[].node_ids, components[].edge_ids",
                }
            )
            continue

        rows.append(
            {
                "analysis action": data["analysis"],
                "selection": example["selection"],
                "result size": (
                    f"{len(data.get('node_ids', []))} node(s), "
                    f"{len(data.get('edge_ids', []))} edge(s)"
                ),
                "main fields": ", ".join(
                    key
                    for key in data
                    if key not in {"analysis", "node_ids", "edge_ids"}
                ),
            }
        )
    return rows
