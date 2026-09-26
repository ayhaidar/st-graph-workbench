import copy
from collections.abc import Iterable as IterableABC
from typing import Any, cast

from st_graph_workbench.component._ids import normalize_id_set
from st_graph_workbench.component.types import (
    Element,
    ElementId,
    ElementIdInput,
    ElementInput,
    Elements,
)
from st_graph_workbench.component.validation import validate_elements


def _copy_elements(elements: Any) -> Elements:
    if not isinstance(elements, dict):
        validate_elements(elements)
        raise TypeError("`elements` must be a dict.")
    result = cast(Elements, copy.deepcopy(elements))
    result.setdefault("nodes", [])
    result.setdefault("edges", [])
    validate_elements(result)
    return result


def _as_element_list(elements: Any) -> list[Element]:
    if elements is None:
        return []
    if isinstance(elements, dict):
        return [copy.deepcopy(elements)]
    if isinstance(elements, (str, bytes)) or not isinstance(elements, IterableABC):
        raise TypeError("Element inputs must be dicts or iterables of dicts.")

    result: list[Element] = []
    for element in elements:
        if not isinstance(element, dict):
            raise TypeError("Element inputs must be dicts or iterables of dicts.")
        result.append(copy.deepcopy(element))
    return result


def _element_id(element: Element) -> str:
    return str(element["data"]["id"])


def _normalized_ids(values: ElementIdInput) -> set[str]:
    return normalize_id_set(values, option_name="node_ids/edge_ids")


def _validate_update_identity(
    element_id: str, data: dict[str, Any], *, merge: bool
) -> None:
    incoming_id = data.get("id")

    if incoming_id is not None and str(incoming_id) != element_id:
        raise ValueError(
            f"Element `{element_id}` data.id cannot be changed to `{incoming_id}`. "
            "Use delete/add or upsert_elements(...) instead."
        )

    if not merge and incoming_id is None:
        raise ValueError(
            f"Element `{element_id}` replacement data must include a matching `id` "
            "when `merge` is false."
        )


def _upsert_group(
    current: list[Element],
    incoming: list[Element],
    *,
    group: str,
    replace: bool,
) -> list[Element]:
    validate_elements({group: incoming}, strict=False)
    by_id = {_element_id(element): copy.deepcopy(element) for element in current}
    order = [_element_id(element) for element in current]

    for element in incoming:
        element_id = _element_id(element)
        if element_id not in by_id:
            order.append(element_id)
            by_id[element_id] = element
            continue

        if replace:
            by_id[element_id] = element
            continue

        existing = by_id[element_id]
        merged = copy.deepcopy(existing)
        merged.update({key: value for key, value in element.items() if key != "data"})
        merged["data"] = {
            **copy.deepcopy(existing.get("data", {})),
            **copy.deepcopy(element.get("data", {})),
        }
        by_id[element_id] = merged

    return [by_id[element_id] for element_id in order]


def get_element(elements: Elements, element_id: ElementId) -> Element | None:
    """Return a copy of a node or edge by ID, or None when it is not present."""
    normalized_id = str(element_id)
    graph = _copy_elements(elements)
    for element in [*graph["nodes"], *graph["edges"]]:
        if _element_id(element) == normalized_id:
            return cast(Element, copy.deepcopy(element))
    return None


def upsert_elements(
    elements: Elements,
    *,
    nodes: ElementInput = None,
    edges: ElementInput = None,
    replace: bool = True,
) -> Elements:
    """Return a graph with nodes and edges added or updated by data.id."""
    graph = _copy_elements(elements)
    graph["nodes"] = _upsert_group(
        graph["nodes"], _as_element_list(nodes), group="nodes", replace=replace
    )
    graph["edges"] = _upsert_group(
        graph["edges"], _as_element_list(edges), group="edges", replace=replace
    )
    validate_elements(graph)
    return graph


def update_element_data(
    elements: Elements,
    element_id: ElementId,
    data: dict[str, Any],
    *,
    merge: bool = True,
) -> Elements:
    """Return a graph with one node or edge data dict updated."""
    if not isinstance(data, dict):
        raise TypeError("`data` must be a dict.")

    normalized_id = str(element_id)
    _validate_update_identity(normalized_id, data, merge=merge)
    graph = _copy_elements(elements)

    for group in ("nodes", "edges"):
        for element in graph[group]:
            if _element_id(element) != normalized_id:
                continue
            element["data"] = (
                {**copy.deepcopy(element.get("data", {})), **copy.deepcopy(data)}
                if merge
                else copy.deepcopy(data)
            )
            validate_elements(graph)
            return graph

    raise KeyError(f"Element `{normalized_id}` was not found.")


def delete_elements(
    elements: Elements,
    *,
    node_ids: ElementIdInput = None,
    edge_ids: ElementIdInput = None,
    remove_incident_edges: bool = True,
) -> Elements:
    """Return a graph with selected nodes, edges, and optional incident edges removed."""
    nodes_to_remove = _normalized_ids(node_ids)
    edges_to_remove = _normalized_ids(edge_ids)
    graph = _copy_elements(elements)

    graph["nodes"] = [
        node for node in graph["nodes"] if _element_id(node) not in nodes_to_remove
    ]

    def keep_edge(edge: Element) -> bool:
        data = edge["data"]
        if _element_id(edge) in edges_to_remove:
            return False
        if remove_incident_edges and (
            str(data.get("source")) in nodes_to_remove
            or str(data.get("target")) in nodes_to_remove
        ):
            return False
        return True

    graph["edges"] = [edge for edge in graph["edges"] if keep_edge(edge)]
    validate_elements(graph)
    return graph
