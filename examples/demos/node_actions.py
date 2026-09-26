import copy

import streamlit as st

from demos.demo_helpers import (
    demo_edge_styles,
    demo_graph,
    demo_node_styles,
    render_demo_intro,
    render_dictionary_preview,
    render_elements_dataframe,
    render_source_expander,
)
from st_graph_workbench import delete_elements, graph_workbench, upsert_elements


STATE_KEY = "node_actions_demo_elements"
EXPANDED_KEY = "node_actions_demo_expanded"
LAST_EVENT_TS_KEY = "node_actions_demo_last_event_timestamp"
LAST_EVENT_KEY = "node_actions_demo_last_event"
NOTICE_KEY = "node_actions_demo_notice"
COMPONENT_KEY = "NODE_ACTIONS"

EXPANSION_DATA = {
    "ABC123": {
        "nodes": [
            {
                "data": {
                    "id": "Person_MReed",
                    "label": "PERSON",
                    "name": "Maya Reed",
                },
                "position": {"x": 610, "y": 130},
            },
            {
                "data": {
                    "id": "Phone_0412",
                    "label": "PHONE",
                    "name": "0412 000 111",
                },
                "position": {"x": 610, "y": 330},
            },
        ],
        "edges": [
            {
                "data": {
                    "id": "ABC123-Person_MReed",
                    "label": "Registered To",
                    "source": "ABC123",
                    "target": "Person_MReed",
                }
            },
            {
                "data": {
                    "id": "Person_MReed-Phone_0412",
                    "label": "Uses",
                    "source": "Person_MReed",
                    "target": "Phone_0412",
                }
            },
        ],
    }
}


def _coerce_position(value):
    if not isinstance(value, dict):
        return None
    try:
        return {
            "x": round(float(value["x"]), 2),
            "y": round(float(value["y"]), 2),
        }
    except (KeyError, TypeError, ValueError):
        return None


def update_node_positions(elements, positions):
    positions_by_id = {}
    for item in positions:
        if not isinstance(item, dict):
            continue
        node_id = item.get("id")
        position = _coerce_position(item.get("position"))
        if node_id is not None and position is not None:
            positions_by_id[str(node_id)] = position

    if not positions_by_id:
        return elements

    updated = copy.deepcopy(elements)
    for node in updated.get("nodes", []):
        node_id = str(node.get("data", {}).get("id"))
        if node_id in positions_by_id:
            node["position"] = positions_by_id[node_id]
    return updated


def position_rows(elements):
    rows = []
    for node in elements.get("nodes", []):
        data = node.get("data", {})
        position = _coerce_position(node.get("position"))
        if position is None:
            continue
        rows.append(
            {
                "node id": data.get("id"),
                "label": data.get("label"),
                "display name": data.get("name"),
                "x": position["x"],
                "y": position["y"],
            }
        )
    return sorted(rows, key=lambda item: str(item["node id"]))


def base_elements() -> dict[str, list[dict]]:
    graph = demo_graph()
    expansion_node_ids = {
        str(node["data"]["id"])
        for additions in EXPANSION_DATA.values()
        for node in additions["nodes"]
    }
    return {
        "nodes": [
            node
            for node in graph["nodes"]
            if str(node["data"]["id"]) not in expansion_node_ids
        ],
        "edges": [
            edge
            for edge in graph["edges"]
            if str(edge["data"]["source"]) not in expansion_node_ids
            and str(edge["data"]["target"]) not in expansion_node_ids
        ],
    }


def ensure_state() -> None:
    st.session_state.setdefault(STATE_KEY, base_elements())
    st.session_state.setdefault(EXPANDED_KEY, set())
    st.session_state.setdefault(LAST_EVENT_TS_KEY, None)
    st.session_state.setdefault(LAST_EVENT_KEY, None)
    st.session_state.setdefault(NOTICE_KEY, "")


def with_expansion_badges(elements: dict[str, list[dict]]) -> dict[str, list[dict]]:
    graph = copy.deepcopy(elements)
    visible_ids = {str(node["data"]["id"]) for node in graph["nodes"]}
    for node in graph["nodes"]:
        node_id = str(node["data"]["id"])
        additions = EXPANSION_DATA.get(node_id)
        if not additions:
            continue
        hidden_nodes = [
            item
            for item in additions["nodes"]
            if str(item["data"]["id"]) not in visible_ids
        ]
        if hidden_nodes:
            node["data"]["expansion"] = {
                "state": "collapsed",
                "next_count": len(hidden_nodes),
                "total_count": len(hidden_nodes),
                "depth": 1,
            }
        else:
            node["data"]["expansion"] = {
                "state": "expanded",
                "collapse_count": len(additions["nodes"]),
                "total_count": 0,
                "depth": 0,
            }
    return graph


def toggle_expansion(node_id: str) -> None:
    additions = EXPANSION_DATA.get(node_id)
    if not additions:
        st.session_state[NOTICE_KEY] = f"No expansion data for `{node_id}`."
        return

    if node_id in st.session_state[EXPANDED_KEY]:
        st.session_state[STATE_KEY] = delete_elements(
            st.session_state[STATE_KEY],
            node_ids=[node["data"]["id"] for node in additions["nodes"]],
            remove_incident_edges=True,
        )
        st.session_state[EXPANDED_KEY].remove(node_id)
        st.session_state[NOTICE_KEY] = f"Collapsed `{node_id}`."
        return

    st.session_state[STATE_KEY] = upsert_elements(
        st.session_state[STATE_KEY],
        nodes=additions["nodes"],
        edges=additions["edges"],
    )
    st.session_state[EXPANDED_KEY].add(node_id)
    st.session_state[NOTICE_KEY] = f"Expanded `{node_id}`."


def handle_graph_event() -> None:
    event = st.session_state.get(COMPONENT_KEY)
    if not isinstance(event, dict):
        return

    timestamp = event.get("timestamp")
    if timestamp == st.session_state.get(LAST_EVENT_TS_KEY):
        return

    st.session_state[LAST_EVENT_TS_KEY] = timestamp
    action = event.get("action")
    data = event.get("data", {})

    if action == "positions":
        positions = data.get("positions", [])
        if isinstance(positions, list):
            st.session_state[STATE_KEY] = update_node_positions(
                st.session_state[STATE_KEY],
                positions,
            )
        return

    if action == "selection":
        return

    st.session_state[LAST_EVENT_KEY] = event

    if action == "expand":
        for node_id in data.get("node_ids", []):
            toggle_expansion(str(node_id))
        return

    if action == "remove":
        st.session_state[STATE_KEY] = delete_elements(
            st.session_state[STATE_KEY],
            node_ids=data.get("node_ids", []),
            remove_incident_edges=True,
        )
        st.session_state[NOTICE_KEY] = "Removed selected node(s) in Python state."


ensure_state()

render_demo_intro(
    "Node actions",
    """
    This demo isolates `node_actions`. Expansion and removal are handled in
    Python; neighbor and visibility tools are browser-side exploration helpers.
    Expandable nodes can be opened from the toolbar or by right-clicking the
    node and choosing expand/collapse.
    """,
    [
        (
            "Expansion",
            "`expand` emits selected node IDs from the toolbar, double-click, or right-click context menu.",
        ),
        (
            "Removal",
            "`remove` emits node IDs so Python can delete nodes and incident edges.",
        ),
        (
            "Exploration",
            "`show_neighbors`, `show_incoming`, and `show_outgoing` filter context.",
        ),
        (
            "Visibility",
            "`hide_unselected` and `restore_hidden` manage what stays visible.",
        ),
        (
            "Positions",
            "`return_positions=True` preserves manual node shuffles during expansion reruns.",
        ),
    ],
    sections=[
        (
            "Capability coverage",
            "The node actions exposed through toolbar buttons, double-clicks, and the right-click menu.",
        ),
        (
            "Data before rendering",
            "The Python-owned graph dictionary and expansion records available to the page.",
        ),
        (
            "Interactive graph",
            "A graph that supports expand, collapse, remove, neighbor filters, visibility tools, and search.",
        ),
        (
            "Try these checks",
            "Concrete interactions for expansion, position preservation, visibility, and removal.",
        ),
        (
            "Returned dictionaries",
            "Node-action payloads and saved position records returned to Python.",
        ),
    ],
)

if st.button("Reset node-action graph", icon=":material/restart_alt:"):
    st.session_state[STATE_KEY] = base_elements()
    st.session_state[EXPANDED_KEY] = set()
    st.session_state[LAST_EVENT_KEY] = None
    st.session_state[NOTICE_KEY] = ""
    st.rerun()

if st.session_state[NOTICE_KEY]:
    st.info(st.session_state[NOTICE_KEY])

elements = with_expansion_badges(st.session_state[STATE_KEY])

st.markdown("## Data before rendering")
st.markdown(
    """
    The graph below is backed by this Python dictionary. Expansion changes the
    dictionary, and position events update each node's `position` so the graph
    can return to the same analyst-arranged layout after a rerun.
    """
)
render_elements_dataframe(elements, "Python-owned node-action graph")

st.markdown("#### Expansion records available to Python")
st.dataframe(
    [
        {
            "expand node": node_id,
            "new nodes": len(additions["nodes"]),
            "new edges": len(additions["edges"]),
            "example returned records": ", ".join(
                str(node["data"]["name"]) for node in additions["nodes"]
            ),
        }
        for node_id, additions in sorted(EXPANSION_DATA.items())
    ],
    hide_index=True,
)

st.markdown("## Interactive graph")
value = graph_workbench(
    elements,
    layout={"name": "preset", "fit": True, "padding": 140},
    node_styles=demo_node_styles(),
    edge_styles=demo_edge_styles(),
    key=COMPONENT_KEY,
    node_actions=[
        "remove",
        "expand",
        "show_neighbors",
        "show_incoming",
        "show_outgoing",
        "hide_unselected",
        "restore_hidden",
    ],
    selection_mode="multiple",
    return_selection=True,
    return_positions=True,
    search=True,
    on_change=handle_graph_event,
    height=700,
)

st.markdown("## Try these checks")
st.markdown(
    """
    - Select `ABC123`, then use the toolbar expand button or right-click the
      node and choose expand to load related person and phone records from
      Python.
    - Drag `ABC123` or a location before expanding it; the position table below
      records the latest coordinates returned from the browser.
    - Select any visible node and use neighbors, incoming, and outgoing to see
      how browser-side visibility filters differ.
    - Hide unselected elements, then restore the hidden graph.
    - Select a node and use remove to delete it from Python-owned state.
    """
)

render_dictionary_preview(
    "Returned node-action value",
    st.session_state[LAST_EVENT_KEY] or value or {},
    """
    This dictionary shows the latest meaningful node-action event. Expansion
    returns the node IDs Python should expand or collapse; removal returns the
    node IDs Python should delete from session state.
    """,
    height=340,
    expanded=True,
)

st.markdown("#### Saved node positions")
st.dataframe(position_rows(elements), hide_index=True)
render_source_expander(__file__)
