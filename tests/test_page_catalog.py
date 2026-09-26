import ast
import inspect
import runpy
from pathlib import Path
from typing import get_args

import st_graph_workbench as api
from examples.component_capability_map import javascript_capability_rows

ROOT = Path(__file__).resolve().parents[1]
CATALOG = runpy.run_path(str(ROOT / "examples" / "page_catalog.py"))


def test_catalog_routes_order_and_destinations():
    pages = CATALOG["PAGE_CATALOG"]
    tutorials = CATALOG["TUTORIAL_PAGES"]
    assert [guide.lesson for guide in tutorials] == list(range(1, 17))
    assert [guide for guide in pages if guide.default] == [tutorials[0]]
    assert len({guide.path for guide in pages}) == len(pages)
    assert len({guide.url_path for guide in pages}) == len(pages)
    assert all((ROOT / "examples" / guide.path).is_file() for guide in pages)
    assert all(guide.area == "Feature Lab" for guide in CATALOG["LAB_PAGES"])
    assert all(guide.area == "Reference" for guide in CATALOG["REFERENCE_PAGES"])
    for guide in tutorials:
        assert (ROOT / "docs" / guide.manual).is_file()
        assert guide.lab in {lab.path for lab in CATALOG["LAB_PAGES"]}
    app = (ROOT / "examples" / "app.py").read_text(encoding="utf-8")
    assert 'position="hidden"' in app
    assert "for guide in PAGE_CATALOG" in app


def test_catalog_covers_current_exports_arguments_and_frontend():
    tutorials = CATALOG["TUTORIAL_PAGES"]
    documented = {name.strip() for guide in tutorials for name in guide.api.split(",")}
    assert set(api.__all__) <= documented
    assert set(CATALOG["COMPONENT_OPTION_LESSONS"]) == set(
        inspect.signature(api.graph_workbench).parameters
    )
    assert set(CATALOG["CAPABILITY_LESSONS"]) == {
        row["javascript module"] for row in javascript_capability_rows()
    }
    for mapping in ("COMPONENT_OPTION_LESSONS", "CAPABILITY_LESSONS"):
        assert all(
            1 <= number <= len(tutorials) for number in CATALOG[mapping].values()
        )


def test_action_literals_have_executable_destinations():
    for alias, lessons in CATALOG["ACTION_LESSONS"].items():
        sources = "\n".join(
            (ROOT / "examples" / CATALOG["TUTORIAL_PAGES"][number - 1].path).read_text(
                encoding="utf-8"
            )
            for number in lessons
        )
        if f"get_args({alias})" in sources:
            continue
        if alias == "AnalysisAction":
            sources += (ROOT / "examples" / "analysis_examples.py").read_text(
                encoding="utf-8"
            )
        if alias == "NodeAction":
            sources += (ROOT / "examples/demos/node_actions.py").read_text(
                encoding="utf-8"
            )
        if alias == "ExpansionOperation":
            tree = ast.parse(
                (ROOT / "st_graph_workbench/component/expansion.py").read_text(
                    encoding="utf-8"
                )
            )
            handler = next(
                n
                for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name == "_handle_event"
            )
            sources += ast.unparse(handler)
        constants = {
            node.value
            for node in ast.walk(ast.parse(sources))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        assert set(get_args(getattr(api, alias))) <= constants


def test_every_guide_explains_its_purpose():
    for guide in CATALOG["PAGE_CATALOG"]:
        assert all(
            getattr(guide, field).strip()
            for field in ("summary", "contents", "reader_action", "api", "output")
        )
