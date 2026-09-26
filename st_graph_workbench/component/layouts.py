"""Supported Cytoscape layouts and Python-side layout validation."""

import copy
from typing import Any

from st_graph_workbench.component.types import Layout

DEFAULT_ATTRS = {
    "padding": 20,
    "animationDuration": 500,
    "fit": True,
    "animate": True,
    "nodeDimensionsIncludeLabels": True,
}

LAYOUTS = {
    "preset": {
        **DEFAULT_ATTRS,
        "name": "preset",
        "animate": False,
    },
    "cose": {
        **DEFAULT_ATTRS,
        "name": "cose",
        "nodeRepulsion": 2024,
        "animate": "end",
    },
    "random": {
        **DEFAULT_ATTRS,
        "name": "random",
    },
    "grid": {
        **DEFAULT_ATTRS,
        "name": "grid",
    },
    "circle": {
        **DEFAULT_ATTRS,
        "name": "circle",
        "nodeDimensionsIncludeLabels": False,
    },
    "concentric": {
        **DEFAULT_ATTRS,
        "name": "concentric",
        "minNodeSpacing": 40,
        "nodeDimensionsIncludeLabels": False,
    },
    "breadthfirst": {
        **DEFAULT_ATTRS,
        "name": "breadthfirst",
        "directed": True,
    },
    "fcose": {
        **DEFAULT_ATTRS,
        "name": "fcose",
    },
    "cola": {
        **DEFAULT_ATTRS,
        "name": "cola",
    },
    "dagre": {
        **DEFAULT_ATTRS,
        "name": "dagre",
    },
}


def validate_layout(
    layout: Any,
    *,
    description: str = "`layout`",
    allow_none: bool = False,
) -> None:
    """Validate a named layout or Cytoscape layout options dictionary."""
    if layout is None and allow_none:
        return

    if isinstance(layout, str):
        name = layout
    elif isinstance(layout, dict):
        candidate_name = layout.get("name")
        if not isinstance(candidate_name, str) or not candidate_name:
            raise ValueError(
                f"{description} dictionaries must include a non-empty string `name`."
            )
        name = candidate_name
    else:
        raise ValueError(
            f"{description} must be a supported layout name or an options dictionary."
        )

    if name not in LAYOUTS:
        raise ValueError(f"Unknown layout `{name}`. Expected one of {sorted(LAYOUTS)}.")


def resolve_layout(layout: Layout) -> dict[str, Any]:
    """Return an independent Cytoscape options dictionary for a layout input."""
    validate_layout(layout)
    if isinstance(layout, str):
        return copy.deepcopy(LAYOUTS[layout])
    return copy.deepcopy(layout)
