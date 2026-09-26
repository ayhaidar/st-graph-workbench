from __future__ import annotations

import math
from collections.abc import Iterable, Mapping

from st_graph_workbench.component.types import ElementIdInput


def normalize_id(value: object, *, option_name: str) -> str:
    """Normalize one supported scalar identifier to a string."""
    if value is None or value == "":
        raise TypeError(f"`{option_name}` values cannot be empty.")
    if isinstance(value, str | bool | int):
        return str(value)
    if isinstance(value, float) and math.isfinite(value):
        return str(value)
    raise TypeError(
        f"`{option_name}` values must be non-empty string, finite number, "
        f"or boolean IDs, not `{type(value).__name__}`."
    )


def normalize_id_list(values: ElementIdInput, *, option_name: str) -> list[str]:
    """Normalize one scalar ID or an iterable of IDs to string IDs."""
    if values is None:
        return []
    if isinstance(values, str | bool | int | float):
        return [normalize_id(values, option_name=option_name)]
    if isinstance(values, Mapping):
        raise TypeError(
            f"`{option_name}` must be one scalar ID or an iterable of ID values, "
            "not a dict."
        )
    if not isinstance(values, Iterable):
        raise TypeError(
            f"`{option_name}` must be one scalar ID or an iterable of ID values, "
            f"not `{type(values).__name__}`."
        )
    return [normalize_id(value, option_name=option_name) for value in values]


def normalize_id_set(values: ElementIdInput, *, option_name: str) -> set[str]:
    """Normalize one scalar ID or an iterable of IDs to a set of string IDs."""
    return set(normalize_id_list(values, option_name=option_name))
