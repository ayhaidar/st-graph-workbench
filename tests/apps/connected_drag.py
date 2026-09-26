"""Deterministic connected-drag fixture with two independent graph instances."""

from __future__ import annotations

from typing import Any

import streamlit as st

from st_graph_workbench import graph_workbench

st.set_page_config(layout="wide")

GRAPH_KEY = "connected-drag-primary"
st.session_state.setdefault("connected_drag_event", {})


def remember_event() -> None:
    event = st.session_state.get(GRAPH_KEY, {})
    if not isinstance(event, dict):
        return
    st.session_state.connected_drag_event = event


configured = st.checkbox("Configure connected dragging", value=True)
python_enabled = st.checkbox("Python connected-drag default", value=False)
python_depth = st.select_slider("Python depth", options=[1, 2, 3], value=1)
max_depth = st.select_slider("Maximum depth", options=[1, 2, 3], value=3)
max_nodes = st.number_input("Maximum connected nodes", min_value=1, value=100)
st.button("Rerun")

elements: dict[str, list[dict[str, Any]]] = {
    "nodes": [
        {"data": {"id": "a", "name": "Anchor"}, "position": {"x": 100, "y": 180}},
        {"data": {"id": "b", "name": "One hop"}, "position": {"x": 250, "y": 180}},
        {"data": {"id": "c", "name": "Two hops"}, "position": {"x": 400, "y": 180}},
        {"data": {"id": "d", "name": "Three hops"}, "position": {"x": 550, "y": 180}},
        {"data": {"id": "branch", "name": "Branch"}, "position": {"x": 250, "y": 330}},
        {
            "data": {"id": "locked", "name": "Locked"},
            "position": {"x": 100, "y": 330},
            "locked": True,
        },
        {
            "data": {"id": "fixed", "name": "Ungrababble"},
            "position": {"x": 400, "y": 330},
            "grabbable": False,
        },
        {
            "data": {"id": "unrelated", "name": "Unrelated"},
            "position": {"x": 700, "y": 330},
        },
    ],
    "edges": [
        {"data": {"id": "ab", "source": "a", "target": "b"}},
        {"data": {"id": "bc", "source": "b", "target": "c"}},
        {"data": {"id": "cd", "source": "c", "target": "d"}},
        {"data": {"id": "ba", "source": "b", "target": "a"}},
        {"data": {"id": "b-branch", "source": "b", "target": "branch"}},
        {"data": {"id": "a-locked", "source": "a", "target": "locked"}},
        {"data": {"id": "c-fixed", "source": "c", "target": "fixed"}},
    ],
}

config = None
if configured:
    config = {
        "enabled": python_enabled,
        "depth": min(python_depth, max_depth),
        "max_depth": max_depth,
        "max_nodes": int(max_nodes),
    }

graph_workbench(
    elements,
    key=GRAPH_KEY,
    layout={"name": "preset", "fit": False},
    height=560,
    selection_mode="multiple",
    show_selection_details=False,
    return_positions=True,
    connected_drag=config,
    elements_sync="initial",
    on_change=remember_event,
)

st.subheader("Last movement")
movement = st.session_state.connected_drag_event.get("data", {}).get("movement", {})
st.json(movement)

graph_workbench(
    elements,
    key="connected-drag-secondary",
    layout={"name": "preset", "fit": False},
    height=300,
    connected_drag={"enabled": True, "depth": 1, "max_depth": 1, "max_nodes": 10},
    elements_sync="initial",
)
limited_value = graph_workbench(
    elements,
    key="connected-drag-limited",
    layout={"name": "preset", "fit": False},
    height=300,
    show_selection_details=False,
    return_positions=True,
    connected_drag={"enabled": True, "depth": 2, "max_depth": 3, "max_nodes": 1},
    elements_sync="initial",
)
st.json(limited_value or {})
