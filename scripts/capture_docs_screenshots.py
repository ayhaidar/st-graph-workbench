"""Capture deterministic MkDocs screenshots from the Streamlit examples app."""

from __future__ import annotations

import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
import contextlib
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from PIL import Image
from playwright.sync_api import Locator, Page, expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "docs" / "assets" / "screenshots"
VIEWPORT = {"width": 1440, "height": 1000}


@dataclass(frozen=True)
class Capture:
    """Describe one screenshot and the interaction state it requires."""

    filename: str
    route: str
    title: str
    scene: str


CAPTURES = (
    Capture("quick-start.png", "/", "Build your first graph", "component"),
    Capture(
        "data-records.png",
        "/data_helpers_commands",
        "Data helpers and commands",
        "dataframe",
    ),
    Capture(
        "showcase.png",
        "/graph_workbench_showcase",
        "Graph Workbench Showcase",
        "component",
    ),
    Capture(
        "selection-search.png",
        "/investigation_tools",
        "Investigation Tools",
        "selection",
    ),
    Capture(
        "analysis.png",
        "/investigation_tools",
        "Investigation Tools",
        "analysis",
    ),
    Capture(
        "node-expansion.png", "/branch_expansion", "Branch exploration", "expansion"
    ),
    Capture(
        "crud-dialog.png",
        "/crud_data_loading",
        "Interactive CRUD / Data Loading",
        "crud",
    ),
    Capture("layouts.png", "/layout", "Layout algorithms", "layout"),
    Capture(
        "editing-viewport.png",
        "/editing_viewport_tools",
        "Editing And Viewport Tools",
        "editing",
    ),
    Capture(
        "workflow-analysis.png",
        "/learn_analysis",
        "Analyze relationships",
        "workflow-analysis",
    ),
    Capture(
        "workflow-search.png",
        "/learn_search",
        "Find and reveal connections",
        "workflow-search",
    ),
    Capture(
        "workflow-expansion-open.png",
        "/learn_expansion",
        "Expand progressively",
        "workflow-expansion-open",
    ),
    Capture(
        "workflow-expansion-collapsed.png",
        "/learn_expansion",
        "Expand progressively",
        "workflow-expansion-collapsed",
    ),
    Capture(
        "workflow-crud.png", "/learn_crud", "Build CRUD workflows", "workflow-crud"
    ),
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(base_url: str, timeout: float = 30) -> None:
    deadline = time.time() + timeout
    health_url = f"{base_url}/_stcore/health"
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception as error:  # noqa: PERF203
            last_error = error
            time.sleep(0.25)
    raise RuntimeError(f"Streamlit did not become healthy: {last_error}")


@contextlib.contextmanager
def _streamlit_server(base_url: str | None) -> Iterator[str]:
    if base_url:
        normalized = base_url.rstrip("/")
        _wait_for_health(normalized)
        yield normalized
        return

    port = _free_port()
    local_url = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(ROOT / "examples" / "app.py"),
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
            "--server.fileWatcherType",
            "none",
        ],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    try:
        _wait_for_health(local_url)
        yield local_url
    finally:
        if process.poll() is None:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    check=False,
                    capture_output=True,
                )
            else:
                process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def _wait_for_component(page: Page) -> Locator:
    component = page.locator("#container").first
    component.wait_for(state="visible", timeout=20_000)
    page.wait_for_function(
        """() => {
            const container = document.querySelector("#container");
            const cy = container?.querySelector("#cy");
            return container?.dataset.ready === "true" && Boolean(cy?._cyreg?.cy);
        }""",
        timeout=20_000,
    )
    return component


def _open_menu(component: Locator, menu_id: str) -> None:
    component.locator(f"#{menu_id}").evaluate("menu => { menu.open = true; }")


def _select_nodes(component: Locator, count: int) -> None:
    component.locator("#cy").evaluate(
        """(element, count) => {
            const cy = element._cyreg.cy;
            cy.elements(":selected").unselect();
            cy.nodes().slice(0, count).select();
        }""",
        count,
    )


def _select_node_ids(component: Locator, node_ids: list[str]) -> None:
    component.locator("#cy").evaluate(
        """(element, ids) => {
            const cy = element._cyreg.cy;
            cy.elements(":selected").unselect();
            ids.forEach(id => cy.getElementById(id).select());
        }""",
        node_ids,
    )


def _hide_details(component: Locator) -> None:
    _open_menu(component, "selectionControls")
    component.locator("#selectionShowDetails").uncheck()
    component.locator("#selectionControls").evaluate("menu => { menu.open = false; }")


def _frame_graph(component: Locator, top: int = 30) -> None:
    """Frame visible records inside the canvas without changing graph data."""
    component.locator("#cy").evaluate(
        """(element, top) => {
            const cy = element._cyreg.cy;
            // Managed expansion can retain cached records outside the displayed
            // branch. Frame only records that are currently visible on canvas.
            const visible = cy.elements().filter(item => item.visible());
            const bounds = visible.boundingBox();
            // The adaptive toolbar is outside #cy, so top is only a canvas margin.
            const height = cy.height() - top - 30;
            const zoom = Math.min((cy.width() - 100) / bounds.w, height / bounds.h, 1.3);
            cy.viewport({zoom, pan: {
                x: cy.width() / 2 - zoom * (bounds.x1 + bounds.w / 2),
                y: top + height / 2 - zoom * (bounds.y1 + bounds.h / 2),
            }});
        }""",
        top,
    )


def _wait_for_nodes(component: Locator, node_ids: set[str]) -> None:
    expect(component.locator("#graphStatsButtonNodes")).to_have_text(str(len(node_ids)))
    actual = component.locator("#cy").evaluate(
        "element => element._cyreg.cy.nodes().map(node => node.id())"
    )
    assert set(actual) == node_ids, actual


def _branch_action(component: Locator, node_id: str, operation: str) -> None:
    _select_node_ids(component, [node_id])
    component.locator("#cy").evaluate(
        """(element, id) => {
            const node = element._cyreg.cy.getElementById(id);
            node.emit({type: 'cxttap', renderedPosition: node.renderedPosition()});
        }""",
        node_id,
    )
    component.locator(f'#managedExpansionMenu [data-operation="{operation}"]').click()


def _prepare_workflow(page: Page, scene: str) -> Locator:
    component = _wait_for_component(page)
    _hide_details(component)
    _frame_graph(component)
    if scene == "workflow-analysis":
        _select_node_ids(component, ["ALPHA", "BETA"])
        _open_menu(component, "analysisControls")
        component.locator("#analysisShortestPath").click()
        page.wait_for_function("""() => document.querySelector('#cy')._cyreg.cy
            .elements('.analysis-result').length === 9""")
        component.locator("#analysisControls").evaluate(
            "menu => { menu.open = false; }"
        )
    elif scene == "workflow-search":
        component.locator("#graphSearchMode").select_option("node-label")
        component.locator("#graphSearchInput").fill("PLACE")
        component.locator("#graphSearchInput").press("Enter")
        expect(component.locator("#graphSearchStatus")).to_contain_text("3")
        page.wait_for_timeout(500)
        # Pan/zoom back to the overview after search, retaining its actual matches.
        _frame_graph(component)
    elif scene.startswith("workflow-expansion"):
        _branch_action(component, "ABC123", "expand")
        roots = {"ABC123", "location-1", "location-2"}
        _wait_for_nodes(component, roots)
        _branch_action(component, "location-1", "expand")
        _wait_for_nodes(component, roots | {"camera-1"})
        _branch_action(component, "location-1", "load_more")
        left = roots | {"camera-1", "shared", "time-0814"}
        _wait_for_nodes(component, left)
        _branch_action(component, "location-2", "expand")
        expect(component.locator("#graphStatsButtonEdges")).to_have_text("6")
        _wait_for_nodes(component, left | {"AB123"})
        _branch_action(component, "location-2", "load_more")
        _wait_for_nodes(component, left | {"camera-2", "AB123"})
        expect(component.locator("#graphStatsButtonEdges")).to_have_text("8")
        _frame_graph(component)
        if scene.endswith("collapsed"):
            checkpoint = component.locator("#cy").evaluate(
                "el => ({zoom: el._cyreg.cy.zoom(), pan: el._cyreg.cy.pan()})"
            )
            _branch_action(component, "location-1", "collapse")
            _wait_for_nodes(component, roots | {"camera-2", "shared", "AB123"})
            expect(component.locator("#graphStatsButtonEdges")).to_have_text("5")
            assert (
                component.locator("#cy").evaluate(
                    "el => ({zoom: el._cyreg.cy.zoom(), pan: el._cyreg.cy.pan()})"
                )
                == checkpoint
            )
        # The same camera and selected shared record make the comparison readable.
        _select_node_ids(component, ["shared"])
        assert component.locator("#cy").evaluate(
            "el => el._cyreg.cy.getElementById('shared').style('background-image').includes('description')"
        )
    elif scene == "workflow-crud":
        component.scroll_into_view_if_needed()
        _open_menu(component, "crudControls")
        component.locator("#crudCreateNode").click()
        dialog = page.get_by_role("dialog", name="Graph record")
        dialog.wait_for(state="visible")
        dialog.get_by_role("combobox", name="Node type").click()
        page.get_by_role("option", name="Camera (CAMERA)", exact=True).click()
        dialog.get_by_role("textbox", name="Record ID", exact=True).fill("camera-8")
        dialog.get_by_role("textbox", name="Name", exact=True).fill("Camera 8")
        dialog.get_by_text("Create node", exact=True).click()
        return dialog
    page.wait_for_timeout(500)
    return component


def _prepare_scene(page: Page, scene: str) -> Locator | None:
    if scene.startswith("workflow-"):
        return _prepare_workflow(page, scene)
    if scene == "dataframe":
        section_heading = page.get_by_role(
            "heading", name="Table to records to graph", exact=True
        )
        section_heading.evaluate(
            "heading => heading.scrollIntoView({block: 'start', inline: 'nearest'})"
        )
        dataframe = page.locator('[data-testid="stDataFrame"]').first
        dataframe.wait_for(state="visible", timeout=20_000)
        page.wait_for_timeout(350)
        return None

    component = _wait_for_component(page)
    if scene == "selection":
        _select_nodes(component, 3)
    elif scene == "analysis":
        _select_node_ids(component, ["case", "time_0910"])
        _open_menu(component, "analysisControls")
        button = component.locator("#analysisShortestPath")
        button.wait_for(state="visible")
        if button.is_enabled():
            button.click()
            page.wait_for_timeout(1_000)
        output_heading = page.get_by_role(
            "heading", name="Returned investigation value", exact=True
        )
        output_heading.scroll_into_view_if_needed()
        page.wait_for_timeout(350)
        return None
    elif scene == "expansion":
        component.locator("#cy").evaluate(
            """element => {
                const cy = element._cyreg.cy;
                const node = cy.getElementById("ABC123");
                if (node.length) {
                    node.emit({
                        type: "cxttap",
                        renderedPosition: node.renderedPosition(),
                    });
                }
            }"""
        )
        component.locator("#managedExpansionMenu").wait_for(state="visible")
    elif scene == "crud":
        _open_menu(component, "crudControls")
        component.locator("#crudCreateNode").click()
        dialog = page.get_by_role("dialog").first
        dialog.wait_for(state="visible", timeout=20_000)
        return None
    elif scene == "editing":
        _open_menu(component, "editControls")
    elif scene == "layout":
        controls_heading = page.get_by_role(
            "heading", name="Layout controls", exact=True
        )
        controls_heading.scroll_into_view_if_needed()
        page.wait_for_timeout(350)
        return None

    page.wait_for_timeout(350)
    return component


def _save_optimized(page: Page, target: Path, locator: Locator | None) -> None:
    if locator is None:
        page.screenshot(path=target, full_page=False)
    else:
        locator.scroll_into_view_if_needed()
        page.wait_for_timeout(200)
        locator.screenshot(path=target)

    with Image.open(target) as image:
        image.save(target, format="PNG", optimize=True)


def _capture_all_sync(
    base_url: str | None, output_dir: Path, *, gallery_only: bool = False
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    with _streamlit_server(base_url) as app_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=1)
        page.emulate_media(reduced_motion="reduce", color_scheme="light")
        try:
            for capture in CAPTURES:
                if gallery_only and not capture.scene.startswith("workflow-"):
                    continue
                page.goto(f"{app_url}{capture.route}", wait_until="domcontentloaded")
                page.get_by_role(
                    "heading", name=capture.title, exact=True
                ).first.wait_for(state="visible", timeout=20_000)
                target = output_dir / capture.filename
                locator = _prepare_scene(page, capture.scene)
                page.evaluate("document.fonts.ready")
                _save_optimized(page, target, locator)
                written.append(target)
        finally:
            browser.close()
    return written


def capture_all(
    base_url: str | None, output_dir: Path, *, gallery_only: bool = False
) -> list[Path]:
    """Capture scenes, isolating Playwright when the caller owns an event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return _capture_all_sync(base_url, output_dir, gallery_only=gallery_only)

    # pytest-playwright can leave an asyncio loop active on the test thread.
    # The synchronous Playwright API requires a thread without a running loop.
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(
            _capture_all_sync,
            base_url,
            output_dir,
            gallery_only=gallery_only,
        ).result()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        help="Reuse a running examples app, for example http://localhost:8502.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for PNG files (default: docs/assets/screenshots).",
    )
    parser.add_argument(
        "--gallery",
        action="store_true",
        help="Capture only the README/homepage workflow gallery, preserving reference images.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Capture to a temporary directory and validate without replacing docs.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.check:
        with tempfile.TemporaryDirectory(prefix="st-graph-workbench-docs-") as temp:
            written = capture_all(args.base_url, Path(temp), gallery_only=args.gallery)
            print(f"Validated {len(written)} documentation screenshots.")
        return 0

    written = capture_all(
        args.base_url, args.output_dir.resolve(), gallery_only=args.gallery
    )
    for path in written:
        print(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
