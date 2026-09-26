import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_javascript_capability_map_covers_frontend_modules():
    namespace = runpy.run_path(str(ROOT / "examples" / "component_capability_map.py"))
    rows = namespace["javascript_capability_rows"]()
    mapped_modules = " ".join(row["javascript module"] for row in rows)

    frontend_src = ROOT / "st_graph_workbench" / "frontend" / "src"
    expected_modules = {"index.js"}
    expected_modules.update(
        path.name
        for folder in ("components", "utils")
        for path in (frontend_src / folder).glob("*.js")
    )

    missing = sorted(
        module for module in expected_modules if module not in mapped_modules
    )
    assert missing == []


def test_javascript_capability_maps_render_as_scrollable_guides():
    page_overview = (ROOT / "examples" / "page_overview.py").read_text(encoding="utf-8")
    mapping_pages = [
        ROOT / "examples" / "docs" / "frontend_architecture.py",
        ROOT / "examples" / "demos" / "investigation_tools.py",
    ]

    assert "def render_javascript_capability_map" in page_overview
    assert "st.container(border=True, height=height)" in page_overview

    for path in mapping_pages:
        source = path.read_text(encoding="utf-8")
        assert "render_javascript_capability_map" in source
        assert "st.table(" not in source
