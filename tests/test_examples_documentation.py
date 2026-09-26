import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = ROOT / "examples"
PAGE_DIRS = (EXAMPLES_DIR / "docs", EXAMPLES_DIR / "demos")
SKIPPED_PAGE_NAMES = {"__init__.py", "demo_helpers.py"}
DATA_BEFORE_GRAPH_MARKERS = (
    "Data before rendering",
    "Source records",
    "Current Python-owned graph",
)
BANNED_STREAMLIT_PATTERNS = (
    "use_container_width",
    "unsafe_allow_html=True",
    "st.table(",
)
BANNED_EXTERNAL_COMPANION_TERMS = re.compile(
    r"\b(?:book|chapter|chapters|companion)\b",
    re.IGNORECASE,
)


def _page_files() -> list[Path]:
    return sorted(
        path
        for directory in PAGE_DIRS
        for path in directory.glob("*.py")
        if path.name not in SKIPPED_PAGE_NAMES
    )


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _function_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _calls_named(tree: ast.Module, name: str) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _function_name(node.func) == name
    ]


def _has_keyword(call: ast.Call, name: str) -> bool:
    return any(keyword.arg == name for keyword in call.keywords)


def test_docs_and_demo_pages_start_with_contents_overview() -> None:
    missing = []
    for path in _page_files():
        source = path.read_text(encoding="utf-8")
        if (
            "render_page_overview(" not in source
            and "render_demo_intro(" not in source
            and '"### On this page"' not in source
            and path.name
            != "project_overview.py"  # The README supplies its own contents list.
        ):
            missing.append(path.relative_to(ROOT).as_posix())

    assert missing == []


def test_examples_avoid_deprecated_streamlit_display_patterns() -> None:
    failures = []
    for path in _page_files():
        source = path.read_text(encoding="utf-8")
        for pattern in BANNED_STREAMLIT_PATTERNS:
            if pattern in source:
                failures.append(f"{path.relative_to(ROOT).as_posix()}: {pattern}")

        tree = _tree(path)
        for call in _calls_named(tree, "radio"):
            for keyword in call.keywords:
                if (
                    keyword.arg == "horizontal"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                ):
                    failures.append(
                        f"{path.relative_to(ROOT).as_posix()}:{call.lineno}: "
                        "st.radio(horizontal=True)"
                    )

    assert failures == []


def test_dataframes_hide_unhelpful_default_index() -> None:
    failures = []
    for path in _page_files():
        tree = _tree(path)
        for call in _calls_named(tree, "dataframe"):
            if not _has_keyword(call, "hide_index"):
                failures.append(f"{path.relative_to(ROOT).as_posix()}:{call.lineno}")

    assert failures == []


def test_graph_demo_pages_show_input_data_before_component() -> None:
    failures = []
    for path in sorted((EXAMPLES_DIR / "demos").glob("*.py")):
        if path.name in SKIPPED_PAGE_NAMES:
            continue

        tree = _tree(path)
        graph_calls = _calls_named(tree, "graph_workbench")
        if not graph_calls:
            continue

        first_graph_line = min(call.lineno for call in graph_calls)
        source_before_graph = "\n".join(
            path.read_text(encoding="utf-8").splitlines()[: first_graph_line - 1]
        )
        if not any(
            marker in source_before_graph for marker in DATA_BEFORE_GRAPH_MARKERS
        ):
            failures.append(path.relative_to(ROOT).as_posix())

    assert failures == []


def test_app_copy_stays_standalone() -> None:
    copy_files = [ROOT / "README.md", ROOT / "CHANGELOG.md", *_page_files()]
    failures = []

    for path in copy_files:
        source = path.read_text(encoding="utf-8")
        matches = sorted(set(BANNED_EXTERNAL_COMPANION_TERMS.findall(source)))
        if matches:
            failures.append(f"{path.relative_to(ROOT).as_posix()}: {matches}")

    assert failures == []


def test_investigation_demo_turns_returned_records_into_a_dataframe() -> None:
    source = (EXAMPLES_DIR / "demos" / "investigation_tools.py").read_text(
        encoding="utf-8"
    )

    assert 'event_data.get("selected_elements")' in source
    assert 'event_data.get("matched_elements")' in source
    assert "records_to_dataframe(returned_records)" in source
    assert "filtered, joined, summarized, or exported" in source


def test_feature_finder_links_to_working_examples_without_duplicate_reference() -> None:
    source = (EXAMPLES_DIR / "demos" / "demo_overview.py").read_text(encoding="utf-8")

    assert "LAB_PAGES" in source
    assert "st.page_link(" in source
    assert "st.text_input(" in source
    assert "render_page_directory" not in source
    assert "render_javascript_capability_map" not in source


def test_packaged_intelligence_graph_is_loaded_by_data_helpers_demo() -> None:
    source = (EXAMPLES_DIR / "demos" / "data_helpers_commands.py").read_text(
        encoding="utf-8"
    )
    sample_path = EXAMPLES_DIR / "data" / "intelligence_case.json"

    assert sample_path.is_file()
    assert '"data" / "intelligence_case.json"' in source
    assert "json.loads" in source
    assert "validate_elements(payload)" in source
    assert "load_graph_file(str(SAMPLE_GRAPH_PATH))" in source
