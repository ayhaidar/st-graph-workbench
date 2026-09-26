import streamlit as st

from st_graph_workbench import records_to_dataframe

# Use the event from the styled graph and the source table above.
selection = event["data"] if event and event["action"] == "selection" else {}
selected_ids = selection.get("selected_node_ids", [])
selected_rows = records_to_dataframe(selection.get("selected_elements", []))

# Join graph IDs back to the source evidence, without changing that evidence.
matching_sightings = sightings_df[sightings_df["vehicle_id"].isin(selected_ids)]
st.metric("Matching sightings", len(matching_sightings))
st.dataframe(matching_sightings, hide_index=True)
