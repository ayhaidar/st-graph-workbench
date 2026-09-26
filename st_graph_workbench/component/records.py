from __future__ import annotations

import datetime as dt
import decimal
import importlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from st_graph_workbench.component.types import Record


def _optional_pandas() -> Any | None:
    try:
        return importlib.import_module("pandas")
    except ImportError:
        return None


def _require_pandas() -> Any:
    pandas = _optional_pandas()
    if pandas is None:
        raise ImportError(
            "`records_to_dataframe(...)` requires pandas. Install pandas or use "
            "Streamlit's normal application environment."
        )
    return pandas


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    )


def _is_missing_scalar(value: Any, pandas: Any | None) -> bool:
    if value is None:
        return True

    if pandas is not None:
        try:
            missing = pandas.isna(value)
        except (TypeError, ValueError):
            missing = False

        try:
            return bool(missing)
        except (TypeError, ValueError):
            return False

    try:
        return bool(value != value)
    except (TypeError, ValueError):
        return False


def _json_ready_value(value: Any, pandas: Any | None) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _json_ready_value(item, pandas) for key, item in value.items()
        }

    if isinstance(value, list):
        return [_json_ready_value(item, pandas) for item in value]

    if isinstance(value, tuple):
        return [_json_ready_value(item, pandas) for item in value]

    if isinstance(value, set):
        return [_json_ready_value(item, pandas) for item in sorted(value, key=repr)]

    if _is_missing_scalar(value, pandas):
        return None

    if isinstance(value, decimal.Decimal):
        if value.is_nan() or value.is_infinite():
            return None
        if value == value.to_integral_value():
            return int(value)
        return float(value)

    if isinstance(value, dt.datetime):
        return value.isoformat(sep=" ")

    if isinstance(value, dt.date | dt.time):
        return value.isoformat()

    if isinstance(value, dt.timedelta):
        return str(value)

    item = getattr(value, "item", None)
    if callable(item):
        try:
            scalar = item()
        except (TypeError, ValueError):
            scalar = value
        if scalar is not value:
            return _json_ready_value(scalar, pandas)

    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        try:
            converted = tolist()
        except (TypeError, ValueError):
            converted = value
        if converted is not value:
            return _json_ready_value(converted, pandas)

    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat) and value.__class__.__module__.startswith("pandas"):
        return isoformat()

    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError):
        return str(value)

    return value


def _clean_record(
    record: Mapping[str, Any],
    *,
    drop_missing: bool,
    pandas: Any | None,
) -> Record:
    cleaned = {
        str(key): _json_ready_value(value, pandas) for key, value in record.items()
    }
    if drop_missing:
        return {key: value for key, value in cleaned.items() if value is not None}
    return cleaned


def dataframe_to_records(dataframe: Any, *, drop_missing: bool = False) -> list[Record]:
    """Convert a dataframe-like object to JSON-friendly record dictionaries.

    Supports pandas dataframes, Polars dataframes, and Arrow-like tables that
    expose one of the common record-export methods. Scalar missing values become
    ``None`` so records can be passed safely into ``graph_workbench(...)``.
    Nested tuples, sets, array-like values, datetimes, and decimals are
    normalized into deterministic JSON-friendly values.
    """

    if hasattr(dataframe, "to_dicts"):
        raw_records = dataframe.to_dicts()
    elif hasattr(dataframe, "to_pylist"):
        raw_records = dataframe.to_pylist()
    elif hasattr(dataframe, "to_dict"):
        try:
            raw_records = dataframe.to_dict(orient="records")
        except TypeError:
            raw_records = dataframe.to_dict("records")
    else:
        raise TypeError(
            "`dataframe` must provide `to_dicts()`, `to_pylist()`, or "
            "`to_dict(orient='records')`."
        )

    if not _is_sequence(raw_records):
        raise TypeError("Dataframe record export must return a sequence of records.")

    pandas = _optional_pandas()
    records: list[Record] = []
    for index, record in enumerate(raw_records):
        if not isinstance(record, Mapping):
            raise TypeError(f"Record {index} is not a dictionary-like object.")
        records.append(_clean_record(record, drop_missing=drop_missing, pandas=pandas))
    return records


def _mapping_to_row(record: Mapping[str, Any]) -> Record:
    return {str(key): value for key, value in record.items()}


def _graph_group_value(group: str) -> str:
    if group == "nodes":
        return "node"
    if group == "edges":
        return "edge"
    return group


def _graph_element_to_row(
    element: Mapping[str, Any],
    *,
    group: str,
    group_key: str,
    flatten_data: bool,
) -> Record:
    row: Record = {group_key: _graph_group_value(group)}
    data = element.get("data")

    if flatten_data and isinstance(data, Mapping):
        row.update(_mapping_to_row(data))
    elif data is not None:
        row["data"] = data

    for key, value in element.items():
        key_text = str(key)
        if key_text == "data":
            continue
        if flatten_data and key_text == "position" and isinstance(value, Mapping):
            for position_key, position_value in value.items():
                row[f"position_{position_key}"] = position_value
            continue
        row[key_text] = value

    row[group_key] = _graph_group_value(group)
    return row


def _records_from_graph_elements(
    records: Mapping[str, Any],
    *,
    group_key: str,
    flatten_data: bool,
) -> list[Record]:
    rows: list[Record] = []
    for group in ("nodes", "edges"):
        values = records.get(group, [])
        if not _is_sequence(values):
            raise TypeError(f"`{group}` must be a sequence of element dictionaries.")
        for index, element in enumerate(values):
            if not isinstance(element, Mapping):
                raise TypeError(f"`{group}` item {index} is not a dictionary.")
            rows.append(
                _graph_element_to_row(
                    element,
                    group=group,
                    group_key=group_key,
                    flatten_data=flatten_data,
                )
            )
    return rows


def _records_from_grouped_mapping(
    records: Mapping[str, Any],
    *,
    group_key: str,
) -> list[Record]:
    rows: list[Record] = []
    for group, values in records.items():
        group_value = str(group)
        if _is_sequence(values):
            for index, value in enumerate(values):
                if isinstance(value, Mapping):
                    row = _mapping_to_row(value)
                    row[group_key] = group_value
                    rows.append(row)
                    continue
                rows.append(
                    {group_key: group_value, "record_index": index, "value": value}
                )
            continue
        if isinstance(values, Mapping):
            row = _mapping_to_row(values)
            row[group_key] = group_value
            rows.append(row)
            continue
        rows.append({group_key: group_value, "value": values})
    return rows


def _event_element_group(record: Mapping[str, Any]) -> str | None:
    group = record.get("group")
    data = record.get("data")
    if not isinstance(group, str) or not isinstance(data, Mapping):
        return None
    normalized_group = group.lower()
    if normalized_group in {"node", "nodes"}:
        return "nodes"
    if normalized_group in {"edge", "edges"}:
        return "edges"
    return None


def _event_element_to_row(
    record: Mapping[str, Any],
    *,
    group: str,
    group_key: str,
    flatten_data: bool,
) -> Record:
    data = _mapping_to_row(record["data"])
    if "id" not in data and record.get("id") is not None:
        data["id"] = record["id"]
    element = {
        "data": data,
        **{
            str(key): value
            for key, value in record.items()
            if key not in {"data", "group", "id"}
        },
    }
    return _graph_element_to_row(
        element,
        group=group,
        group_key=group_key,
        flatten_data=flatten_data,
    )


def _records_from_sequence(
    records: Sequence[Any],
    *,
    group_key: str,
    flatten_data: bool,
) -> list[Record]:
    rows: list[Record] = []
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise TypeError(f"Record {index} is not a dictionary-like object.")
        event_group = _event_element_group(record)
        if event_group is not None:
            rows.append(
                _event_element_to_row(
                    record,
                    group=event_group,
                    group_key=group_key,
                    flatten_data=flatten_data,
                )
            )
            continue
        rows.append(_mapping_to_row(record))
    return rows


def records_to_dataframe(
    records: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    group_key: str = "record_group",
    flatten_data: bool = True,
) -> Any:
    """Convert record dictionaries to a pandas dataframe.

    ``records`` may be a normal list of dictionaries, a dictionary of named
    record groups such as ``{"sightings": [...]}``, a graph element dictionary
    such as ``{"nodes": [...], "edges": [...]}``, or the element records in a
    selection/search event. Graph and event element ``data`` fields are
    flattened into columns by default so returned records are immediately
    useful in Streamlit and notebooks.
    """

    pandas = _require_pandas()

    if isinstance(records, Mapping):
        if "nodes" in records or "edges" in records:
            rows = _records_from_graph_elements(
                records,
                group_key=group_key,
                flatten_data=flatten_data,
            )
        else:
            rows = _records_from_grouped_mapping(records, group_key=group_key)
    elif _is_sequence(records):
        rows = _records_from_sequence(
            records,
            group_key=group_key,
            flatten_data=flatten_data,
        )
    else:
        raise TypeError(
            "`records` must be a sequence of dictionaries or a dictionary of "
            "record groups."
        )

    return pandas.DataFrame(rows)
