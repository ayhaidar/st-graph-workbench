import streamlit as st

from st_graph_workbench import graph_workbench, records_to_dataframe

# Each node needs a unique ID; edges refer to those IDs.
elements = {
    "nodes": [
        {"data": {"id": "ABC123", "label": "VEHICLE", "name": "ABC123"}},
        {"data": {"id": "camera-7", "label": "LOCATION", "name": "Harbour camera 7"}},
    ],
    "edges": [
        {
            "data": {
                "id": "sighting-1",
                "source": "ABC123",
                "target": "camera-7",
                "label": "SEEN_AT",
                "observed_at": "2024-09-02 08:14",
            }
        }
    ],
}

# Inspect the source records before exploring the graph.
st.dataframe(records_to_dataframe(elements), hide_index=True)
event = graph_workbench(
    elements,
    layout="cose",
    selection_mode="multiple",
    return_selection=True,
    search=True,
    key="readme_quick_start_output",
    height=420,
)
