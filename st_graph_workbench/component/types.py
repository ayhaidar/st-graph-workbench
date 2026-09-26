"""Public type aliases for graph data, commands, layouts, and events."""

from collections.abc import Iterable
from typing import Any, Literal, TypeAlias, TypedDict


Element: TypeAlias = dict[str, Any]
"""One Cytoscape node or edge dictionary."""

Elements: TypeAlias = dict[str, Any]
"""A graph dictionary containing ``nodes`` and ``edges`` lists."""

Record: TypeAlias = dict[str, Any]
"""One table-like or JSON-ready record dictionary."""

ElementId: TypeAlias = str | int | float | bool
"""One node, edge, command, source, target, or parent identifier."""

ElementIdInput: TypeAlias = ElementId | Iterable[ElementId] | None
"""One identifier, an iterable of identifiers, or no identifiers."""

Layout: TypeAlias = str | dict[str, Any]
"""A named layout or a Cytoscape layout options dictionary."""

GraphCommand: TypeAlias = dict[str, Any]
"""One incremental command sent to the browser graph."""

GraphEvent: TypeAlias = dict[str, Any]
"""An event dictionary returned from the browser component."""


class ProgressiveLoadConfig(TypedDict, total=False):
    """Configuration for requesting incremental graph batches.

    ``page_size`` is the requested number of domain records in the next batch.
    ``loaded_count`` and ``total_count`` drive the progress shown in the graph.
    ``cursor`` is an opaque JSON scalar returned unchanged in the next
    ``load_more`` event. Set ``has_more`` to false when no further batch exists.
    ``acknowledged_request_id`` echoes the completed event's ``request_id``,
    including after a handled fetch failure, to enable another request without
    changing the cursor or counts. Omit it for legacy progress-driven completion.
    """

    page_size: int
    loaded_count: int
    total_count: int | None
    has_more: bool
    cursor: str | int | float | bool | None
    acknowledged_request_id: str | None


class ConnectedDragConfig(TypedDict, total=False):
    """Configuration for rigidly dragging visible connected nodes.

    ``enabled`` and ``depth`` are initial browser preferences. ``max_depth``
    bounds the toolbar choices to one, two, or three visible hops, while
    ``max_nodes`` limits automatic followers for one gesture. Explicitly
    selected and compound-descendant nodes retain Cytoscape's native behavior.
    """

    enabled: bool
    depth: Literal[1, 2, 3]
    max_depth: Literal[1, 2, 3]
    max_nodes: int


class ToolbarConfig(TypedDict, total=False):
    """Configuration for the responsive controls above the graph.

    ``mode`` chooses adaptive, expanded, compact, or initially minimized
    presentation. ``position`` currently supports the top of the graph.
    ``collapsible`` lets the reader minimize and restore the controls, while
    ``sticky`` reserves their measured height so they never cover the canvas.
    """

    mode: Literal["adaptive", "expanded", "compact", "minimized"]
    position: Literal["top"]
    collapsible: bool
    sticky: bool


ElementInput: TypeAlias = Element | Iterable[Element] | None
"""One element, an iterable of elements, or no elements."""
