"""Pure checkpoints, executable snippets, and state-boundary tests."""

import ast
from copy import deepcopy
import importlib
import inspect
from pathlib import Path
from typing import get_args

import pytest
from st_graph_workbench import apply_graph_command, get_element, validate_elements
from st_graph_workbench.component.commands import GraphCommandOperation

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def lesson_modules(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "examples"))
    return importlib.import_module("tutorials.data"), importlib.import_module(
        "tutorials.workflows"
    )


def test_all_tutorial_sources_compile_and_follow_lesson_structure():
    from examples.page_catalog import TUTORIAL_PAGES

    for guide in TUTORIAL_PAGES:
        path = ROOT / "examples" / guide.path
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
        assert "begin_lesson(" in source and "finish_lesson(" in source
        if guide.lesson == 9:
            assert source.index("show_graph_data(") < source.index(
                "render_expansion_workflow(state"
            )
            shared = (ROOT / "examples/expansion_workflow.py").read_text(
                encoding="utf-8"
            )
            assert "with show_example(__file__):" in shared
            assert "result = graph_workbench(" in shared
            assert "render_dictionary_preview(" in shared
            assert "mistakes=" in source and "conclusion=" in source
            continue
        assert (
            source.index("show_graph_data(") < source.index("result = graph_workbench(")
            if guide.lesson != 16
            else source.index("show_graph_data(")
            < source.index("first = graph_workbench(")
        )
        assert "with show_example(__file__):" in source
        assert "with st.echo():" not in source
        assert "show_result(" in source
        assert "mistakes=" in source and "conclusion=" in source
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "show_result"
            ):
                assert any(keyword.arg == "label" for keyword in node.keywords)
        assert any(
            isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
            for node in tree.body
        )


def test_checkpoints_are_valid_independent_and_expansion_counts_are_real(
    lesson_modules,
):
    data, _ = lesson_modules
    first = data.first_graph()
    assert (len(first["nodes"]), len(first["edges"])) == (2, 1)
    graph = data.checkpoint()
    original = deepcopy(graph)
    marked = data.expansion_graph(graph)
    assert get_element(marked, "ABC123")["data"]["expansion"]["next_count"] == 2
    assert sum("expansion" in node["data"] for node in marked["nodes"]) == 1
    expanded = data.toggle_related(graph, False)
    assert len(expanded["nodes"]) == len(graph["nodes"]) + 2
    assert data.toggle_related(expanded, True) == original
    assert graph == original
    for count in (0, 10, 100, 1000):
        for compound in (False, True):
            validate_elements(data.fleet_graph(count, compound=compound))
    assert data.checkpoint() == graph


def test_tutorial_exercises_match_the_shared_source_data(lesson_modules):
    data, _ = lesson_modules
    from examples.analysis_examples import analysis_example_payloads

    graph = data.checkpoint()
    assert (len(graph["nodes"]), len(graph["edges"])) == (7, 5)
    sightings = data.SIGHTING_RECORDS
    assert len(sightings) == 5
    assert sum(row["Entity"] == "ABC123" for row in sightings) == 2
    assert sum(row["Entity"] in {"ABC123", "ALPHA"} for row in sightings) == 3

    results = {
        example["data"]["analysis"]: example["data"]
        for example in analysis_example_payloads(
            graph,
            shortest_path=("ALPHA", "BETA"),
            traversal_root="ABC123",
            degree_node="ABC123",
        )
    }
    assert results["shortest_path"]["distance"] == 4
    assert len(results["connected_components"]["components"]) == 2
    for algorithm in ("bfs", "dfs"):
        assert set(results[algorithm]["node_ids"]) == {
            "ABC123",
            "ALPHA",
            "BETA",
            "location_1",
            "location_2",
        }
    assert results["degree"]["degree"] == 2
    assert results["degree"]["indegree"] == 0
    assert results["degree"]["outdegree"] == 2
    for count in (30, 50, 60, 100, 180, 1000):
        for compound in (False, True):
            generated = data.fleet_graph(count, compound=compound)
            assert len(generated["nodes"]) == count + 3 + int(compound)
            assert len(generated["edges"]) == count


def test_every_command_example_executes(lesson_modules):
    data, workflows = lesson_modules
    for operation in get_args(GraphCommandOperation):
        graph = data.checkpoint()
        command = workflows.command_example(operation, f"test-{operation}")
        result = apply_graph_command(graph, command)
        validate_elements(result)
        assert command["operation"] == operation


@pytest.mark.parametrize(
    "payload,expected_ids",
    [
        ({}, []),
        (
            {
                "added_elements": [
                    {"group": "nodes", "data": {"id": "draft", "label": "NODE"}}
                ]
            },
            ["draft"],
        ),
        (
            {
                "updated_elements": [
                    {"group": "nodes", "data": {"id": "draft"}, "locked": True}
                ]
            },
            ["draft"],
        ),
        (
            {
                "elements": {
                    "nodes": [{"data": {"id": "a"}}, {"data": {"id": "b"}}],
                    "edges": [{"data": {"id": "ab", "source": "a", "target": "b"}}],
                }
            },
            ["a", "b", "ab"],
        ),
        (
            {
                "operation": "delete_selected",
                "deleted_node_ids": ["a"],
                "deleted_edge_ids": ["ab"],
            },
            ["a", "ab"],
        ),
        ({"positions": [{"id": "a", "position": {"x": 40, "y": 80}}]}, ["a"]),
        ({"elements": {}}, []),
    ],
)
def test_edit_report_contains_only_returned_records(
    lesson_modules, payload, expected_ids
):
    _, workflows = lesson_modules
    original = deepcopy(payload)
    frame = workflows.edit_report_frame(payload)
    assert frame["id"].tolist() == expected_ids
    assert payload == original
    if payload.get("operation") == "delete_selected":
        assert frame["change"].tolist() == ["Deleted", "Deleted"]
        assert frame["record_group"].tolist() == ["node", "edge"]


def test_crud_types_have_matching_styles_and_bundled_icons(lesson_modules):
    data, _ = lesson_modules
    from examples.demos.demo_helpers import demo_node_styles
    from st_graph_workbench import NodeStyle

    styles = {
        style.label: style
        for style in demo_node_styles(text_size=18)
        if isinstance(style, NodeStyle)
    }
    assert set(data.CRUD_NODE_TYPES) == {
        "PLACE",
        "VEHICLE",
        "PERSON",
        "PHONE",
        "CAMERA",
        "TIME",
        "CHECKPOINT",
    }
    for label in data.CRUD_NODE_TYPES:
        style = styles[label]
        assert style.color and style.caption == "name"
        assert (
            ROOT / "st_graph_workbench/frontend/build/icons" / f"{style.icon}.svg"
        ).is_file()


def test_loading_overlap_error_empty_completion_and_stale_cursors(lesson_modules):
    _, workflows = lesson_modules
    state = {"elements": workflows.loading_checkpoint(), "sequence": 0, "generation": 0}
    request = {"request_id": "one", "cursor": 30, "page_size": 30}
    workflows.load_next_batch(state, request, outcome="Fail once")
    assert state["acknowledged"] == "one" and state["error"]
    assert state.get("loaded", 30) == 30
    workflows.load_next_batch(state, {**request, "request_id": "retry"})
    assert state["loaded"] == 60 and len(state["elements"]["nodes"]) == 63
    snapshot = deepcopy(state["elements"])
    workflows.load_next_batch(state, {**request, "request_id": "stale"})
    assert state["acknowledged"] == "stale" and state["elements"] == snapshot
    workflows.load_next_batch(
        state,
        {**request, "request_id": "empty", "cursor": 60},
        outcome="Empty final batch",
    )
    assert state["complete"] and state["loaded"] == 60
    state["complete"] = False
    for cursor in range(60, 180, 30):
        workflows.load_next_batch(
            state, {"request_id": str(cursor), "cursor": cursor, "page_size": 30}
        )
    assert state["complete"] and state["loaded"] == 180
    assert len(state["elements"]["nodes"]) == 183
    validate_elements(state["elements"])


def test_position_restore_is_atomic_and_preserves_other_records(lesson_modules):
    data, workflows = lesson_modules
    graph = data.checkpoint()
    snapshot = deepcopy(graph)
    changed = workflows.restore_positions(
        graph, {"positions": [{"id": "ABC123", "position": {"x": 123, "y": 456}}]}
    )
    assert get_element(changed, "ABC123")["position"] == {"x": 123, "y": 456}
    assert graph == snapshot
    with pytest.raises(ValueError):
        workflows.restore_positions(
            graph,
            {"positions": [{"id": "ABC123", "position": {"x": float("nan"), "y": 0}}]},
        )
    assert graph == snapshot


def test_manual_links_handle_index_pages_and_custom_base(monkeypatch):
    from examples.page_links import docs_url

    monkeypatch.delenv("GRAPH_WORKBENCH_DOCS_URL", raising=False)
    assert docs_url("reference/index.md") == (
        "https://ayhaidar.github.io/st-graph-workbench/reference/"
    )
    monkeypatch.setenv("GRAPH_WORKBENCH_DOCS_URL", "https://example.test/manual/")
    assert docs_url("guides/selection-search.md") == (
        "https://example.test/manual/guides/selection-search/"
    )


def test_lesson_state_reset_and_events_are_isolated(lesson_modules, monkeypatch):
    data, _ = lesson_modules
    common = importlib.import_module("tutorials.common")
    session = {}
    monkeypatch.setattr(common.st, "session_state", session)
    first = common.lesson_state(1, data.first_graph)
    second = common.lesson_state(2)
    first_key = common.component_key(1)
    session[first_key] = {
        "action": "record_tapped",
        "data": {"target_id": "ABC123"},
        "timestamp": 1,
    }
    common.receive_event(1)
    session[first_key] = {"action": "selection", "data": {}, "timestamp": 2}
    common.receive_event(1)
    assert "record_tapped" in first["results_graph"]
    assert common.receive_event(1) is None
    session["tutorial_01_widget_example"] = "edited"
    session["tutorial_02_widget_example"] = "keep"
    common.reset_lesson(1, data.first_graph)
    assert common.component_key(1) != first_key
    assert common.lesson_state(1)["elements"] == data.first_graph()
    assert common.lesson_state(2) is second
    assert "tutorial_01_widget_example" not in session
    assert session["tutorial_02_widget_example"] == "keep"


def test_example_code_is_displayed_before_the_block_runs(lesson_modules, monkeypatch):
    common = importlib.import_module("tutorials.common")
    displayed = []
    monkeypatch.setattr(
        common.st, "code", lambda source, **kwargs: displayed.append(source)
    )
    with common.show_example(__file__):
        # This teaching comment must appear before the executing statement.
        answer = 6 * 7
        assert displayed
    assert answer == 42
    assert "answer = 6 * 7" in displayed[0]
    assert displayed[0].startswith("# This teaching comment")
    compile(displayed[0], "displayed.py", "exec")


def test_every_lesson_has_specific_objectives_and_multiple_code_examples(
    lesson_modules,
):
    from examples.page_catalog import TUTORIAL_PAGES

    common = importlib.import_module("tutorials.common")
    objective_sets = set()
    for guide in TUTORIAL_PAGES:
        assert len(guide.learning_objectives) == 3
        assert all(len(target.split()) >= 8 for target in guide.learning_objectives)
        objective_sets.add(guide.learning_objectives)
        path = (
            ROOT
            / "examples"
            / ("expansion_workflow.py" if guide.lesson == 9 else guide.path)
        )
        source = path.read_text(encoding="utf-8")
        assert 'st.subheader("Code in practice")' in source
        tree = ast.parse(source)
        examples = []
        helper_calls = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                helper_calls += node.func.id == "show_function"
            if not isinstance(node, ast.With):
                continue
            if any(
                isinstance(item.context_expr, ast.Call)
                and isinstance(item.context_expr.func, ast.Name)
                and item.context_expr.func.id == "show_example"
                for item in node.items
            ):
                snippet = common.example_source(source, node.lineno)
                compile(snippet, f"{path}:{node.lineno}", "exec")
                examples.append(snippet)
        assert len(examples) + helper_calls >= 2, guide.title
        assert any("# " in snippet for snippet in examples), guide.title
    assert len(objective_sets) == len(TUTORIAL_PAGES)


def test_source_examples_preserve_comments_and_exclude_neighboring_code(lesson_modules):
    common = importlib.import_module("tutorials.common")
    source = """before = 1
with show_example(__file__):
    # Explain the input before the first statement.
    answer = 42
    if answer:
        # Keep comments inside branches too.
        result = answer + 1
after = 2
"""
    snippet = common.example_source(source, 2)
    assert snippet.startswith("# Explain the input")
    assert "# Keep comments inside branches too." in snippet
    assert "before =" not in snippet and "after =" not in snippet
    namespace = {}
    exec(compile(snippet, "example.py", "exec"), namespace)
    assert namespace["result"] == 43


def test_supporting_code_is_the_actual_function_source(lesson_modules, monkeypatch):
    _, workflows = lesson_modules
    common = importlib.import_module("tutorials.common")
    descriptions, displayed = [], []
    monkeypatch.setattr(common.st, "markdown", descriptions.append)
    monkeypatch.setattr(
        common.st, "code", lambda source, **kwargs: displayed.append((source, kwargs))
    )
    common.show_function(workflows.load_next_batch, "The loader used by lesson 15.")
    source, options = displayed[0]
    assert source == inspect.getsource(workflows.load_next_batch)
    assert descriptions == ["The loader used by lesson 15."]
    assert options["height"] == 360 and options["wrap_lines"]
    compile(source, "loader.py", "exec")


def test_analysis_table_code_handles_each_actual_result(lesson_modules, monkeypatch):
    data, _ = lesson_modules
    common = importlib.import_module("tutorials.common")
    from examples.analysis_examples import analysis_example_payloads
    from st_graph_workbench import records_to_dataframe

    source = (ROOT / "examples/tutorials/analysis.py").read_text(encoding="utf-8")
    block = next(
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.With)
        and any(
            isinstance(child, ast.Name) and child.id == "analysis_data"
            for child in ast.walk(node)
        )
    )
    snippet = compile(
        common.example_source(source, block.lineno), "analysis-table.py", "exec"
    )
    frames = []
    monkeypatch.setattr(
        common.st, "dataframe", lambda frame, **kwargs: frames.append(frame)
    )
    graph = data.checkpoint()
    results = analysis_example_payloads(
        graph,
        shortest_path=("ALPHA", "BETA"),
        traversal_root="ABC123",
        degree_node="ABC123",
    )
    for scenario in results:
        payload = scenario["data"]
        exec(
            snippet,
            {
                "state": {"elements": graph, "analysis": {"data": payload}},
                "st": common.st,
                "records_to_dataframe": records_to_dataframe,
            },
        )
        expected = (
            7
            if payload["analysis"] == "connected_components"
            else 1
            if payload["analysis"] == "degree"
            else 5
        )
        assert len(frames[-1]) == expected
    exec(
        snippet,
        {
            "state": {"elements": graph},
            "st": common.st,
            "records_to_dataframe": records_to_dataframe,
        },
    )
    assert frames[-1].empty


def test_data_preview_uses_its_explicit_label(lesson_modules, monkeypatch):
    data, _ = lesson_modules
    common = importlib.import_module("tutorials.common")
    headings, previews = [], []
    monkeypatch.setattr(common.st, "header", headings.append)
    monkeypatch.setattr(
        common,
        "render_dictionary_preview",
        lambda *args, **kwargs: previews.append((args, kwargs)),
    )
    payload = data.first_graph()
    common.show_result(payload, "Input records", label="Input graph dictionary")
    assert headings == ["Data and practical result"]
    assert previews == [
        (("Input graph dictionary", payload, "Input records"), {"height": 280})
    ]
