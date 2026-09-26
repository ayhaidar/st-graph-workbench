import copy

import streamlit as st

from demos.demo_helpers import (
    capability_rows,
    render_capability_summary,
    render_dictionary_preview,
    render_elements_dataframe,
    render_source_expander,
)
from page_overview import render_page_overview
from st_graph_workbench import (
    EdgeStyle,
    EditAction,
    NodeStyle,
    ViewportAction,
    delete_elements,
    graph_workbench,
    upsert_elements,
    validate_elements,
)


STATE_KEY = "editing_viewport_demo_elements"
LAST_EVENT_TS_KEY = "editing_viewport_demo_last_event_timestamp"
LAST_EVENT_KEY = "editing_viewport_demo_last_event"
EPOCH_KEY = "editing_viewport_demo_epoch"
STATE_VERSION_KEY = "editing_viewport_demo_state_version"
STATE_VERSION = 2

EDIT_ACTIONS: list[EditAction] = [
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

VIEWPORT_ACTIONS: list[ViewportAction] = [
    "toggle_zoom",
    "toggle_pan",
    "save_viewport",
    "restore_viewport",
    "reset_viewport",
]


INITIAL_ELEMENTS = {
    "nodes": [
        {
            "data": {
                "id": "case",
                "label": "CASE",
                "name": "Case Alpha",
                "risk": "high",
            },
            "position": {"x": 0, "y": 0},
        },
        {
            "data": {
                "id": "vehicle",
                "label": "MAIN_VEHICLE",
                "name": "ABC123",
                "risk": "high",
            },
            "position": {"x": 190, "y": -70},
        },
        {
            "data": {
                "id": "person",
                "label": "PERSON",
                "name": "Maya Reed",
                "risk": "medium",
            },
            "position": {"x": 200, "y": 130},
        },
        {
            "data": {
                "id": "time_window",
                "label": "TIME",
                "name": "02 Sep 2024 08:14",
                "risk": "high",
            },
            "position": {"x": 410, "y": 20},
        },
        {
            "data": {
                "id": "device",
                "label": "DEVICE",
                "name": "Phone 0412",
                "risk": "low",
            },
            "position": {"x": 90, "y": 230},
        },
    ],
    "edges": [
        {
            "data": {
                "id": "case-vehicle",
                "label": "INVESTIGATES",
                "source": "case",
                "target": "vehicle",
            }
        },
        {
            "data": {
                "id": "vehicle-time",
                "label": "OBSERVED_DURING",
                "source": "vehicle",
                "target": "time_window",
            }
        },
        {
            "data": {
                "id": "person-vehicle",
                "label": "REGISTERED_TO",
                "source": "person",
                "target": "vehicle",
            }
        },
        {
            "data": {
                "id": "person-device",
                "label": "USES",
                "source": "person",
                "target": "device",
            }
        },
    ],
}


def initialize_state() -> None:
    if st.session_state.get(STATE_VERSION_KEY) != STATE_VERSION:
        st.session_state[STATE_KEY] = copy.deepcopy(INITIAL_ELEMENTS)
        st.session_state[EPOCH_KEY] = st.session_state.get(EPOCH_KEY, 0) + 1
        st.session_state.pop(LAST_EVENT_KEY, None)
        st.session_state.pop(LAST_EVENT_TS_KEY, None)
        st.session_state[STATE_VERSION_KEY] = STATE_VERSION
        return

    if STATE_KEY not in st.session_state:
        st.session_state[STATE_KEY] = copy.deepcopy(INITIAL_ELEMENTS)
    if EPOCH_KEY not in st.session_state:
        st.session_state[EPOCH_KEY] = 0


def split_elements(elements):
    if isinstance(elements, dict):
        return elements.get("nodes", []), elements.get("edges", [])

    nodes = []
    edges = []
    for element in elements or []:
        group = element.get("group")
        if group == "edges" or "source" in element.get("data", {}):
            edges.append(element)
        else:
            nodes.append(element)
    return nodes, edges


def set_positions(elements, positions):
    graph = copy.deepcopy(elements)
    by_id = {position["id"]: position["position"] for position in positions}
    for node in graph["nodes"]:
        node_id = node["data"]["id"]
        if node_id in by_id:
            node["position"] = by_id[node_id]
    validate_elements(graph)
    return graph


def mirror_edit_event(event) -> None:
    if not isinstance(event, dict) or event.get("action") != "edit":
        return

    timestamp = event.get("timestamp")
    if timestamp == st.session_state.get(LAST_EVENT_TS_KEY):
        return

    st.session_state[LAST_EVENT_TS_KEY] = timestamp
    st.session_state[LAST_EVENT_KEY] = event
    data = event.get("data", {})
    operation = data.get("operation")
    graph = st.session_state[STATE_KEY]

    if "elements" in data:
        nodes, edges = split_elements(data["elements"])
        st.session_state[STATE_KEY] = {"nodes": nodes, "edges": edges}
        validate_elements(st.session_state[STATE_KEY])
        return

    if operation in {"add_node", "connect_selected"}:
        nodes, edges = split_elements(data.get("added_elements", []))
        st.session_state[STATE_KEY] = upsert_elements(
            graph, nodes=nodes, edges=edges, replace=True
        )
        return

    if operation == "delete_selected":
        st.session_state[STATE_KEY] = delete_elements(
            graph,
            node_ids=data.get("deleted_node_ids", []),
            edge_ids=data.get("deleted_edge_ids", []),
            remove_incident_edges=True,
        )
        return

    if operation in {
        "lock_selected",
        "unlock_selected",
        "make_ungrabbable",
        "make_grabbable",
    }:
        nodes, edges = split_elements(data.get("updated_elements", []))
        st.session_state[STATE_KEY] = upsert_elements(
            graph, nodes=nodes, edges=edges, replace=True
        )
        return

    if operation == "snap_to_grid":
        st.session_state[STATE_KEY] = set_positions(graph, data.get("positions", []))


def mirror_positions_event(event) -> None:
    if not isinstance(event, dict) or event.get("action") != "positions":
        return

    timestamp = event.get("timestamp")
    if timestamp == st.session_state.get(LAST_EVENT_TS_KEY):
        return

    st.session_state[LAST_EVENT_TS_KEY] = timestamp
    st.session_state[LAST_EVENT_KEY] = event
    st.session_state[STATE_KEY] = set_positions(
        st.session_state[STATE_KEY],
        event.get("data", {}).get("positions", []),
    )


initialize_state()

st.markdown("# Editing And Viewport Tools")
st.markdown(
    """
    This page demonstrates browser-side graph editing controls and extra
    viewport controls. The edit happens immediately in Cytoscape, then the
    event payload below mirrors the change into Streamlit session state.
    """
)

render_page_overview(
    [
        (
            "Capability coverage",
            "Browser editing, viewport controls, and incremental graph-state mirroring.",
        ),
        (
            "Editing controls",
            "Profile selection, reset behavior, add/connect/delete/lock/snap/undo/redo tools.",
        ),
        (
            "Data before rendering",
            "The current Python-owned graph that browser edits and positions update.",
        ),
        (
            "Interactive graph",
            "A browser-editable graph whose events are mirrored back into Streamlit session state.",
        ),
        (
            "Executed output",
            "The current graph table, returned edit/viewport payload, and mirrored state.",
        ),
        (
            "Try these checks",
            "Small interactions that verify browser edits, saved viewport, and state preservation.",
        ),
    ],
    description="This editing overview summarizes the page before the editable graph appears.",
)

render_capability_summary(
    "What this demo covers",
    [
        row
        for row in capability_rows()
        if row["capability"]
        in {
            "Browser editing",
            "Viewport controls",
            "Incremental browser updates",
        }
    ],
    description="The browser-editing and viewport controls demonstrated on this page.",
)

left, middle, right = st.columns([0.45, 0.35, 0.2])
with left:
    performance_profile = st.segmented_control(
        "Performance profile",
        ["default", "large", "dense"],
        default="large",
        key="editing_viewport_profile",
    )
with middle:
    use_custom_wheel_sensitivity = st.toggle(
        "Custom wheel sensitivity",
        value=False,
        help=(
            "Leave this off for Cytoscape's native wheel behavior. Turn it on "
            "when you want to demonstrate the optional graph_workbench setting."
        ),
        key="editing_viewport_custom_wheel",
    )
with right:
    if st.button("Reset demo graph", type="secondary"):
        st.session_state[STATE_KEY] = copy.deepcopy(INITIAL_ELEMENTS)
        st.session_state[EPOCH_KEY] += 1
        st.session_state.pop(LAST_EVENT_KEY, None)
        st.session_state.pop(LAST_EVENT_TS_KEY, None)
        st.rerun()

wheel_sensitivity = None
if use_custom_wheel_sensitivity:
    wheel_sensitivity = st.slider(
        "Wheel sensitivity",
        min_value=0.05,
        max_value=1.0,
        value=0.18,
        step=0.01,
        help="Passed to graph_workbench(..., wheel_sensitivity=...).",
        key="editing_viewport_wheel_sensitivity",
    )

wheel_key = f"{wheel_sensitivity:.2f}" if wheel_sensitivity is not None else "native"

st.markdown("## Data before rendering")
st.markdown(
    """
    This dataframe is the authoritative Streamlit-side graph before the browser
    component renders. Browser edit events update these records so a refreshed
    page keeps added nodes, deleted edges, locks, and manual positions.
    """
)
render_elements_dataframe(st.session_state[STATE_KEY], "Current editable graph records")

event = graph_workbench(
    st.session_state[STATE_KEY],
    layout={"name": "preset", "fit": True, "padding": 40},
    node_styles=[
        NodeStyle("CASE", color="#2f4858", caption="name", icon="folder", size=34),
        NodeStyle(
            "MAIN_VEHICLE",
            color="#33658a",
            caption="name",
            icon="directions_car",
        ),
        NodeStyle("PERSON", color="#f26419", caption="name", icon="person"),
        NodeStyle("TIME", color="#7a5195", caption="name", icon="schedule"),
        NodeStyle("DEVICE", color="#3a7d44", caption="name", icon="smartphone"),
        NodeStyle("NODE", color="#6c757d", caption="name"),
    ],
    edge_styles=[
        EdgeStyle("INVESTIGATES", color="#2f4858", directed=True),
        EdgeStyle("OBSERVED_DURING", color="#7a5195", directed=True),
        EdgeStyle("REGISTERED_TO", color="#f26419", directed=True),
        EdgeStyle("USES", color="#3a7d44", directed=True),
        EdgeStyle("RELATED", color="#6c757d", directed=True, line_style="dashed"),
    ],
    selection_mode="multiple",
    return_selection=True,
    return_positions=True,
    edit_actions=EDIT_ACTIONS,
    viewport_actions=VIEWPORT_ACTIONS,
    performance_profile=performance_profile,
    min_zoom=0.15,
    max_zoom=4,
    wheel_sensitivity=wheel_sensitivity,
    elements_sync="initial",
    height=620,
    key=(
        f"editing-viewport-demo-{st.session_state[EPOCH_KEY]}-"
        f"{performance_profile}-{wheel_key}"
    ),
)

mirror_edit_event(event)
mirror_positions_event(event)
if isinstance(event, dict) and event.get("action") not in {
    "edit",
    "positions",
    "selection",
}:
    st.session_state[LAST_EVENT_KEY] = event

node_count = len(st.session_state[STATE_KEY]["nodes"])
edge_count = len(st.session_state[STATE_KEY]["edges"])
st.markdown("## Executed output")
metric_row = st.container(horizontal=True)
metric_row.metric("Python-state nodes", node_count)
metric_row.metric("Python-state edges", edge_count)
metric_row.metric(
    "Last event", st.session_state.get(LAST_EVENT_KEY, {}).get("action", "none")
)

st.markdown("### Try These Checks")
st.markdown(
    """
    1. Open **Edit**, click **Add Browser Node**, and confirm the node count
       increases.
    2. Select two nodes, then click **Connect Two Selected Nodes**.
    3. Select a node or edge, then click **Delete Selected**.
    4. Drag a node, open **Edit**, and use **Snap Nodes to Grid**.
    5. Select a node, use **Lock Selected Nodes** or **Make Selected Nodes
       Fixed**, then restore it with **Unlock Selected Nodes** or **Make
       Selected Nodes Draggable** and drag it again.
    6. Open **Viewport**, save the current view, pan or zoom, then restore it.
    7. Toggle user zoom or pan, then try the mouse wheel or canvas dragging.
    """
)

render_dictionary_preview(
    "Last component event",
    st.session_state.get(LAST_EVENT_KEY, event),
    """
    This dictionary describes the latest browser edit or viewport action. The
    `operation` field explains what changed, while selected IDs, positions, pan,
    or zoom values let Python mirror or document the browser state.
    """,
    height=340,
    expanded=True,
)

render_dictionary_preview(
    "Current Python-owned elements",
    st.session_state[STATE_KEY],
    """
    This dictionary is the authoritative graph state held by Streamlit. Browser
    edit and position events are applied back into this `nodes` and `edges`
    structure so the graph can be rebuilt or exported later with the latest
    manual layout.
    """,
    height=360,
    expanded=True,
)

render_source_expander(__file__)
