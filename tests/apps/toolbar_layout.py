"""Responsive toolbar fixture with explicit Python option changes."""

import streamlit as st

from st_graph_workbench import NodeStyle, graph_workbench

st.set_page_config(layout="wide")

mode = st.selectbox(
    "Python toolbar mode",
    ["adaptive", "expanded", "compact", "minimized"],
)
sticky = st.checkbox("Reserve toolbar space", value=True)
collapsible = st.checkbox("Allow minimizing", value=True)
st.button("Rerun")

elements = {
    "nodes": [
        {
            "data": {"id": "a", "label": "RECORD", "name": "Record A"},
            "position": {"x": 260, "y": 220},
        },
        {
            "data": {"id": "b", "label": "RECORD", "name": "Record B"},
            "position": {"x": 520, "y": 340},
        },
    ],
    "edges": [{"data": {"id": "ab", "source": "a", "target": "b"}}],
}

graph_workbench(
    elements,
    key="toolbar-layout-primary",
    layout={"name": "preset", "fit": False},
    node_styles=[NodeStyle("RECORD", "#2A629A", "name", "description")],
    node_actions=["show_neighbors"],
    crud_actions=["read_selected"],
    edit_actions=["add_node"],
    viewport_actions=["toggle_pan"],
    analysis_actions=["degree"],
    return_selection=True,
    return_positions=True,
    search=True,
    progressive_loading={
        "page_size": 10,
        "loaded_count": 2,
        "total_count": 20,
        "has_more": True,
        "cursor": 2,
    },
    toolbar={
        "mode": mode,
        "position": "top",
        "collapsible": collapsible,
        "sticky": sticky,
    },
    height=620,
)
