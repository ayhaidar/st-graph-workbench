import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def exported_names() -> set[str]:
    module = ast.parse((ROOT / "st_graph_workbench" / "__init__.py").read_text())
    for node in module.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            return set(ast.literal_eval(node.value))
    raise AssertionError("__all__ was not found in st_graph_workbench.__init__")


def test_mkdocs_api_reference_lists_all_root_exports() -> None:
    reference = (DOCS / "reference" / "index.md").read_text(encoding="utf-8")
    missing = sorted(
        name for name in exported_names() if f"- `{name}`:" not in reference
    )

    assert missing == []


def test_docs_explain_crud_event_context_fields() -> None:
    crud_guide = (DOCS / "guides" / "crud.md").read_text(encoding="utf-8")
    crud_demo = (ROOT / "examples" / "docs" / "interactive_crud.py").read_text(
        encoding="utf-8"
    )

    for field in (
        "operation",
        "selected_node_ids",
        "selected_edge_ids",
        "connected_node_ids",
        "connected_edge_ids",
        "last_selected",
        "selected_elements",
        "connected_elements",
        "suggested_position",
    ):
        assert field in crud_guide
        assert field in crud_demo


def test_docs_explain_record_helper_options() -> None:
    record_guide = (DOCS / "concepts" / "records.md").read_text(encoding="utf-8")
    data_helpers_demo = (
        ROOT / "examples" / "demos" / "data_helpers_commands.py"
    ).read_text(encoding="utf-8")

    for term in ("drop_missing=True", "flatten_data=False", "group_key"):
        assert term in record_guide
        assert term in data_helpers_demo


def test_docs_explain_height_updates_without_remount() -> None:
    mental_model = (DOCS / "getting-started" / "mental-model.md").read_text(
        encoding="utf-8"
    )
    component = (ROOT / "st_graph_workbench" / "component" / "component.py").read_text(
        encoding="utf-8"
    )
    architecture = (DOCS / "advanced" / "architecture.md").read_text(encoding="utf-8")

    assert "Height and zoom-bound changes update the live" in mental_model
    assert "resize without forcing a remount" in component
    assert "height updates\ndo not require remounting" in architecture


def test_docs_explain_event_listeners_update_without_remount() -> None:
    component = (ROOT / "st_graph_workbench" / "component" / "component.py").read_text(
        encoding="utf-8"
    )
    event_guide = (DOCS / "guides" / "events-exports.md").read_text(encoding="utf-8")
    event_demo = (ROOT / "examples" / "demos" / "event_listeners.py").read_text(
        encoding="utf-8"
    )

    assert "changing `events` does not require a new component key" in component
    assert "without requiring a new key" in event_guide
    assert 'key="event-listeners"' in event_demo


def test_docs_explain_delete_command_incident_edge_validation() -> None:
    crud_guide = (DOCS / "guides" / "crud.md").read_text(encoding="utf-8")
    data_helpers_demo = (
        ROOT / "examples" / "demos" / "data_helpers_commands.py"
    ).read_text(encoding="utf-8")

    for source in (crud_guide, data_helpers_demo):
        assert "remove_incident_edges=False" in source
        assert "dangling edge references" in source


def test_docs_explain_delete_id_inputs_are_scalar_values() -> None:
    element_guide = (DOCS / "concepts" / "elements.md").read_text(encoding="utf-8")
    crud_docs = (ROOT / "examples" / "docs" / "interactive_crud.py").read_text(
        encoding="utf-8"
    )

    for source in (element_guide, crud_docs):
        assert "non-empty scalar string, finite number, or boolean" in source
        assert "dictionaries" in source


def test_docs_explain_viewport_command_numeric_validation() -> None:
    docs = "\n".join(
        (DOCS / relative).read_text(encoding="utf-8")
        for relative in (
            "guides/commands.md",
            "guides/rendering-layouts.md",
            "advanced/troubleshooting.md",
        )
    )

    for term in (
        "duration",
        "padding",
        "renderedPosition",
        "min_zoom",
        "max_zoom",
        "wheel_sensitivity",
        "finite",
        "greater than zero",
    ):
        assert term in docs
