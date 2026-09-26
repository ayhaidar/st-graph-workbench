import pandas as pd

from st_graph_workbench import dataframe_to_records, records_to_dataframe

sightings = pd.DataFrame(
    [
        {
            "vehicle_id": "ABC123",
            "location": "Harbour camera 7",
            "observed_at": "2024-09-02 08:14",
            "confidence": 0.96,
        },
        {
            "vehicle_id": "12VEC",
            "location": "Depot gate",
            "observed_at": "2024-09-02 09:10",
            "confidence": None,
        },
    ]
)

records = dataframe_to_records(sightings, drop_missing=True)
round_trip = records_to_dataframe({"sightings": records})

print(records)
print(round_trip.to_dict(orient="records"))
