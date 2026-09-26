"""Custom Cytoscape event listener definitions."""

RESERVED_NAMES = frozenset(
    {
        "_graph_workbench_sync_request",
        "analysis",
        "crud",
        "edit",
        "expand",
        "expansion",
        "layout_error",
        "load_more",
        "positions",
        "remove",
        "search",
        "selection",
        "viewport",
        "visibility",
    }
)


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"`{field}` must be a non-empty string.")
    return value


class Event:
    """Define a custom Cytoscape event listener returned to Python."""

    def __init__(
        self,
        name: str,
        event_type: str,
        selector: str,
    ) -> None:
        """Create a listener definition.

        Parameters
        ----------
        name
            Application-specific action name included in the returned event.
        event_type
            Space-separated Cytoscape event names, for example ``"click tap"``.
        selector
            Cytoscape selector that scopes the listener, for example ``"node"``.

        Examples
        --------
        >>> event = Event("clicked_node", "click tap", "node")
        >>> event.dump()["name"]
        'clicked_node'
        """
        self.name = _required_text(name, "name")
        self.event_type = _required_text(event_type, "event_type")
        self.selector = _required_text(selector, "selector")
        if self.name in RESERVED_NAMES:
            raise ValueError(
                f"`{self.name}` is reserved by st-graph-workbench. "
                "Choose an application-specific event name."
            )

    def dump(self) -> dict[str, str]:
        """Return the listener as a JSON-ready component dictionary."""
        return {
            "name": self.name,
            "event_type": self.event_type,
            "selector": self.selector,
        }
