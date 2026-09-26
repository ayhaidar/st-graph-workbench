import pytest

from st_graph_workbench.component.layouts import (
    LAYOUTS,
    resolve_layout,
    validate_layout,
)


def test_named_preset_layout_is_supported() -> None:
    assert "preset" in LAYOUTS
    assert resolve_layout("preset")["name"] == "preset"


def test_resolved_named_layout_is_an_independent_copy() -> None:
    first = resolve_layout("circle")
    first["padding"] = 999

    assert resolve_layout("circle")["padding"] != 999


def test_layout_dictionary_keeps_custom_supported_options() -> None:
    layout = {"name": "dagre", "rankDir": "LR", "fit": False}

    assert resolve_layout(layout) == layout
    assert resolve_layout(layout) is not layout


@pytest.mark.parametrize(
    "layout, message",
    [
        ({"fit": True}, "non-empty string `name`"),
        ({"name": "unknown"}, "Unknown layout"),
        ("unknown", "Unknown layout"),
        ([], "supported layout name"),
    ],
)
def test_layout_validation_rejects_browser_errors_early(layout, message) -> None:
    with pytest.raises(ValueError, match=message):
        validate_layout(layout)
