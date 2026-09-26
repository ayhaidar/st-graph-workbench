import pytest

from st_graph_workbench import Event
from st_graph_workbench.component.events import RESERVED_NAMES


@pytest.mark.parametrize("name", sorted(RESERVED_NAMES))
def test_custom_events_reject_built_in_action_names(name: str) -> None:
    with pytest.raises(ValueError, match="reserved by st-graph-workbench"):
        Event(name, "click", "node")


@pytest.mark.parametrize(
    "kwargs, field",
    [
        ({"name": "", "event_type": "click", "selector": "node"}, "name"),
        (
            {"name": "node_click", "event_type": "  ", "selector": "node"},
            "event_type",
        ),
        (
            {"name": "node_click", "event_type": "click", "selector": ""},
            "selector",
        ),
    ],
)
def test_custom_events_require_non_empty_text(kwargs, field: str) -> None:
    with pytest.raises(ValueError, match=field):
        Event(**kwargs)


def test_custom_event_dump_is_json_ready() -> None:
    event = Event("case_node_click", "click tap", "node[label = 'CASE']")

    assert event.dump() == {
        "name": "case_node_click",
        "event_type": "click tap",
        "selector": "node[label = 'CASE']",
    }
