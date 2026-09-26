import math
from collections.abc import Iterable
from typing import Any, NoReturn, cast

from st_graph_workbench.component._ids import normalize_id


class ElementValidationError(ValueError):
    """Raised when graph elements cannot be safely rendered by Cytoscape."""


def _fail(message: str) -> NoReturn:
    raise ElementValidationError(f"Invalid st-graph-workbench elements: {message}")


def _as_list(value: Any, name: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        _fail(f"`elements['{name}']` must be a list.")
    return value


def _get_data(element: Any, group: str, index: int) -> dict[str, Any]:
    if not isinstance(element, dict):
        _fail(f"{group}[{index}] must be a dict with a `data` dict.")
    data = element.get("data")
    if not isinstance(data, dict):
        _fail(f"{group}[{index}] must include a `data` dict.")
    return cast(dict[str, Any], data)


def _normalize_id(value: Any, description: str) -> str:
    try:
        return normalize_id(value, option_name=description)
    except TypeError as error:
        _fail(str(error))


def _validate_count(value: Any, field: str, node_id: str) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        _fail(f"node `{node_id}` expansion `{field}` must be a finite number.")
    if value < 0:
        _fail(f"node `{node_id}` expansion `{field}` must be zero or greater.")


def _validate_expansion(data: dict[str, Any], node_id: str) -> None:
    expansion = data.get("expansion")
    if expansion is None:
        return
    if not isinstance(expansion, dict):
        _fail(f"node `{node_id}` expansion metadata must be a dict.")

    state = expansion.get("state")
    if state is not None and state not in {"collapsed", "expanded"}:
        _fail(f"node `{node_id}` expansion `state` must be `collapsed` or `expanded`.")

    for field in ("next_count", "total_count", "depth", "collapse_count"):
        if field in expansion:
            _validate_count(expansion[field], field, node_id)


def _validate_parent_cycles(parent_by_node: dict[str, str]) -> None:
    for node_id in parent_by_node:
        seen: set[str] = set()
        current = node_id
        while current in parent_by_node:
            if current in seen:
                _fail(f"compound parent cycle detected at node `{node_id}`.")
            seen.add(current)
            current = parent_by_node[current]


def _validate_unique_ids(ids: Iterable[str]) -> None:
    seen: set[str] = set()
    for element_id in ids:
        if element_id in seen:
            _fail(f"duplicate element id `{element_id}`.")
        seen.add(element_id)


def validate_elements(elements: Any, *, strict: bool = True) -> None:
    """
    Validate Streamlit graph elements before they are sent to Cytoscape.

    Cytoscape treats IDs as strings and requires every edge source/target to
    reference an existing node. This helper catches common data-shape mistakes
    on the Python side so Streamlit apps get actionable errors instead of a
    browser-side rendering failure.
    """
    if not isinstance(elements, dict):
        _fail("`elements` must be a dict with optional `nodes` and `edges` lists.")

    nodes = _as_list(elements.get("nodes", []), "nodes")
    edges = _as_list(elements.get("edges", []), "edges")

    node_ids: set[str] = set()
    all_ids: list[str] = []
    parent_by_node: dict[str, str] = {}

    for index, node in enumerate(nodes):
        data = _get_data(node, "nodes", index)
        node_id = _normalize_id(data.get("id"), f"nodes[{index}].data.id")
        node_ids.add(node_id)
        all_ids.append(node_id)
        _validate_expansion(data, node_id)

        parent = data.get("parent")
        if parent is not None and parent != "":
            parent_id = _normalize_id(parent, f"node `{node_id}` data.parent")
            if parent_id == node_id:
                _fail(f"node `{node_id}` cannot be its own compound parent.")
            parent_by_node[node_id] = parent_id

    edge_refs: list[tuple[str, str, str]] = []
    for index, edge in enumerate(edges):
        data = _get_data(edge, "edges", index)
        edge_id = _normalize_id(data.get("id"), f"edges[{index}].data.id")
        all_ids.append(edge_id)

        source = _normalize_id(data.get("source"), f"edge `{edge_id}` source")
        target = _normalize_id(data.get("target"), f"edge `{edge_id}` target")
        edge_refs.append((edge_id, source, target))

    _validate_unique_ids(all_ids)

    if not strict:
        return

    for edge_id, source, target in edge_refs:
        if source not in node_ids:
            _fail(f"edge `{edge_id}` source `{source}` does not match any node id.")
        if target not in node_ids:
            _fail(f"edge `{edge_id}` target `{target}` does not match any node id.")

    for node_id, parent_id in parent_by_node.items():
        if parent_id not in node_ids:
            _fail(
                f"node `{node_id}` compound parent `{parent_id}` "
                "does not match any node id."
            )

    _validate_parent_cycles(parent_by_node)
