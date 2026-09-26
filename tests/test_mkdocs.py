from __future__ import annotations

import ast
import inspect
import re
import subprocess
import sys
from pathlib import Path
from typing import get_args
import yaml

from PIL import Image

from examples.component_capability_map import javascript_capability_rows
from st_graph_workbench.component import commands, component
from st_graph_workbench import ExpansionOperation
from st_graph_workbench.component.layouts import LAYOUTS


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SCREENSHOTS = {
    "analysis.png",
    "crud-dialog.png",
    "data-records.png",
    "editing-viewport.png",
    "layouts.png",
    "node-expansion.png",
    "quick-start.png",
    "selection-search.png",
    "showcase.png",
    "workflow-analysis.png",
    "workflow-search.png",
    "workflow-expansion-open.png",
    "workflow-expansion-collapsed.png",
    "workflow-crud.png",
}
LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
SCREENSHOT_PATTERN = re.compile(
    r"!\[([^\]]+)\]\([^)]*assets/screenshots/([^/)]+\.png)\)"
)
SNIPPET_PATTERN = re.compile(r'--8<--\s+"([^"]+)"')
BANNED_TERMS = re.compile(r"\b(?:chapter|chapters|wallet|wallets)\b", re.IGNORECASE)


def _markdown_files() -> list[Path]:
    return sorted(DOCS.rglob("*.md"))


def _docs_corpus() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in _markdown_files())


def test_local_mkdocs_config_serves_without_the_pages_subpath() -> None:
    config = yaml.safe_load((ROOT / "mkdocs.local.yml").read_text(encoding="utf-8"))

    assert config["INHERIT"] == "mkdocs.yml"
    assert config["site_url"] is None


def test_mkdocs_navigation_targets_exist() -> None:
    config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    nav_targets = re.findall(r"^\s+- [^:]+:\s+([^\s]+\.md)$", config, re.MULTILINE)
    local_targets = [target for target in nav_targets if "://" not in target]

    assert local_targets
    assert [target for target in local_targets if not (DOCS / target).is_file()] == []
    assert "Publishing the documentation" not in config
    assert "implementation-notes" not in config


def test_markdown_links_and_snippets_resolve() -> None:
    failures = []
    for path in [ROOT / "README.md", *_markdown_files()]:
        source = path.read_text(encoding="utf-8")
        for raw_target in LINK_PATTERN.findall(source):
            target = raw_target.strip().split()[0].strip("<>").split("#", 1)[0]
            if not target or "://" in target or target.startswith(("mailto:", "#")):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                failures.append(f"{path.relative_to(ROOT)} -> {target}")
        for snippet in SNIPPET_PATTERN.findall(source):
            if not (ROOT / snippet).is_file():
                failures.append(f"{path.relative_to(ROOT)} -> {snippet}")

    assert failures == []


def test_published_docs_do_not_link_to_a_readers_local_examples_port() -> None:
    clickable_localhost = re.compile(r"\]\(http://localhost:8502(?:/[^)]*)?\)")
    failures = [
        path.relative_to(ROOT).as_posix()
        for path in _markdown_files()
        if clickable_localhost.search(path.read_text(encoding="utf-8"))
    ]

    assert failures == []


def test_guides_have_contents_introduction_and_conclusion() -> None:
    failures = []
    guide_files = [
        *sorted((DOCS / "getting-started").glob("*.md")),
        *sorted((DOCS / "concepts").glob("*.md")),
        *sorted((DOCS / "guides").glob("*.md")),
        *sorted((DOCS / "recipes").glob("*.md")),
    ]
    for path in guide_files:
        source = path.read_text(encoding="utf-8")
        if "## On this page" not in source or "## Conclusion" not in source:
            failures.append(path.relative_to(ROOT).as_posix())

    assert failures == []


def test_all_public_option_values_are_documented() -> None:
    corpus = _docs_corpus()
    option_types = (
        component.NodeAction,
        component.CrudAction,
        component.EditAction,
        component.ViewportAction,
        component.SelectionMode,
        component.AnalysisAction,
        component.PerformanceProfile,
        component.ElementsSync,
        commands.GraphCommandOperation,
        ExpansionOperation,
    )
    expected = set(LAYOUTS)
    for option_type in option_types:
        expected.update(get_args(option_type))

    missing = sorted(value for value in expected if f"`{value}`" not in corpus)

    assert missing == []


def test_every_component_argument_is_documented() -> None:
    signature = inspect.signature(component.graph_workbench)
    docstring = inspect.getdoc(component.graph_workbench) or ""

    missing = [
        name
        for name in signature.parameters
        if not re.search(rf"^{re.escape(name)}\s*:", docstring, re.MULTILINE)
    ]

    assert missing == []
    assert "Returns\n-------" in docstring
    assert "Raises\n------" in docstring


def test_frontend_capability_map_is_documented() -> None:
    matrix = (DOCS / "reference" / "capability-matrix.md").read_text(encoding="utf-8")
    failures = []
    for row in javascript_capability_rows():
        modules = [part.strip() for part in row["javascript module"].split("/")]
        if not all(module in matrix for module in modules):
            failures.append(row["javascript module"])

    assert len(javascript_capability_rows()) == 25
    assert failures == []


def test_documentation_stays_in_intelligence_domain() -> None:
    failures = []
    for path in _markdown_files():
        matches = sorted(set(BANNED_TERMS.findall(path.read_text(encoding="utf-8"))))
        if matches:
            failures.append(f"{path.relative_to(ROOT)}: {matches}")

    assert failures == []


def test_brand_assets_match_canonical_images() -> None:
    for filename in ("logo.png", "logo_icon.png"):
        assert (DOCS / "assets" / "images" / filename).read_bytes() == (
            ROOT / "images" / filename
        ).read_bytes()


def test_python_snippets_compile_and_pure_example_runs() -> None:
    snippets = sorted((DOCS / "snippets").glob("*.py"))
    assert snippets
    for path in snippets:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    subprocess.run(
        [sys.executable, "-m", "docs.snippets.managed_expansion"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )

    result = subprocess.run(
        [sys.executable, str(DOCS / "snippets" / "record_roundtrip.py")],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "ABC123" in result.stdout
    assert "Harbour camera 7" in result.stdout


def test_screenshot_manifest_and_assets_match() -> None:
    script = ast.parse(
        (ROOT / "scripts" / "capture_docs_screenshots.py").read_text(encoding="utf-8")
    )
    filenames = {
        node.args[0].value
        for node in ast.walk(script)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Capture"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    }
    image_paths = {
        path.name for path in (DOCS / "assets" / "screenshots").glob("*.png")
    }

    assert filenames == SCREENSHOTS
    assert image_paths == SCREENSHOTS
    for path in (DOCS / "assets" / "screenshots").glob("*.png"):
        with Image.open(path) as image:
            assert image.format == "PNG"
            assert image.width >= (450 if path.name == "workflow-crud.png" else 600)
            assert image.height >= 300


def test_every_screenshot_has_alt_text_and_caption() -> None:
    documented = {}
    for path in _markdown_files():
        source = path.read_text(encoding="utf-8")
        for alt_text, filename in SCREENSHOT_PATTERN.findall(source):
            documented[filename] = alt_text.strip()
            assert "screenshot-caption" in source

    assert set(documented) == SCREENSHOTS
    assert all(documented.values())


def test_mkdocs_build_is_strict(tmp_path: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "mkdocs",
            "build",
            "--strict",
            "--site-dir",
            str(tmp_path / "site"),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    site = tmp_path / "site"
    home = (site / "index.html").read_text(encoding="utf-8")
    assert 'href="https://ayhaidar.github.io/st-graph-workbench/"' in home
    assert 'src="assets/screenshots/workflow-analysis.png"' in home
    gallery = (site / "getting-started/in-action/index.html").read_text(
        encoding="utf-8"
    )
    for filename in SCREENSHOTS:
        if filename.startswith("workflow-"):
            assert f'src="../../assets/screenshots/{filename}"' in gallery
            assert (site / "assets/screenshots" / filename).is_file()
