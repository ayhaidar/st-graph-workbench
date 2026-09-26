import copy
import streamlit as st

from st_graph_workbench import graph_workbench


def apply_positions(elements: dict, position_records: list[dict]) -> dict:
    positions = {
        str(item["id"]): item["position"]
        for item in position_records
        if "id" in item and "position" in item
    }
    updated = copy.deepcopy(elements)
    for node in updated["nodes"]:
        node_id = str(node["data"]["id"])
        if node_id in positions:
            node["position"] = positions[node_id]
    return updated


event = graph_workbench(
    st.session_state.elements,
    layout={"name": "preset", "fit": True, "padding": 40},
    return_positions=True,
    connected_drag={"enabled": False, "depth": 1, "max_nodes": 100},
    key="persisted-layout",
)

if isinstance(event, dict) and event.get("action") == "positions":
    st.session_state.elements = apply_positions(
        st.session_state.elements,
        event.get("data", {}).get("positions", []),
    )
