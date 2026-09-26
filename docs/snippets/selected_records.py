import json
from pathlib import Path

import streamlit as st

from st_graph_workbench import graph_workbench, records_to_dataframe

elements = json.loads(
    Path("examples/data/intelligence_case.json").read_text(encoding="utf-8")
)
event = graph_workbench(
    elements,
    selection_mode="box",
    return_selection=True,
    # Keep selection events and the Python table without an automatic inspector.
    show_selection_details=False,
    search=True,
    key="investigation-selection",
)

event_data = event.get("data", {}) if isinstance(event, dict) else {}
returned_records = (
    event_data.get("selected_elements") or event_data.get("matched_elements") or []
)

st.dataframe(records_to_dataframe(returned_records), hide_index=True)
