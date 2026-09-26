import streamlit as st

from st_graph_workbench import EdgeStyle, NodeStyle, graph_workbench

st.set_page_config(layout="wide")

elements = {
    "nodes": [
        {"data": {"id": "ABC123", "label": "VEHICLE", "name": "ABC123"}},
        {
            "data": {
                "id": "camera-7",
                "label": "LOCATION",
                "name": "Harbour camera 7",
            }
        },
        {
            "data": {
                "id": "time-0814",
                "label": "TIME",
                "name": "02 Sep 2024 08:14",
            }
        },
    ],
    "edges": [
        {
            "data": {
                "id": "ABC123-camera-7",
                "label": "SEEN_AT",
                "source": "ABC123",
                "target": "camera-7",
            }
        },
        {
            "data": {
                "id": "camera-7-time-0814",
                "label": "OBSERVED_DURING",
                "source": "camera-7",
                "target": "time-0814",
            }
        },
    ],
}

event = graph_workbench(
    elements,
    layout="cose",
    node_styles=[
        NodeStyle("VEHICLE", "#2A629A", "name", "directions_car"),
        NodeStyle("LOCATION", "#2D936C", "name", "place"),
        NodeStyle("TIME", "#8A5A44", "name", "schedule"),
    ],
    edge_styles=[
        EdgeStyle("SEEN_AT", "#2D936C", "label", directed=True),
        EdgeStyle("OBSERVED_DURING", "#8A5A44", "label", directed=True),
    ],
    selection_mode="multiple",
    return_selection=True,
    search=True,
    height=560,
    key="quickstart-graph",
)

st.subheader("Returned component event")
st.caption(
    "The browser returns this dictionary after a selection or search interaction."
)
st.json(event or {})
