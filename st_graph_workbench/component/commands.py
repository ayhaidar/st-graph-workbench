import copy
import math
from typing import Any, Dict, Iterable, List, Literal, NoReturn, Optional, Set, cast

from st_graph_workbench.component._ids import normalize_id, normalize_id_list
from st_graph_workbench.component._typing import literal_choices
from st_graph_workbench.component.elements import (
    _as_element_list,
    _copy_elements,
    delete_elements,
    get_element,
    update_element_data,
    upsert_elements,
)
from st_graph_workbench.component.layouts import validate_layout
from st_graph_workbench.component.types import (
    Element,
    ElementId,
    ElementIdInput,
    ElementInput,
    Elements,
    GraphCommand,
)
from st_graph_workbench.component.validation import validate_elements


EdgeEndpoints = Dict[str, tuple[str, str]]
GraphCommandOperation = Literal[
    "add_elements",
    "upsert_elements",
    "update_data",
    "delete_elements",
    "clear",
    "set_elements",
    "fit",
    "center",
    "pan",
    "zoom",
    "set_viewport",
    "set_zoom_bounds",
    "run_layout",
]
ViewportCommandOperation = Literal[
    "fit",
    "center",
    "pan",
    "zoom",
    "set_viewport",
    "set_zoom_bounds",
    "run_layout",
]
_GRAPH_COMMAND_OPERATIONS: Set[str] = literal_choices(GraphCommandOperation)


class GraphCommandValidationError(ValueError):
    """Raised when incremental graph commands cannot be applied safely."""


def _fail(message: str) -> NoReturn:
    raise GraphCommandValidationError(
        f"Invalid st-graph-workbench graph command: {message}"
    )


def _as_id_list(values: ElementIdInput) -> List[str]:
    try:
        return normalize_id_list(values, option_name="node_ids/edge_ids")
    except TypeError as exc:
        _fail(str(exc))


def _normalize_command_id(command_id: Any) -> str:
    try:
        return normalize_id(command_id, option_name="command_id")
    except TypeError as error:
        _fail(str(error))


def _normalize_operation(operation: Any) -> str:
    if operation not in _GRAPH_COMMAND_OPERATIONS:
        _fail(
            f"unknown operation `{operation}`. "
            f"Expected one of {sorted(_GRAPH_COMMAND_OPERATIONS)}."
        )
    return str(operation)


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _is_pan_dict(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and _is_number(value.get("x"))
        and _is_number(value.get("y"))
    )


def _validate_nonnegative_number(
    command: GraphCommand,
    field: str,
    *,
    operation: str,
) -> None:
    value = command.get(field)
    if value is not None and (not _is_number(value) or value < 0):
        _fail(
            f"`{operation}` command `{field}` must be a finite numeric value "
            "zero or greater."
        )


def _validate_optional_duration(command: GraphCommand, *, operation: str) -> None:
    _validate_nonnegative_number(command, "duration", operation=operation)


def _validate_optional_rendered_position(command: GraphCommand) -> None:
    if "renderedPosition" not in command:
        return
    rendered_position = command.get("renderedPosition")
    if not _is_pan_dict(rendered_position):
        _fail("`zoom` command `renderedPosition` must include numeric `x` and `y`.")


def _command_base(
    command_id: ElementId, operation: GraphCommandOperation
) -> GraphCommand:
    return {
        "command_id": _normalize_command_id(command_id),
        "operation": operation,
    }


def add_elements_command(
    command_id: ElementId,
    *,
    nodes: ElementInput = None,
    edges: ElementInput = None,
) -> GraphCommand:
    """Build a command that adds only missing nodes and edges in the browser."""
    command = _command_base(command_id, "add_elements")
    node_list = _as_element_list(nodes)
    edge_list = _as_element_list(edges)
    if node_list:
        command["nodes"] = node_list
    if edge_list:
        command["edges"] = edge_list
    validate_graph_commands([command])
    return command


def upsert_elements_command(
    command_id: ElementId,
    *,
    nodes: ElementInput = None,
    edges: ElementInput = None,
    replace: bool = True,
) -> GraphCommand:
    """Build a command that adds or updates nodes and edges by `data.id`."""
    command = _command_base(command_id, "upsert_elements")
    node_list = _as_element_list(nodes)
    edge_list = _as_element_list(edges)
    if node_list:
        command["nodes"] = node_list
    if edge_list:
        command["edges"] = edge_list
    command["replace"] = replace
    validate_graph_commands([command])
    return command


def update_data_command(
    command_id: ElementId,
    element_id: ElementId,
    data: Dict[str, Any],
    *,
    merge: bool = True,
) -> GraphCommand:
    """Build a command that updates one existing node or edge data dict."""
    command = _command_base(command_id, "update_data")
    command["element_id"] = str(element_id)
    command["data"] = copy.deepcopy(data)
    command["merge"] = merge
    validate_graph_commands([command])
    return command


def delete_elements_command(
    command_id: ElementId,
    *,
    node_ids: ElementIdInput = None,
    edge_ids: ElementIdInput = None,
    remove_incident_edges: bool = True,
) -> GraphCommand:
    """Build a command that deletes nodes, edges, and optional incident edges."""
    command = _command_base(command_id, "delete_elements")
    command["node_ids"] = _as_id_list(node_ids)
    command["edge_ids"] = _as_id_list(edge_ids)
    command["remove_incident_edges"] = remove_incident_edges
    validate_graph_commands([command])
    return command


def set_elements_command(command_id: ElementId, elements: Elements) -> GraphCommand:
    """Build a command that replaces the browser graph with full elements."""
    graph = _copy_elements(elements)
    command = _command_base(command_id, "set_elements")
    command["elements"] = graph
    validate_graph_commands([command])
    return command


def clear_graph_command(command_id: ElementId) -> GraphCommand:
    """Build a command that clears every node and edge from the browser graph."""
    command = _command_base(command_id, "clear")
    validate_graph_commands([command])
    return command


def viewport_command(
    command_id: ElementId,
    operation: ViewportCommandOperation,
    **options: Any,
) -> GraphCommand:
    """Build a non-mutating viewport/layout command."""
    command = _command_base(command_id, operation)
    command.update(copy.deepcopy(options))
    validate_graph_commands([command])
    return command


def _command_nodes(command: GraphCommand) -> List[Element]:
    return _as_element_list(cast(ElementInput, command.get("nodes")))


def _command_edges(command: GraphCommand) -> List[Element]:
    return _as_element_list(cast(ElementInput, command.get("edges")))


def _command_elements(command: GraphCommand) -> Elements:
    elements = command.get("elements")
    if not isinstance(elements, dict):
        _fail("`set_elements` commands must include an `elements` dict.")
    return _copy_elements(cast(Elements, elements))


def _known_node_ids(elements: Optional[Elements]) -> Set[str]:
    if elements is None:
        return set()
    return {
        str(node["data"]["id"])
        for node in elements.get("nodes", [])
        if isinstance(node, dict) and isinstance(node.get("data"), dict)
    }


def _known_edge_endpoints(elements: Optional[Elements]) -> EdgeEndpoints:
    if elements is None:
        return {}
    endpoints: EdgeEndpoints = {}
    for edge in elements.get("edges", []):
        if not isinstance(edge, dict) or not isinstance(edge.get("data"), dict):
            continue
        data = edge["data"]
        if (
            data.get("id") is None
            or data.get("source") is None
            or data.get("target") is None
        ):
            continue
        endpoints[str(data["id"])] = (str(data["source"]), str(data["target"]))
    return endpoints


def _command_node_ids(command: GraphCommand) -> Set[str]:
    return {str(node["data"]["id"]) for node in _command_nodes(command)}


def _command_edge_endpoints(command: GraphCommand) -> EdgeEndpoints:
    return {
        str(edge["data"]["id"]): (
            str(edge["data"]["source"]),
            str(edge["data"]["target"]),
        )
        for edge in _command_edges(command)
    }


def _validate_command_edge_refs(
    command: GraphCommand,
    *,
    known_node_ids: Optional[Set[str]],
) -> None:
    if known_node_ids is None:
        return

    known_ids = set(known_node_ids)
    known_ids.update(_command_node_ids(command))
    for edge in _command_edges(command):
        data = edge["data"]
        edge_id = str(data["id"])
        source = str(data["source"])
        target = str(data["target"])
        if source not in known_ids:
            _fail(f"edge `{edge_id}` source `{source}` does not match any node id.")
        if target not in known_ids:
            _fail(f"edge `{edge_id}` target `{target}` does not match any node id.")


def _validate_update_data_edge_refs(
    command: GraphCommand,
    *,
    known_node_ids: Optional[Set[str]],
    known_edge_endpoints: Optional[EdgeEndpoints],
) -> None:
    if known_node_ids is None or known_edge_endpoints is None:
        return

    element_id = str(command.get("element_id"))
    if element_id not in known_edge_endpoints:
        return

    data = cast(Dict[str, Any], command["data"])
    current_source, current_target = known_edge_endpoints[element_id]
    merge = bool(command.get("merge", True))

    if not merge and ("source" not in data or "target" not in data):
        _fail(
            f"`update_data` command for edge `{element_id}` must include "
            "`source` and `target` when `merge` is false."
        )

    source = str(data.get("source", current_source if merge else ""))
    target = str(data.get("target", current_target if merge else ""))

    if source not in known_node_ids:
        _fail(f"edge `{element_id}` source `{source}` does not match any node id.")
    if target not in known_node_ids:
        _fail(f"edge `{element_id}` target `{target}` does not match any node id.")


def _validate_update_data_identity(command: GraphCommand) -> None:
    element_id = str(command.get("element_id"))
    data = cast(Dict[str, Any], command["data"])
    merge = bool(command.get("merge", True))
    incoming_id = data.get("id")

    if incoming_id is not None and str(incoming_id) != element_id:
        _fail(
            f"`update_data` command for element `{element_id}` cannot change "
            f"`data.id` to `{incoming_id}`. Use delete/add or upsert instead."
        )

    if not merge and incoming_id is None:
        _fail(
            f"`update_data` command for element `{element_id}` must include "
            "a matching `id` when `merge` is false."
        )


def _validate_update_data_target_exists(
    command: GraphCommand,
    *,
    known_node_ids: Optional[Set[str]],
    known_edge_endpoints: Optional[EdgeEndpoints],
) -> None:
    if known_node_ids is None or known_edge_endpoints is None:
        return

    element_id = str(command.get("element_id"))
    if element_id not in known_node_ids and element_id not in known_edge_endpoints:
        _fail(f"`update_data` command references missing element `{element_id}`.")


def _validate_delete_elements_keeps_graph_valid(
    command: GraphCommand,
    *,
    known_edge_endpoints: Optional[EdgeEndpoints],
) -> None:
    if known_edge_endpoints is None or bool(command.get("remove_incident_edges", True)):
        return

    node_ids = set(_as_id_list(cast(ElementIdInput, command.get("node_ids"))))
    edge_ids = set(_as_id_list(cast(ElementIdInput, command.get("edge_ids"))))
    if not node_ids:
        return

    dangling_edge_ids = sorted(
        edge_id
        for edge_id, (source, target) in known_edge_endpoints.items()
        if edge_id not in edge_ids and (source in node_ids or target in node_ids)
    )
    if dangling_edge_ids:
        _fail(
            "`delete_elements` cannot remove node(s) "
            f"{sorted(node_ids)} with `remove_incident_edges=False` while "
            f"leaving incident edge(s) {dangling_edge_ids}. Include those "
            "edge IDs or allow incident edge removal."
        )


def _update_known_node_ids_for_command(
    known_node_ids: Optional[Set[str]],
    command: GraphCommand,
    operation: str,
) -> Optional[Set[str]]:
    if known_node_ids is None:
        return None

    next_ids = set(known_node_ids)
    if operation in {"add_elements", "upsert_elements"}:
        next_ids.update(_command_node_ids(command))
        return next_ids

    if operation == "delete_elements":
        next_ids.difference_update(
            _as_id_list(cast(ElementIdInput, command.get("node_ids")))
        )
        return next_ids

    if operation == "clear":
        return set()

    if operation == "set_elements":
        return _known_node_ids(_command_elements(command))

    return next_ids


def _update_known_edge_endpoints_for_command(
    known_edge_endpoints: Optional[EdgeEndpoints],
    command: GraphCommand,
    operation: str,
) -> Optional[EdgeEndpoints]:
    if known_edge_endpoints is None:
        return None

    next_endpoints = dict(known_edge_endpoints)
    if operation in {"add_elements", "upsert_elements"}:
        next_endpoints.update(_command_edge_endpoints(command))
        return next_endpoints

    if operation == "update_data":
        element_id = str(command.get("element_id"))
        if element_id not in next_endpoints:
            return next_endpoints

        data = cast(Dict[str, Any], command["data"])
        merge = bool(command.get("merge", True))
        current_source, current_target = next_endpoints[element_id]
        source = str(data.get("source", current_source if merge else ""))
        target = str(data.get("target", current_target if merge else ""))
        next_endpoints[element_id] = (source, target)
        return next_endpoints

    if operation == "delete_elements":
        edge_ids = set(_as_id_list(cast(ElementIdInput, command.get("edge_ids"))))
        node_ids = set(_as_id_list(cast(ElementIdInput, command.get("node_ids"))))
        for edge_id in edge_ids:
            next_endpoints.pop(edge_id, None)
        if bool(command.get("remove_incident_edges", True)) and node_ids:
            next_endpoints = {
                edge_id: endpoints
                for edge_id, endpoints in next_endpoints.items()
                if endpoints[0] not in node_ids and endpoints[1] not in node_ids
            }
        return next_endpoints

    if operation == "clear":
        return {}

    if operation == "set_elements":
        return _known_edge_endpoints(_command_elements(command))

    return next_endpoints


def _validate_command(
    command: Any,
    *,
    known_node_ids: Optional[Set[str]],
    known_edge_endpoints: Optional[EdgeEndpoints],
) -> str:
    if not isinstance(command, dict):
        _fail("each command must be a dict.")

    normalized = cast(GraphCommand, command)
    _normalize_command_id(normalized.get("command_id"))
    operation = _normalize_operation(normalized.get("operation"))

    if operation in {"add_elements", "upsert_elements"}:
        nodes = _command_nodes(normalized)
        edges = _command_edges(normalized)
        validate_elements({"nodes": nodes, "edges": edges}, strict=False)
        _validate_command_edge_refs(normalized, known_node_ids=known_node_ids)
        return operation

    if operation == "update_data":
        element_id = normalized.get("element_id")
        if element_id is None or element_id == "":
            _fail("`update_data` commands must include `element_id`.")
        if not isinstance(normalized.get("data"), dict):
            _fail("`update_data` commands must include a `data` dict.")
        _validate_update_data_identity(normalized)
        _validate_update_data_target_exists(
            normalized,
            known_node_ids=known_node_ids,
            known_edge_endpoints=known_edge_endpoints,
        )
        _validate_update_data_edge_refs(
            normalized,
            known_node_ids=known_node_ids,
            known_edge_endpoints=known_edge_endpoints,
        )
        return operation

    if operation == "delete_elements":
        _as_id_list(cast(ElementIdInput, normalized.get("node_ids")))
        _as_id_list(cast(ElementIdInput, normalized.get("edge_ids")))
        _validate_delete_elements_keeps_graph_valid(
            normalized,
            known_edge_endpoints=known_edge_endpoints,
        )
        return operation

    if operation == "set_elements":
        _command_elements(normalized)
        return operation

    if operation == "zoom":
        _validate_optional_duration(normalized, operation=operation)
        level = normalized.get("level", normalized.get("zoom"))
        if not _is_number(level):
            _fail("`zoom` commands must include a finite numeric `level` or `zoom`.")
        _validate_optional_rendered_position(normalized)
        return operation

    if operation == "pan":
        _validate_optional_duration(normalized, operation=operation)
        pan = normalized.get("pan")
        if not isinstance(pan, dict):
            _fail("`pan` commands must include a `pan` dict.")
        if not _is_pan_dict(pan):
            _fail("`pan` command `pan` must include numeric `x` and `y`.")
        return operation

    if operation == "set_viewport":
        _validate_optional_duration(normalized, operation=operation)
        zoom = normalized.get("zoom")
        pan = normalized.get("pan")
        if zoom is not None and (not _is_number(zoom)):
            _fail("`set_viewport` command `zoom` must be finite numeric when provided.")
        if pan is not None:
            if not isinstance(pan, dict):
                _fail("`set_viewport` command `pan` must be a dict when provided.")
            if not _is_pan_dict(pan):
                _fail("`set_viewport` command `pan` must include numeric `x` and `y`.")
        return operation

    if operation == "set_zoom_bounds":
        for field in ("min_zoom", "max_zoom"):
            value = normalized.get(field)
            if value is not None and not _is_number(value):
                _fail(f"`set_zoom_bounds` command `{field}` must be finite numeric.")
        min_zoom = normalized.get("min_zoom")
        max_zoom = normalized.get("max_zoom")
        if (
            min_zoom is not None
            and max_zoom is not None
            and cast(float, min_zoom) > cast(float, max_zoom)
        ):
            _fail("`set_zoom_bounds` command `min_zoom` cannot exceed `max_zoom`.")
        return operation

    if operation == "run_layout":
        _validate_optional_duration(normalized, operation=operation)
        layout = normalized.get("layout")
        try:
            validate_layout(
                layout,
                description="`run_layout` command `layout`",
                allow_none=True,
            )
        except ValueError as error:
            _fail(str(error))
        return operation

    if operation in {"fit", "center"}:
        _validate_optional_duration(normalized, operation=operation)
        if operation == "fit":
            _validate_nonnegative_number(normalized, "padding", operation=operation)

    return operation


def validate_graph_commands(
    commands: Optional[Iterable[GraphCommand]],
    *,
    elements: Optional[Elements] = None,
) -> None:
    """Validate incremental graph commands before they are sent to the browser."""
    if commands is None:
        return
    if isinstance(commands, (str, bytes, dict)):
        _fail("`graph_commands` must be a list or iterable of command dicts.")

    seen_ids: Set[str] = set()
    known_node_ids = _known_node_ids(elements) if elements is not None else None
    known_edge_endpoints = (
        _known_edge_endpoints(elements) if elements is not None else None
    )
    for command in commands:
        operation = _validate_command(
            command,
            known_node_ids=known_node_ids,
            known_edge_endpoints=known_edge_endpoints,
        )
        command_id = _normalize_command_id(command.get("command_id"))
        if command_id in seen_ids:
            _fail(f"duplicate command_id `{command_id}`.")
        seen_ids.add(command_id)
        known_node_ids = _update_known_node_ids_for_command(
            known_node_ids,
            command,
            operation,
        )
        known_edge_endpoints = _update_known_edge_endpoints_for_command(
            known_edge_endpoints,
            command,
            operation,
        )


def apply_graph_command(elements: Elements, command: GraphCommand) -> Elements:
    """
    Return a new graph after applying one command to Python-owned elements.

    This helper is useful in Streamlit apps that keep `st.session_state`
    authoritative while also sending the same command to the browser for an
    incremental Cytoscape update.
    """
    validate_graph_commands([command], elements=elements)
    operation = _normalize_operation(command.get("operation"))

    if operation == "add_elements":
        for element in [*_command_nodes(command), *_command_edges(command)]:
            element_id = element["data"]["id"]
            if get_element(elements, element_id) is not None:
                raise KeyError(f"Element `{element_id}` already exists.")
        return upsert_elements(
            elements,
            nodes=_command_nodes(command),
            edges=_command_edges(command),
            replace=True,
        )

    if operation == "upsert_elements":
        return upsert_elements(
            elements,
            nodes=_command_nodes(command),
            edges=_command_edges(command),
            replace=bool(command.get("replace", True)),
        )

    if operation == "update_data":
        return update_element_data(
            elements,
            command["element_id"],
            cast(Dict[str, Any], command["data"]),
            merge=bool(command.get("merge", True)),
        )

    if operation == "delete_elements":
        return delete_elements(
            elements,
            node_ids=cast(ElementIdInput, command.get("node_ids")),
            edge_ids=cast(ElementIdInput, command.get("edge_ids")),
            remove_incident_edges=bool(command.get("remove_incident_edges", True)),
        )

    if operation == "clear":
        return {"nodes": [], "edges": []}

    if operation == "set_elements":
        return _command_elements(command)

    return _copy_elements(elements)


def apply_graph_commands(
    elements: Elements,
    commands: Optional[Iterable[GraphCommand]],
) -> Elements:
    """Return a new graph after applying commands in order."""
    graph = _copy_elements(elements)
    if commands is None:
        return graph
    for command in commands:
        graph = apply_graph_command(graph, command)
    return graph
