import streamlit as st

from st_graph_workbench import graph_workbench

left_elements = {
    "nodes": [{"data": {"id": "ABC123", "label": "VEHICLE"}}],
    "edges": [],
}
right_elements = {
    "nodes": [{"data": {"id": "camera-7", "label": "LOCATION"}}],
    "edges": [],
}

left, right = st.columns(2)

with left:
    left_event = graph_workbench(
        left_elements,
        selection_mode="multiple",
        return_selection=True,
        key="case-left",
    )

with right:
    right_event = graph_workbench(
        right_elements,
        selection_mode="single",
        return_selection=True,
        key="case-right",
    )

st.write({"left": left_event, "right": right_event})
