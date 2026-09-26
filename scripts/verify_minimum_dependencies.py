"""Verify the oldest dependency versions promised by package metadata."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from st_graph_workbench import (
    dataframe_to_records,
    records_to_dataframe,
    validate_elements,
)


def main() -> None:
    """Exercise imports and pure helpers in the minimum-dependency environment."""
    elements = {
        "nodes": [{"data": {"id": "vehicle-1", "label": "VEHICLE"}}],
        "edges": [],
    }
    validate_elements(elements)

    records = dataframe_to_records(pd.DataFrame([{"id": "vehicle-1"}]))
    restored = records_to_dataframe(records)
    assert records == [{"id": "vehicle-1"}]
    assert restored.to_dict(orient="records") == records

    print(
        "Minimum dependencies verified:",
        f"pandas={pd.__version__}",
        f"streamlit={st.__version__}",
    )


if __name__ == "__main__":
    main()
