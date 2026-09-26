import streamlit as st

from st_graph_workbench import graph_workbench, upsert_elements

RELATED = {
    "ABC123": {
        "nodes": [
            {
                "data": {
                    "id": "person-maya",
                    "label": "PERSON",
                    "name": "Maya Reed",
                }
            }
        ],
        "edges": [
            {
                "data": {
                    "id": "ABC123-person-maya",
                    "label": "REGISTERED_TO",
                    "source": "ABC123",
                    "target": "person-maya",
                }
            }
        ],
    }
}

if "graph" not in st.session_state:
    st.session_state.graph = {
        "nodes": [
            {
                "data": {
                    "id": "ABC123",
                    "label": "VEHICLE",
                    "name": "ABC123",
                    "expansion": {
                        "state": "collapsed",
                        "next_count": 1,
                        "total_count": 2,
                        "depth": 1,
                    },
                }
            }
        ],
        "edges": [],
    }


def handle_event() -> None:
    event = st.session_state.get("expansion-graph")
    if not isinstance(event, dict) or event.get("action") != "expand":
        return
    for node_id in event.get("data", {}).get("node_ids", []):
        related = RELATED.get(node_id)
        if related:
            st.session_state.graph = upsert_elements(
                st.session_state.graph,
                nodes=related["nodes"],
                edges=related["edges"],
            )


graph_workbench(
    st.session_state.graph,
    node_actions=["expand"],
    on_change=handle_event,
    key="expansion-graph",
)
