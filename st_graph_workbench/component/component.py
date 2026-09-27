import math
import warnings
from collections.abc import Iterable as IterableABC, Mapping
from pathlib import Path
from typing import Any, Callable, List, Literal, Optional, Set, Union, cast

import streamlit as st
from streamlit.errors import StreamlitAPIException

from st_graph_workbench.component._typing import literal_choices
from st_graph_workbench.component._warnings import GraphWorkbenchDeprecationWarning
from st_graph_workbench.component.layouts import resolve_layout
from st_graph_workbench.component.styles import NodeStyle, EdgeStyle, StyleRule
from st_graph_workbench.component.events import Event
from st_graph_workbench.component.validation import validate_elements
from st_graph_workbench.component.commands import validate_graph_commands
from st_graph_workbench.component.expansion import ExpansionConfig
from st_graph_workbench.component.types import (
    ConnectedDragConfig,
    Elements,
    GraphCommand,
    GraphEvent,
    Layout,
    ProgressiveLoadConfig,
    ToolbarConfig,
)


_COMPONENT_NAME = "st_graph_workbench.graph_workbench"
_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
_FRONTEND_BUILD_DIR = _PACKAGE_ROOT / "frontend" / "build"
_FRONTEND_SRC_DIR = _PACKAGE_ROOT / "frontend" / "src"


def _read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8") as f:
        return f.read()


def _read_component_html() -> str:
    build_html = _FRONTEND_BUILD_DIR / "component.html"
    if build_html.exists():
        return _read_text(build_html)
    return _read_text(_FRONTEND_SRC_DIR / "component.html")


def _read_component_css() -> str:
    build_css = _FRONTEND_BUILD_DIR / "style.css"
    if build_css.exists():
        return _read_text(build_css)
    return _read_text(_FRONTEND_SRC_DIR / "style.css")


def _read_component_js() -> str:
    js_files = list(_FRONTEND_BUILD_DIR.glob("index-*.js"))
    if len(js_files) != 1:
        raise StreamlitAPIException(
            "Expected exactly one built frontend bundle matching index-*.js. "
            "Run `npm run build` in st_graph_workbench/frontend."
        )
    return _read_text(js_files[0])


def _register_source_manifest() -> None:
    from streamlit.components.v2.get_bidi_component_manager import (
        get_bidi_component_manager,
    )
    from streamlit.components.v2.manifest_scanner import (
        ComponentConfig,
        ComponentManifest,
    )

    manager = get_bidi_component_manager()
    if manager.get_component_asset_root(_COMPONENT_NAME) is not None:
        return

    manifest = ComponentManifest(
        name="st_graph_workbench",
        version="0.1.0",
        components=[
            ComponentConfig(
                name="graph_workbench",
                asset_dir="frontend/build",
            )
        ],
    )
    manager.register_from_manifest(manifest, _PACKAGE_ROOT)


def _create_component_func() -> Any:
    html = _read_component_html()
    # Cytoscape's box-selection pointer handling misses node hits inside a
    # shadow root in current browser tests, so the component stays in the light
    # DOM and keeps its CSS scoped under the st-graph-workbench root.
    try:
        _register_source_manifest()
        return st.components.v2.component(
            _COMPONENT_NAME,
            html=html,
            css="style.css",
            js="index-*.js",
            isolate_styles=False,
        )
    except StreamlitAPIException:
        return st.components.v2.component(
            _COMPONENT_NAME,
            html=html,
            css=_read_component_css(),
            js=_read_component_js(),
            isolate_styles=False,
        )


_component_func = _create_component_func()

NodeAction = Literal[
    "remove",
    "expand",
    "show_neighbors",
    "show_incoming",
    "show_outgoing",
    "hide_unselected",
    "restore_hidden",
]
"""Node context/toolbox actions supported by ``graph_workbench``."""
CrudAction = Literal[
    "create_node",
    "create_edge",
    "read_selected",
    "update_selected",
    "delete_selected",
    "request_node_data",
]
"""CRUD intents that the browser can return for Python handling."""
EditAction = Literal[
    "add_node",
    "connect_selected",
    "delete_selected",
    "lock_selected",
    "unlock_selected",
    "make_ungrabbable",
    "make_grabbable",
    "snap_to_grid",
    "undo",
    "redo",
]
"""Immediate browser-local graph editing actions."""
ViewportAction = Literal[
    "toggle_zoom",
    "toggle_pan",
    "save_viewport",
    "restore_viewport",
    "reset_viewport",
]
"""Interactive viewport actions exposed by the graph toolbox."""
SelectionMode = Literal["single", "multiple", "box"]
"""Supported Cytoscape selection interaction modes."""
AnalysisAction = Literal[
    "shortest_path",
    "bfs",
    "dfs",
    "connected_components",
    "degree",
]
"""Browser-side graph algorithms exposed by the analysis toolbox."""
PerformanceProfile = Literal["default", "large", "dense"]
"""Rendering profiles that tune graph behavior for different scales."""
ElementsSync = Literal["always", "initial"]
"""Full reconciliation or command-driven element synchronization."""

_NODE_ACTIONS: Set[str] = literal_choices(NodeAction)
_CRUD_ACTIONS: Set[str] = literal_choices(CrudAction)
_EDIT_ACTIONS: Set[str] = literal_choices(EditAction)
_VIEWPORT_ACTIONS: Set[str] = literal_choices(ViewportAction)
_SELECTION_MODES: Set[str] = literal_choices(SelectionMode)
_ANALYSIS_ACTIONS: Set[str] = literal_choices(AnalysisAction)
_PERFORMANCE_PROFILES: Set[str] = literal_choices(PerformanceProfile)
_ELEMENTS_SYNC_MODES: Set[str] = literal_choices(ElementsSync)
_SYNC_REQUEST_ACTION = "_graph_workbench_sync_request"


def _noop() -> None:
    pass


def _component_field(component_result: Any, name: str) -> Any:
    if component_result is None:
        return None
    if isinstance(component_result, dict):
        return component_result.get(name)
    if hasattr(component_result, name):
        return getattr(component_result, name)
    try:
        return component_result[name]
    except (KeyError, TypeError):
        return None


def _extract_event(component_result: Any) -> Optional[GraphEvent]:
    event = _component_field(component_result, "event")
    return cast(GraphEvent, event) if isinstance(event, dict) else None


def _is_sync_request(event: Optional[GraphEvent]) -> bool:
    return event is not None and event.get("action") == _SYNC_REQUEST_ACTION


def _elements_sync_state_key(component_key: str) -> str:
    return f"{component_key}:elements-synced"


def _validate_option_values(
    node_actions: List[NodeAction],
    crud_actions: List[CrudAction],
    edit_actions: List[EditAction],
    viewport_actions: List[ViewportAction],
    selection_mode: SelectionMode,
    analysis_actions: List[AnalysisAction],
    performance_profile: PerformanceProfile,
    elements_sync: ElementsSync,
    component_key: Optional[str],
) -> None:
    unknown_node_actions = _unknown_option_values(
        "node_actions",
        node_actions,
        _NODE_ACTIONS,
    )
    if unknown_node_actions:
        raise ValueError(
            "Unknown node action(s) "
            f"{unknown_node_actions}. Expected one of {sorted(_NODE_ACTIONS)}."
        )

    unknown_crud_actions = _unknown_option_values(
        "crud_actions",
        crud_actions,
        _CRUD_ACTIONS,
    )
    if unknown_crud_actions:
        raise ValueError(
            "Unknown CRUD action(s) "
            f"{unknown_crud_actions}. Expected one of {sorted(_CRUD_ACTIONS)}."
        )

    unknown_edit_actions = _unknown_option_values(
        "edit_actions",
        edit_actions,
        _EDIT_ACTIONS,
    )
    if unknown_edit_actions:
        raise ValueError(
            "Unknown edit action(s) "
            f"{unknown_edit_actions}. Expected one of {sorted(_EDIT_ACTIONS)}."
        )

    unknown_viewport_actions = _unknown_option_values(
        "viewport_actions",
        viewport_actions,
        _VIEWPORT_ACTIONS,
    )
    if unknown_viewport_actions:
        raise ValueError(
            "Unknown viewport action(s) "
            f"{unknown_viewport_actions}. Expected one of "
            f"{sorted(_VIEWPORT_ACTIONS)}."
        )

    if selection_mode not in _SELECTION_MODES:
        raise ValueError(
            f"Unknown selection_mode `{selection_mode}`. "
            f"Expected one of {sorted(_SELECTION_MODES)}."
        )

    unknown_analysis_actions = _unknown_option_values(
        "analysis_actions",
        analysis_actions,
        _ANALYSIS_ACTIONS,
    )
    if unknown_analysis_actions:
        raise ValueError(
            "Unknown analysis action(s) "
            f"{unknown_analysis_actions}. Expected one of {sorted(_ANALYSIS_ACTIONS)}."
        )

    if performance_profile not in _PERFORMANCE_PROFILES:
        raise ValueError(
            f"Unknown performance_profile `{performance_profile}`. "
            f"Expected one of {sorted(_PERFORMANCE_PROFILES)}."
        )

    if elements_sync not in _ELEMENTS_SYNC_MODES:
        raise ValueError(
            f"Unknown elements_sync `{elements_sync}`. "
            f"Expected one of {sorted(_ELEMENTS_SYNC_MODES)}."
        )

    if elements_sync == "initial" and component_key is None:
        raise ValueError(
            "`elements_sync='initial'` requires a stable `key` so Streamlit can "
            "track when the initial element payload has already been sent."
        )


def _unknown_option_values(
    option_name: str,
    values: Any,
    allowed_values: Set[str],
) -> List[str]:
    normalized_values = _normalize_option_values(option_name, values)
    return sorted(set(normalized_values) - allowed_values)


def _normalize_option_values(option_name: str, values: Any) -> List[Any]:
    if values is None:
        return []
    if isinstance(values, (str, bytes)) or not isinstance(values, IterableABC):
        raise ValueError(
            f"`{option_name}` must be a list or iterable of option names, not "
            f"`{type(values).__name__}`."
        )
    return [str(value) for value in values]


def _normalize_height(height: Any) -> int:
    if isinstance(height, bool) or not isinstance(height, int) or height <= 0:
        raise ValueError("`height` must be a positive integer pixel height.")
    return height


def _normalize_optional_viewport_number(
    option_name: str, value: Any
) -> Optional[float]:
    if value is None:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"`{option_name}` must be finite numeric when provided.")
    return float(value)


def _normalize_viewport_options(
    min_zoom: Any,
    max_zoom: Any,
    wheel_sensitivity: Any,
) -> tuple[Optional[float], Optional[float], Optional[float]]:
    normalized_min_zoom = _normalize_optional_viewport_number("min_zoom", min_zoom)
    normalized_max_zoom = _normalize_optional_viewport_number("max_zoom", max_zoom)
    normalized_wheel_sensitivity = _normalize_optional_viewport_number(
        "wheel_sensitivity",
        wheel_sensitivity,
    )

    if (
        normalized_min_zoom is not None
        and normalized_max_zoom is not None
        and normalized_min_zoom > normalized_max_zoom
    ):
        raise ValueError("`min_zoom` cannot exceed `max_zoom`.")
    if normalized_wheel_sensitivity is not None and normalized_wheel_sensitivity <= 0:
        raise ValueError("`wheel_sensitivity` must be greater than zero.")

    return normalized_min_zoom, normalized_max_zoom, normalized_wheel_sensitivity


def _normalize_nonnegative_integer(option_name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"`{option_name}` must be a non-negative integer.")
    return value


def _normalize_progressive_loading(
    config: Optional[ProgressiveLoadConfig],
) -> Optional[ProgressiveLoadConfig]:
    if config is None:
        return None
    if not isinstance(config, Mapping):
        raise TypeError("`progressive_loading` must be a mapping when provided.")

    allowed_fields = {
        "page_size",
        "loaded_count",
        "total_count",
        "has_more",
        "cursor",
        "acknowledged_request_id",
    }
    unknown_fields = sorted(
        str(field) for field in config if field not in allowed_fields
    )
    if unknown_fields:
        raise ValueError(
            "Unknown `progressive_loading` field(s) "
            f"{unknown_fields}. Expected only {sorted(allowed_fields)}."
        )

    page_size = _normalize_nonnegative_integer(
        "progressive_loading.page_size", config.get("page_size", 100)
    )
    if page_size == 0:
        raise ValueError("`progressive_loading.page_size` must be greater than zero.")
    loaded_count = _normalize_nonnegative_integer(
        "progressive_loading.loaded_count", config.get("loaded_count", 0)
    )
    total_value = config.get("total_count")
    total_count = (
        None
        if total_value is None
        else _normalize_nonnegative_integer(
            "progressive_loading.total_count", total_value
        )
    )
    if total_count is not None and loaded_count > total_count:
        raise ValueError(
            "`progressive_loading.loaded_count` cannot exceed `total_count`."
        )

    has_more_value = config.get("has_more")
    if has_more_value is not None and not isinstance(has_more_value, bool):
        raise TypeError("`progressive_loading.has_more` must be a boolean.")
    has_more = (
        has_more_value
        if has_more_value is not None
        else total_count is None or loaded_count < total_count
    )

    cursor = config.get("cursor")
    if cursor is not None and (
        not isinstance(cursor, (str, int, float, bool))
        or (isinstance(cursor, float) and not math.isfinite(cursor))
    ):
        raise TypeError(
            "`progressive_loading.cursor` must be a finite JSON scalar or None."
        )

    acknowledged_request_id = config.get("acknowledged_request_id")
    if acknowledged_request_id is not None and (
        not isinstance(acknowledged_request_id, str)
        or not acknowledged_request_id.strip()
    ):
        raise ValueError(
            "`progressive_loading.acknowledged_request_id` must be a non-empty "
            "string or None."
        )

    return {
        "page_size": page_size,
        "loaded_count": loaded_count,
        "total_count": total_count,
        "has_more": has_more,
        "cursor": cursor,
        "acknowledged_request_id": acknowledged_request_id,
    }


def _normalize_connected_drag(
    config: Optional[ConnectedDragConfig],
) -> Optional[ConnectedDragConfig]:
    if config is None:
        return None
    if not isinstance(config, Mapping):
        raise TypeError("`connected_drag` must be a mapping when provided.")

    allowed_fields = {"enabled", "depth", "max_depth", "max_nodes"}
    unknown_fields = sorted(
        str(field) for field in config if field not in allowed_fields
    )
    if unknown_fields:
        raise ValueError(
            "Unknown `connected_drag` field(s) "
            f"{unknown_fields}. Expected only {sorted(allowed_fields)}."
        )

    enabled = config.get("enabled", False)
    if not isinstance(enabled, bool):
        raise TypeError("`connected_drag.enabled` must be a boolean.")

    def depth_value(field: str, default: int) -> int:
        value = config.get(field, default)
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value not in {1, 2, 3}
        ):
            raise ValueError(f"`connected_drag.{field}` must be 1, 2, or 3.")
        return value

    depth = depth_value("depth", 1)
    max_depth = depth_value("max_depth", 3)
    if depth > max_depth:
        raise ValueError("`connected_drag.depth` cannot exceed `max_depth`.")

    max_nodes = config.get("max_nodes", 100)
    if isinstance(max_nodes, bool) or not isinstance(max_nodes, int) or max_nodes <= 0:
        raise ValueError("`connected_drag.max_nodes` must be a positive integer.")

    return {
        "enabled": enabled,
        "depth": cast(Any, depth),
        "max_depth": cast(Any, max_depth),
        "max_nodes": max_nodes,
    }


def _normalize_toolbar(config: Optional[ToolbarConfig]) -> ToolbarConfig:
    if config is None:
        config = {}
    if not isinstance(config, Mapping):
        raise TypeError("`toolbar` must be a mapping when provided.")

    allowed_fields = {"mode", "position", "collapsible", "sticky"}
    unknown_fields = sorted(
        str(field) for field in config if field not in allowed_fields
    )
    if unknown_fields:
        raise ValueError(
            "Unknown `toolbar` field(s) "
            f"{unknown_fields}. Expected only {sorted(allowed_fields)}."
        )

    mode = config.get("mode", "adaptive")
    if mode not in {"adaptive", "expanded", "compact", "minimized"}:
        raise ValueError(
            "`toolbar.mode` must be 'adaptive', 'expanded', 'compact', or 'minimized'."
        )
    position = config.get("position", "top")
    if position != "top":
        raise ValueError("`toolbar.position` currently supports only 'top'.")

    collapsible = config.get("collapsible", True)
    sticky = config.get("sticky", True)
    if not isinstance(collapsible, bool):
        raise TypeError("`toolbar.collapsible` must be a boolean.")
    if not isinstance(sticky, bool):
        raise TypeError("`toolbar.sticky` must be a boolean.")

    return {
        "mode": cast(Any, mode),
        "position": cast(Any, position),
        "collapsible": collapsible,
        "sticky": sticky,
    }


def _component_instance_key(key: Optional[str]) -> Optional[str]:
    if key is None:
        return None
    encoded_key = key.encode("utf-8").hex()
    return f"st-graph-workbench-v2-{encoded_key}"


def graph_workbench(
    elements: Elements,
    layout: Layout = "cose",
    node_styles: Optional[List[Union[NodeStyle, StyleRule]]] = None,
    edge_styles: Optional[List[Union[EdgeStyle, StyleRule]]] = None,
    height: int = 500,
    key: Optional[str] = None,
    on_change: Optional[Callable[..., None]] = None,
    node_actions: Optional[List[NodeAction]] = None,
    crud_actions: Optional[List[CrudAction]] = None,
    edit_actions: Optional[List[EditAction]] = None,
    viewport_actions: Optional[List[ViewportAction]] = None,
    enable_node_actions: Optional[bool] = None,  # deprecated
    events: Optional[List[Event]] = None,
    validate: bool = True,
    selection_mode: SelectionMode = "single",
    return_selection: bool = False,
    search: bool = False,
    analysis_actions: Optional[List[AnalysisAction]] = None,
    return_positions: bool = False,
    performance_profile: PerformanceProfile = "default",
    min_zoom: Optional[float] = None,
    max_zoom: Optional[float] = None,
    wheel_sensitivity: Optional[float] = None,
    graph_commands: Optional[List[GraphCommand]] = None,
    elements_sync: ElementsSync = "always",
    progressive_loading: Optional[ProgressiveLoadConfig] = None,
    expansion: Optional[dict[str, Any]] = None,
    show_selection_details: bool = True,
    connected_drag: Optional[ConnectedDragConfig] = None,
    toolbar: Optional[ToolbarConfig] = None,
) -> Optional[GraphEvent]:
    """
    Renders an interactive graph workbench using Cytoscape.js in Streamlit.

    Parameters
    ----------
    elements : dict
        Graph elements data including nodes and edges. Each node should have
        an 'id', and 'label'. Each edge should have an 'id', 'source', 'target',
        and 'label'. Nodes can optionally include an 'expansion' object with
        'state', 'next_count', 'total_count', 'depth', and 'collapse_count' to
        show expand/collapse badges and exact side-panel totals.
    layout : Union[str, dict], default 'cose'
        Layout configuration for Cytoscape. A string selects a supported named
        layout, including ``"preset"``. A dictionary must contain a supported
        ``name`` and may override its Cytoscape options. Invalid names fail in
        Python before the browser mounts. Default is ``"cose"``. The supported
        layouts and defaults are available in
        ``st_graph_workbench.component.layouts``.
    node_styles : list[NodeStyle | StyleRule], default []
        Node label styles and optional selector-based rules applied to nodes.
    edge_styles : list[EdgeStyle | StyleRule], default []
        Edge label styles and optional selector-based rules applied to edges.
    height : int, default 500
        Component height in positive integer pixels. The frontend updates the
        container height on rerun and observes size changes so Cytoscape can
        resize without forcing a remount.
    key : str, default None
        A unique key for the component. If provided, this key allows multiple
        instances of the component to exist in the same Streamlit app without
        conflicts. Setting this parameter is also important to avoid unnecessary
        re-rendering of the component. The wrapper encodes this value into a
        Streamlit-safe internal component key, so similar values such as
        'case__left' and 'case--left' remain separate instances without using
        reserved bidirectional-component ID delimiters.
    on_change : callable, default None
        Optional Streamlit callback invoked when the component value changes.
        Read the latest event from the callback's component state or use the
        function's return value during ordinary reruns.
    node_actions : list[NodeAction], default []
        Enables node and neighborhood controls such as 'remove', 'expand',
        'show_neighbors', 'show_incoming', 'show_outgoing',
        'hide_unselected', and 'restore_hidden'. Expansion/collapse still emits
        the existing 'expand' action so callback behavior stays compatible.
    crud_actions : list[CrudAction], default []
        Enables browser-side CRUD intent buttons. The component emits an
        `action == "crud"` event with the requested operation and selected
        graph data; your Streamlit app remains responsible for changing
        `elements`, fetching external data, and persisting the graph.
    edit_actions : list[EditAction], default []
        Enables frontend-local editing tools such as add node, connect selected
        nodes, delete selected, lock/unlock selected nodes, make nodes
        grabbable/ungrabbable, snap to grid, undo, and redo. These actions emit
        `action == "edit"` events so Python can persist the changed graph. For
        large interactive editing, combine this with `elements_sync='initial'`
        and a stable `key`.
    viewport_actions : list[ViewportAction], default []
        Enables extra viewport tools such as toggling user zoom/pan, saving and
        restoring a browser-local viewport, and resetting pan/zoom.
    enable_node_actions : bool, default None (deprecated)
        Compatibility parameter retained for older examples. Use `node_actions`
        instead to enable node actions. If `enable_node_actions` is set to True
        and `node_actions` is not provided, default actions ('remove', 'expand')
        will be enabled.
    events : list[Event], default []
        For advanced usage only. A list of events to listen to.  When any of these
        events are triggered, the event information is sent back to the Streamlit
        app as the component's return value. The browser updates the listener
        set on rerun, so changing `events` does not require a new component key.
        Custom names cannot reuse built-in action names such as ``selection``,
        ``search``, ``analysis``, ``crud``, ``edit``, ``viewport``, or
        ``load_more``.
    validate : bool, default True
        Validates element IDs, edge references, compound parents, and expansion
        metadata in Python before rendering.
    selection_mode : Literal['single', 'multiple', 'box'], default 'single'
        Controls Cytoscape selection behavior. Box mode displays a Pan/Box
        select control so blank-canvas dragging can switch between viewport
        navigation and rectangular node selection.
    return_selection : bool, default False
        When True, selection changes are returned as Streamlit events without
        requiring a custom Event.
    search : bool, default False
        Shows a frontend search panel that highlights/selects matches and emits
        matched element data without hiding graph context.
    analysis_actions : list[AnalysisAction], default []
        Enables built-in graph analysis actions in the toolbox.
    return_positions : bool, default False
        Returns node positions after layout or drag updates. When
        ``connected_drag`` is configured, node-drag events also include a
        ``movement`` dictionary describing the operation, status, anchor,
        native and connected moved IDs, depth, candidate count, and limit.
    performance_profile : Literal['default', 'large', 'dense'], default 'default'
        Applies frontend rendering defaults for larger graphs. Large and dense
        profiles reduce animation, hide labels during viewport movement, and
        enable Cytoscape texture rendering hints without hiding edges during
        zoom or pan.
    min_zoom : float, default None
        Optional finite numeric lower bound for Cytoscape zoom. When both
        bounds are provided, `min_zoom` must be less than or equal to
        `max_zoom`.
    max_zoom : float, default None
        Optional finite numeric upper bound for Cytoscape zoom. When both
        bounds are provided, `max_zoom` must be greater than or equal to
        `min_zoom`.
    wheel_sensitivity : float, default None
        Optional finite numeric mouse-wheel zoom sensitivity passed to
        Cytoscape. Values must be greater than zero.
    graph_commands : list[GraphCommand], default []
        Incremental graph commands that the browser applies directly to the
        existing Cytoscape instance with `cy.batch(...)`. Commands require a
        stable `command_id` and are applied once per mounted component.
    elements_sync : Literal['always', 'initial'], default 'always'
        Controls when full `elements` are sent to the browser. Use `'always'`
        for backward-compatible full reconciliation on every rerun. Use
        `'initial'` with `graph_commands` for large graphs: full elements are
        sent on the first render, then only small commands are sent until the
        frontend requests a full sync or you remount/reset the component.
    progressive_loading : ProgressiveLoadConfig, default None
        Shows an in-canvas progress indicator and Load more button. A click
        returns ``action == "load_more"`` with the configured cursor, page
        size, loaded and total counts, remaining count, and current browser
        node/edge counts. Python remains responsible for fetching the next
        batch and sending it with an idempotent graph command. The option
        updates on a live component without remounting. Each request includes
        a unique ``request_id``. Echo it as ``acknowledged_request_id`` after
        handling a request, including a fetch failure, so the button becomes
        available again even if the cursor and counts did not change. Existing
        configurations can still complete a request by changing progress.

    expansion : dict, default None
        Opt-in branch controls from ``ExpansionController.describe(provider)``.
        Requires a stable key. Explicit ``expansion`` events request expand,
        load-more, collapse, protection, scoped search/analysis or bounded bulk
        work. Source records remain Python-owned; legacy expand events are
        unchanged when this option is omitted. Configuration updates do not
        require a remount. Loaded records are sent only when this is enabled.

    show_selection_details : bool, default True
        Initial selection-details preference, adjustable in the Selection menu.
        The checkbox hides details without clearing selected records or changing
        returned events. The panel's X clears selection without changing this
        preference. With a stable key, the browser preference
        survives reruns with the same argument. Changing this argument overrides
        that preference without remounting; a new key or browser reload starts
        with the supplied default. This is a display preference, not access control.

    connected_drag : ConnectedDragConfig, default None
        Opts into rigid connected-record dragging. The Selection menu can enable
        the behavior and choose one to three visible, undirected hops. Automatic
        followers are bounded by ``max_nodes``; explicitly selected nodes and
        compound descendants retain Cytoscape's native dragging behavior. The
        controls are hidden when this argument is omitted. With a stable key,
        unchanged Python defaults preserve browser choices; changed defaults
        override them without remounting.

    toolbar : ToolbarConfig, default None
        Configures the controls anchored above the graph. Adaptive mode uses the
        expanded presentation when space permits and compact icon menus at
        narrower widths. Readers can minimize and restore the toolbar when
        ``collapsible`` is true. With ``sticky`` true, its measured height is
        reserved instead of covering graph nodes. A stable component key
        preserves the reader's minimized preference through ordinary reruns;
        changing the Python configuration resets that preference.

    Returns
    -------
    GraphEvent or None
        The latest JSON-compatible browser event dictionary, or ``None`` before
        an enabled interaction emits a value. Event fields depend on the action;
        the event and feature guides document every returned payload shape.

    Raises
    ------
    TypeError
        If an option, style, event, command, or element has the wrong Python type.
    ValueError
        If an option value, layout, viewport bound, ID, graph relationship, or
        command transition is invalid. Specialized validation errors subclass
        ``ValueError`` and identify the failing record or command.
    """
    node_styles = [] if node_styles is None else node_styles
    if not isinstance(show_selection_details, bool):
        raise TypeError("show_selection_details must be a bool.")
    edge_styles = [] if edge_styles is None else edge_styles
    node_actions = _normalize_option_values("node_actions", node_actions)
    crud_actions = _normalize_option_values("crud_actions", crud_actions)
    edit_actions = _normalize_option_values("edit_actions", edit_actions)
    viewport_actions = _normalize_option_values("viewport_actions", viewport_actions)
    events = [] if events is None else events
    analysis_actions = _normalize_option_values(
        "analysis_actions",
        analysis_actions,
    )
    graph_commands = [] if graph_commands is None else graph_commands
    height = _normalize_height(height)
    min_zoom, max_zoom, wheel_sensitivity = _normalize_viewport_options(
        min_zoom,
        max_zoom,
        wheel_sensitivity,
    )
    component_key = _component_instance_key(key)
    progressive_loading = _normalize_progressive_loading(progressive_loading)
    connected_drag = _normalize_connected_drag(connected_drag)
    toolbar = _normalize_toolbar(toolbar)
    if expansion is not None:
        if not isinstance(expansion, dict) or not isinstance(
            expansion.get("nodes"), dict
        ):
            raise ValueError(
                "expansion must be configuration from ExpansionController.describe()."
            )
        if component_key is None:
            raise ValueError("A stable key is required for managed expansion.")
        for field, kind in {
            "controller_id": str,
            "source_id": str,
            "source_version": str,
            "view_revision": int,
            "limits": dict,
            "branches": list,
            "loaded": dict,
        }.items():
            if not isinstance(expansion.get(field), kind):
                raise ValueError(
                    f"Managed expansion requires a valid {field}; use controller.describe()."
                )
        ExpansionConfig(**expansion["limits"])
        validate_elements(expansion["loaded"])

    if validate:
        validate_elements(elements, strict=True)
        validate_graph_commands(graph_commands, elements=elements)
    else:
        validate_graph_commands(graph_commands)

    _validate_option_values(
        node_actions,
        crud_actions,
        edit_actions,
        viewport_actions,
        selection_mode,
        analysis_actions,
        performance_profile,
        elements_sync,
        component_key,
    )

    node_styles_dump = [n.dump() for n in node_styles]
    edge_styles_dump = [e.dump() for e in edge_styles]
    style = node_styles_dump + edge_styles_dump

    height_str = f"{height}px"

    layout_config = resolve_layout(layout)

    events_dump = [e.dump() for e in events]

    if enable_node_actions is not None:
        warnings.warn(
            "Parameter `enable_node_actions` is deprecated. Please use the "
            "`node_actions` parameter instead.",
            GraphWorkbenchDeprecationWarning,
        )
    if enable_node_actions and not node_actions:
        node_actions = ["remove", "expand"]

    send_elements = True
    sync_state_key = None
    if elements_sync == "initial" and component_key is not None:
        sync_state_key = _elements_sync_state_key(component_key)
        send_elements = not bool(st.session_state.get(sync_state_key, False))

    def handle_event_change() -> None:
        event = (
            _extract_event(st.session_state.get(component_key))
            if component_key is not None
            else None
        )
        if _is_sync_request(event):
            if sync_state_key is not None:
                st.session_state[sync_state_key] = False
            return
        if key is not None and component_key is not None:
            st.session_state[key] = event
        if on_change is not None:
            on_change()

    receipt_key = f"{component_key}:request-receipts"
    result_key = f"{component_key}:request-result"
    command_queue_key = f"{component_key}:pending-commands"
    command_receipt_key = f"{component_key}:command-receipts"
    if expansion is not None:
        pending = dict(st.session_state.get(command_queue_key, {}))
        completed = set(st.session_state.get(command_receipt_key, []))
        for command in graph_commands:
            identity = str(command["command_id"])
            if identity not in completed:
                pending[identity] = command
        st.session_state[command_queue_key] = pending
        graph_commands = list(pending.values())

    def handle_command_receipts_change() -> None:
        if expansion is None or component_key is None:
            return
        value = st.session_state.get(component_key, {})
        receipts = _component_field(value, "command_receipts")
        completed = set(st.session_state.get(command_receipt_key, []))
        pending = dict(st.session_state.get(command_queue_key, {}))
        for identity in receipts or []:
            if isinstance(identity, str):
                completed.add(identity)
                pending.pop(identity, None)
        st.session_state[command_queue_key] = pending
        st.session_state[command_receipt_key] = sorted(completed)

    def handle_requests_change() -> None:
        if component_key is None:
            return
        value = st.session_state.get(component_key, {})
        requests = _component_field(value, "requests")
        requests = requests if isinstance(requests, list) else []
        valid_requests = []
        for event in requests:
            if not isinstance(event, dict) or event.get("action") not in {
                "expansion",
                "load_more",
            }:
                continue
            data = event.get("data")
            identity = data.get("request_id") if isinstance(data, dict) else None
            if isinstance(identity, str) and identity:
                valid_requests.append((identity, event))
        receipts = list(st.session_state.get(receipt_key, []))
        # Retain receipts until the browser removes their queued requests.
        retained = {identity for identity, _ in valid_requests} | set(receipts[-256:])
        receipts = [identity for identity in receipts if identity in retained]
        seen = set(receipts)
        st.session_state[receipt_key] = receipts
        for request_id, event in valid_requests:
            if request_id in seen:
                continue
            if key is not None:
                st.session_state[key] = event
            if on_change is not None:
                on_change()
            receipts.append(request_id)
            seen.add(request_id)
            st.session_state[receipt_key] = receipts
            st.session_state[result_key] = event
            if on_change is None:
                # Return-only applications consume one request per rerun.
                break

    component_result = _component_func(
        data={
            "elements": elements if send_elements else None,
            "style": style,
            "layout": layout_config,
            "height": height_str,
            "nodeActions": node_actions,
            "crudActions": crud_actions,
            "editActions": edit_actions,
            "viewportActions": viewport_actions,
            "graphCommands": graph_commands,
            "elementsSync": elements_sync,
            "componentKey": component_key,
            "events": events_dump,
            "assetBasePath": f"./_stcore/bidi-components/{_COMPONENT_NAME}",
            "selectionMode": selection_mode,
            "returnSelection": return_selection,
            "showSelectionDetails": show_selection_details,
            "search": search,
            "analysisActions": analysis_actions,
            "returnPositions": return_positions,
            "performanceProfile": performance_profile,
            "viewportOptions": {
                "minZoom": min_zoom,
                "maxZoom": max_zoom,
                "wheelSensitivity": wheel_sensitivity,
            },
            "progressiveLoading": progressive_loading,
            "expansion": expansion,
            "connectedDrag": connected_drag,
            "toolbar": toolbar,
            "receivedRequestIds": list(st.session_state.get(receipt_key, [])),
        },
        height=height,
        key=component_key,
        on_event_change=handle_event_change,
        on_requests_change=handle_requests_change,
        on_command_receipts_change=handle_command_receipts_change,
    )

    if sync_state_key is not None and send_elements:
        st.session_state[sync_state_key] = True

    event = _extract_event(component_result)
    event = st.session_state.pop(result_key, None) or event
    if _is_sync_request(event):
        if sync_state_key is not None:
            st.session_state[sync_state_key] = False
        return None
    if key is not None and event is not None:
        st.session_state[key] = event
    return event
