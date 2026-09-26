"""Indexed in-memory expansion and contextual search over ordinary graph records."""

from collections import defaultdict, deque
from copy import deepcopy
from typing import Any

from ._expansion_contract import (
    normalize_elements,
    normalize_query,
    parse_instant,
    positive_limit,
)
from .expansion import ExpansionRequest, ExpansionResponse
from .types import Elements


class InMemoryExpansionProvider:
    """Expand dataframe-derived dictionaries without modifying the source graph.

    Pages contain distinct neighboring nodes and all matching edges to them.
    Relationship labels and direction filter edges; attributes match the merged
    edge/neighbor data (neighbor values win). Time filters use ISO-8601 values
    from the configured edge field, falling back to the neighboring node field.
    ``search`` returns verified paths from supplied roots, not isolated matches.
    """

    def __init__(self, elements: Elements) -> None:
        self._elements = normalize_elements(elements)
        self._nodes = {str(n["data"]["id"]): n for n in self._elements["nodes"]}
        self._adjacency: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for edge in self._elements["edges"]:
            for node_id in {str(edge["data"]["source"]), str(edge["data"]["target"])}:
                self._adjacency[node_id].append(edge)

    def _neighbors(
        self, node_id: str, query: dict[str, Any]
    ) -> dict[str, list[dict[str, Any]]]:
        query = normalize_query(query)
        start = parse_instant(query["time_from"]) if query.get("time_from") else None
        end = parse_instant(query["time_to"]) if query.get("time_to") else None
        neighbors: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for edge in self._adjacency.get(node_id, []):
            data = edge["data"]
            source, target = str(data["source"]), str(data["target"])
            if query["direction"] == "incoming" and target != node_id:
                continue
            if query["direction"] == "outgoing" and source != node_id:
                continue
            if (
                query["relationships"]
                and data.get("label") not in query["relationships"]
            ):
                continue
            other = target if source == node_id else source
            neighbor = self._nodes[other]["data"]
            merged = {**data, **neighbor}
            if any(
                key not in merged or merged[key] != value
                for key, value in query["attributes"].items()
            ):
                continue
            field = query.get("time_field", "observed_at")
            value = data.get(field, neighbor.get(field))
            if start is not None or end is not None:
                if value is None:
                    continue
                instant = parse_instant(value)
                if start is not None and instant < start:
                    continue
                if end is not None and instant > end:
                    continue
            neighbors[other].append(edge)
        return neighbors

    def _context_nodes(
        self, node_ids: set[str], *, exclude: str | None = None
    ) -> list[dict[str, Any]]:
        """Include the compound ancestry needed to render a set of records."""
        node_ids = node_ids - {exclude}
        pending = list(node_ids)
        while pending:
            parent = self._nodes[pending.pop()]["data"].get("parent")
            if parent is not None and parent != exclude and parent not in node_ids:
                node_ids.add(parent)
                pending.append(parent)
        return [deepcopy(self._nodes[key]) for key in sorted(node_ids)]

    def expand(self, request: ExpansionRequest) -> ExpansionResponse:
        """Return an immutable source page, with separate exact node and edge totals."""
        positive_limit(request.limit, "Expansion limit")
        if request.node_id not in self._nodes:
            raise ValueError(f"Unknown source node: {request.node_id}")
        neighbors = self._neighbors(request.node_id, request.query)
        keys = sorted(neighbors)
        cursor = request.cursor if request.cursor is not None else 0
        if isinstance(cursor, bool) or not isinstance(cursor, int) or cursor < 0:
            raise ValueError("The in-memory cursor must be a nonnegative integer.")
        selected = keys[cursor : cursor + request.limit]
        edges = [edge for node_id in selected for edge in neighbors[node_id]]
        return ExpansionResponse(
            request.request_id,
            {
                "nodes": self._context_nodes(set(selected), exclude=request.node_id),
                "edges": deepcopy(edges),
            },
            has_more=cursor + len(selected) < len(keys),
            cursor=cursor + len(selected),
            total_nodes=len(set(keys) - {request.node_id}),
            total_edges=sum(len(value) for value in neighbors.values()),
        )

    def preview(self, request: ExpansionRequest) -> ExpansionResponse:
        """Preview the next page using the local index, without remote I/O."""
        return self.expand(request)

    def search(
        self, query: str, *, roots: list[str], limit: int = 50
    ) -> dict[str, Any]:
        """Search source node properties and return real connecting paths from roots.

        Disconnected matches are reported separately and are not silently added
        as new exploration anchors. Applications may explicitly protect/load them.
        """
        positive_limit(limit, "Search limit")
        all_matches = [
            key
            for key, node in self._nodes.items()
            if query.casefold() in str(node["data"]).casefold()
        ]
        matches = all_matches[:limit]
        parents: dict[str, tuple[str, dict[str, Any]] | None] = {
            key: None for key in roots if key in self._nodes
        }
        pending = deque(parents)
        while pending:
            node_id = pending.popleft()
            for edge in self._adjacency[node_id]:
                source, target = (str(edge["data"][x]) for x in ("source", "target"))
                other = target if source == node_id else source
                if other not in parents:
                    parents[other] = (node_id, edge)
                    pending.append(other)
        paths: dict[str, list[str]] = {}
        nodes: set[str] = set()
        edges: dict[str, dict[str, Any]] = {}
        for match in matches:
            if match not in parents:
                continue
            path = [match]
            while parents[path[-1]] is not None:
                entry = parents[path[-1]]
                assert entry is not None
                parent, edge = entry
                path.append(parent)
                edges[str(edge["data"]["id"])] = edge
            paths[match] = list(reversed(path))
            nodes.update(path)
        return {
            "node_ids": matches,
            "node_count": len(self._elements["nodes"]),
            "edge_count": len(self._elements["edges"]),
            "total_matches": len(all_matches),
            "complete": len(all_matches) <= limit,
            "paths": paths,
            "unreachable_node_ids": [key for key in matches if key not in paths],
            "elements": {
                "nodes": self._context_nodes(nodes),
                "edges": deepcopy(list(edges.values())),
            },
        }
