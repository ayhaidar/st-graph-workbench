"""Shared record and filter validation for expansion controllers and providers."""

from copy import deepcopy
from datetime import datetime, timezone
import json
import math
from typing import Any

from ._ids import normalize_id
from .types import Elements
from .validation import validate_elements


def positive_limit(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer.")
    return value


def normalize_elements(elements: Elements, *, strict: bool = True) -> Elements:
    validate_elements(elements, strict=strict)
    elements = deepcopy(elements)
    for group in ("nodes", "edges"):
        elements.setdefault(group, [])
        for record in elements[group]:
            data = record["data"]
            fields = (
                ("id", "source", "target") if group == "edges" else ("id", "parent")
            )
            for name in fields:
                if name == "parent" and data.get(name) in (None, ""):
                    data.pop(name, None)
                elif name in data:
                    data[name] = normalize_id(data[name], option_name=name)
    try:
        json.dumps(elements, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "Expansion records must contain JSON-compatible finite values."
        ) from error
    for node in elements["nodes"]:
        if "position" not in node:
            continue
        position = node["position"]
        if not isinstance(position, dict) or any(
            isinstance(position.get(axis), bool)
            or not isinstance(position.get(axis), (int, float))
            or not math.isfinite(float(position[axis]))
            for axis in ("x", "y")
        ):
            raise ValueError(
                f"Node {node['data']['id']} position requires finite numeric x and y."
            )
    return elements


def parse_instant(value: Any) -> datetime:
    instant = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return instant.replace(tzinfo=timezone.utc) if instant.tzinfo is None else instant


def normalize_query(value: dict[str, Any] | None) -> dict[str, Any]:
    if value is not None and not isinstance(value, dict):
        raise ValueError("Expansion filters must be a dictionary.")
    result = deepcopy(value or {})
    unknown = set(result) - {
        "direction",
        "relationships",
        "attributes",
        "time_field",
        "time_from",
        "time_to",
    }
    if unknown:
        raise ValueError(f"Unknown expansion filters: {sorted(unknown)}")
    result.setdefault("direction", "both")
    if result["direction"] not in ("both", "incoming", "outgoing"):
        raise ValueError("direction must be both, incoming or outgoing.")
    relationships = result.get("relationships", [])
    if not isinstance(relationships, list) or any(
        not isinstance(x, str) for x in relationships
    ):
        raise ValueError("relationships must be a list of strings.")
    result["relationships"] = sorted(set(relationships))
    result.setdefault("attributes", {})
    result.setdefault("time_field", "observed_at")
    if not isinstance(result["attributes"], dict):
        raise ValueError("attributes must be a dictionary of exact-match properties.")
    if not isinstance(result["time_field"], str) or not result["time_field"].strip():
        raise ValueError("time_field must be a nonempty property name.")
    bounds = {}
    for name in ("time_from", "time_to"):
        if result.get(name) in (None, ""):
            continue
        try:
            if not isinstance(result[name], str):
                raise ValueError
            bounds[name] = parse_instant(result[name])
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"{name} must be an ISO-8601 date or timestamp."
            ) from error
    if len(bounds) == 2 and bounds["time_from"] > bounds["time_to"]:
        raise ValueError("time_from must not be later than time_to.")
    json.dumps(result, allow_nan=False)
    return result
