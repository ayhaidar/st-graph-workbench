from pathlib import Path

from st_graph_workbench import (
    AnalysisAction,
    CrudAction,
    EdgeStyle,
    ElementId,
    ElementIdInput,
    Event,
    EditAction,
    ElementsSync,
    NodeStyle,
    NodeAction,
    PerformanceProfile,
    ProgressiveLoadConfig,
    SelectionMode,
    StyleRule,
    ViewportAction,
    delete_elements,
    get_element,
    graph_workbench,
    update_element_data,
    upsert_elements,
    validate_elements,
)


def test_new_package_exports_public_api():
    assert callable(graph_workbench)
    assert NodeStyle
    assert EdgeStyle
    assert ElementId
    assert ElementIdInput
    assert StyleRule
    assert Event
    assert AnalysisAction
    assert CrudAction
    assert EditAction
    assert ElementsSync
    assert NodeAction
    assert PerformanceProfile
    assert ProgressiveLoadConfig
    assert SelectionMode
    assert ViewportAction
    assert callable(get_element)
    assert callable(upsert_elements)
    assert callable(update_element_data)
    assert callable(delete_elements)
    assert callable(validate_elements)


def test_old_python_imports_are_not_left_in_source():
    root = Path(__file__).resolve().parents[1]
    ignored_parts = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
    }
    old_package = "st" + "_link" + "_analysis"
    old_component = "st_graph_workbench" + "." + "st_graph_workbench"
    forbidden = (
        f"from {old_package}",
        f"import {old_package}",
        f"{old_package}.",
        f"{old_package}/",
        f"{old_package}\\",
        old_component,
    )
    checked_suffixes = {".md", ".py", ".toml", ".js", ".json", ".html", ".css", ".yml"}

    offenders = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in checked_suffixes:
            continue
        if ignored_parts & set(path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden:
            if pattern in text:
                offenders.append(f"{path.relative_to(root)} contains {pattern}")

    assert offenders == []
