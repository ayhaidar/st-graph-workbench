from st_graph_workbench import dataframe_to_records, records_to_dataframe

# Named groups become a record_group column in the resulting dataframe.
sightings = {
    "sightings": [
        {"vehicle_id": "ABC123", "location": "Harbour camera 7", "time": "08:14"},
        {"vehicle_id": "ABC123", "location": "Depot gate", "time": "08:41"},
        {"vehicle_id": "12VEC", "location": "Depot gate", "time": "09:10"},
    ]
}
sightings_df = records_to_dataframe(sightings)

# Convert dataframe rows back into JSON-friendly dictionaries.
records = dataframe_to_records(sightings_df.drop(columns="record_group"))

# Decide which columns identify nodes; the helper does not infer relationships.
vehicle_df = sightings_df[["vehicle_id"]].drop_duplicates()
vehicle_df = vehicle_df.rename(columns={"vehicle_id": "id"})
vehicle_df["label"] = "VEHICLE"
vehicle_df["name"] = vehicle_df["id"]
vehicle_nodes = [{"data": row} for row in dataframe_to_records(vehicle_df)]
