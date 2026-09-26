import streamlit as st

from st_graph_workbench import (
    apply_graph_command,
    graph_workbench,
    upsert_elements_command,
)

if "elements" not in st.session_state:
    st.session_state.elements = {"nodes": [], "edges": []}
if "commands" not in st.session_state:
    st.session_state.commands = []

if st.button("Load sighting"):
    command = upsert_elements_command(
        "load-sighting-1",
        nodes=[
            {"data": {"id": "ABC123", "label": "VEHICLE", "name": "ABC123"}},
            {"data": {"id": "gate-4", "label": "LOCATION", "name": "Gate 4"}},
        ],
        edges={
            "data": {
                "id": "ABC123-gate-4",
                "label": "SEEN_AT",
                "source": "ABC123",
                "target": "gate-4",
            }
        },
    )
    st.session_state.elements = apply_graph_command(st.session_state.elements, command)
    st.session_state.commands = [command]

graph_workbench(
    st.session_state.elements,
    graph_commands=st.session_state.commands,
    elements_sync="initial",
    key="command-driven-graph",
)
