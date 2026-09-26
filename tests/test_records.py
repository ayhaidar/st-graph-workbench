import datetime as dt
import decimal

import numpy as np
import pandas as pd
import pytest

from st_graph_workbench import dataframe_to_records, records_to_dataframe


def test_dataframe_to_records_returns_json_ready_records():
    table = pd.DataFrame(
        [
            {
                "Entity": "ABC123",
                "Target": "Location 1",
                "Time": pd.Timestamp("2024-09-02 08:14"),
                "Confidence": 0.93,
                "Reviewed": None,
                "Tags": ("vehicle", "location"),
            }
        ]
    )

    assert dataframe_to_records(table) == [
        {
            "Entity": "ABC123",
            "Target": "Location 1",
            "Time": "2024-09-02 08:14:00",
            "Confidence": 0.93,
            "Reviewed": None,
            "Tags": ["vehicle", "location"],
        }
    ]


def test_dataframe_to_records_can_drop_missing_values():
    table = pd.DataFrame(
        [
            {
                "Entity": "ABC123",
                "Target": None,
                "Time": pd.NaT,
                "First Seen": dt.date(2024, 9, 2),
            }
        ]
    )

    assert dataframe_to_records(table, drop_missing=True) == [
        {
            "Entity": "ABC123",
            "First Seen": "2024-09-02",
        }
    ]


def test_dataframe_to_records_converts_nested_json_values_deterministically():
    class EvidenceScore:
        def __str__(self):
            return "manual-review"

    table = pd.DataFrame(
        [
            {
                "Entity": "ABC123",
                "Embedding": np.array([1, 2, 3]),
                "Confidence": decimal.Decimal("0.95"),
                "Visit Count": decimal.Decimal("2"),
                "Tags": {"vehicle", "camera"},
                "Review": EvidenceScore(),
            }
        ]
    )

    assert dataframe_to_records(table) == [
        {
            "Entity": "ABC123",
            "Embedding": [1, 2, 3],
            "Confidence": 0.95,
            "Visit Count": 2,
            "Tags": ["camera", "vehicle"],
            "Review": "manual-review",
        }
    ]


def test_records_to_dataframe_accepts_grouped_record_dictionary():
    table = records_to_dataframe(
        {
            "vehicles": [
                {"id": "ABC123", "label": "MAIN_VEHICLE"},
                {"id": "BETA", "label": "VEHICLE", "record_group": "raw"},
            ],
            "locations": [{"id": "location_1", "label": "PLACE"}],
        }
    )

    assert table.to_dict("records") == [
        {"record_group": "vehicles", "id": "ABC123", "label": "MAIN_VEHICLE"},
        {"record_group": "vehicles", "id": "BETA", "label": "VEHICLE"},
        {"record_group": "locations", "id": "location_1", "label": "PLACE"},
    ]


def test_records_to_dataframe_flattens_graph_elements():
    elements = {
        "nodes": [
            {
                "data": {"id": "ABC123", "label": "MAIN_VEHICLE", "name": "ABC123"},
                "position": {"x": 10, "y": 20},
            }
        ],
        "edges": [
            {
                "data": {
                    "id": "ABC123-location_1",
                    "label": "Seen at",
                    "source": "ABC123",
                    "target": "location_1",
                }
            }
        ],
    }

    table = records_to_dataframe(elements)
    rows = table.to_dict("records")

    assert rows[0]["record_group"] == "node"
    assert rows[0]["id"] == "ABC123"
    assert rows[0]["position_x"] == 10
    assert rows[0]["position_y"] == 20
    assert rows[1]["record_group"] == "edge"
    assert rows[1]["id"] == "ABC123-location_1"
    assert rows[1]["source"] == "ABC123"
    assert rows[1]["target"] == "location_1"


def test_records_to_dataframe_can_keep_graph_data_nested():
    elements = {
        "nodes": [
            {
                "data": {"id": "ABC123", "label": "MAIN_VEHICLE", "name": "ABC123"},
                "position": {"x": 10, "y": 20},
            }
        ],
        "edges": [],
    }

    table = records_to_dataframe(
        elements,
        group_key="element_type",
        flatten_data=False,
    )
    rows = table.to_dict("records")

    assert rows == [
        {
            "element_type": "node",
            "data": {"id": "ABC123", "label": "MAIN_VEHICLE", "name": "ABC123"},
            "position": {"x": 10, "y": 20},
        }
    ]


def test_records_to_dataframe_flattens_returned_event_elements():
    selected_elements = [
        {
            "id": "ABC123",
            "group": "nodes",
            "data": {
                "id": "ABC123",
                "label": "MAIN_VEHICLE",
                "name": "ABC123",
                "risk": 8,
            },
        },
        {
            "id": "ABC123-location_1",
            "group": "edges",
            "data": {
                "id": "ABC123-location_1",
                "label": "SEEN_AT",
                "source": "ABC123",
                "target": "location_1",
            },
        },
    ]

    rows = records_to_dataframe(selected_elements).to_dict("records")

    assert rows[0]["record_group"] == "node"
    assert rows[0]["name"] == "ABC123"
    assert rows[0]["risk"] == 8
    assert rows[1]["record_group"] == "edge"
    assert rows[1]["source"] == "ABC123"
    assert rows[1]["target"] == "location_1"
    assert "data" not in rows[0]


def test_records_to_dataframe_can_keep_returned_event_data_nested():
    selected_elements = [
        {
            "id": "ABC123",
            "group": "node",
            "data": {"id": "ABC123", "label": "MAIN_VEHICLE", "risk": 8},
        }
    ]

    rows = records_to_dataframe(
        selected_elements,
        group_key="element_type",
        flatten_data=False,
    ).to_dict("records")

    assert rows == [
        {
            "element_type": "node",
            "data": {"id": "ABC123", "label": "MAIN_VEHICLE", "risk": 8},
        }
    ]


def test_records_to_dataframe_supports_custom_group_key():
    table = records_to_dataframe(
        {"sightings": [{"id": "ABC123"}]},
        group_key="source_table",
    )

    assert table.to_dict("records") == [{"source_table": "sightings", "id": "ABC123"}]


def test_records_to_dataframe_rejects_non_record_sequences():
    with pytest.raises(TypeError, match="Record 1"):
        records_to_dataframe([{"id": "ABC123"}, "not-a-record"])
