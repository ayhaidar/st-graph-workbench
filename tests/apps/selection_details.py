"""Deterministic UI-preference fixture with independent graph instances."""

import streamlit as st

from st_graph_workbench import NodeStyle, graph_workbench

st.set_page_config(layout="wide")
st.session_state.setdefault("revision", 0)
st.session_state.setdefault("events", 0)
st.session_state.setdefault("updated", False)
st.session_state.setdefault("removed", False)
st.session_state["render_count"] = st.session_state.get("render_count", 0) + 1


def receive():
    st.session_state.events += 1


default_details = st.checkbox("Python details preference", value=True)
mode = st.selectbox("Selection mode", ["single", "multiple", "box"])
with st.container(horizontal=True):
    st.button("Rerun")
    if st.button("Update records"):
        st.session_state.updated = not st.session_state.updated
    if st.button("Remove selected record"):
        st.session_state.removed = True
    if st.button("New graph key"):
        st.session_state.revision += 1
st.caption(f"Render marker: {st.session_state.render_count}")

elements = {
    "nodes": [
        {
            "data": {"id": "a", "name": "Record A", "label": "RECORD"},
            "position": {"x": 350, "y": 280},
        },
        {
            "data": {
                "id": "b",
                "name": "Updated B" if st.session_state.updated else "Record B",
                "label": "RECORD",
            },
            "position": {"x": 580, "y": 400},
        },
    ],
    "edges": [{"data": {"id": "ab", "source": "a", "target": "b"}}],
}
if st.session_state.removed:
    elements["nodes"] = [elements["nodes"][1]]
    elements["edges"] = []

for index in range(2):
    graph_workbench(
        elements,
        key=f"details-{index}-{st.session_state.revision}",
        layout={"name": "preset", "fit": False},
        node_styles=[NodeStyle("RECORD", "#2A629A", "name", "description")],
        selection_mode=mode,
        return_selection=True,
        node_actions=["show_neighbors"],
        crud_actions=["read_selected"],
        analysis_actions=["degree"],
        search=True,
        show_selection_details=default_details if index == 0 else True,
        on_change=receive,
        height=620,
    )
st.metric("Selection events", st.session_state.events)
