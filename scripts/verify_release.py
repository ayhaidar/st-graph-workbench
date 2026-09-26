"""Build and verify an installed wheel without publishing or touching live servers."""

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from PIL import Image
from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
SMOKE_APP = """import streamlit as st
from st_graph_workbench import EdgeStyle, NodeStyle, graph_workbench

layout = st.selectbox("Layout", ["preset", "grid", "circle", "concentric",
    "breadthfirst", "random", "cose", "fcose", "dagre", "cola"])
graph_workbench(
    {"nodes": [
        {"data": {"id": "vehicle", "label": "VEHICLE", "name": "ABC123"},
         "position": {"x": 0, "y": 0}},
        {"data": {"id": "location", "label": "LOCATION", "name": "Camera 7"},
         "position": {"x": 180, "y": 100}}],
     "edges": [{"data": {"id": "sighting", "source": "vehicle",
         "target": "location", "label": "SEEN_AT"}}]},
    layout={"name": layout, "animate": False},
    node_styles=[NodeStyle("VEHICLE", "#2A629A", "name", "directions_car"),
                 NodeStyle("LOCATION", "#2D936C", "name", "place")],
    edge_styles=[EdgeStyle("SEEN_AT", "#2D936C", "label", directed=True)],
    return_selection=True, search=True, key="installed-smoke", height=650,
    show_selection_details=False,
    connected_drag={"enabled": False, "depth": 1, "max_depth": 3, "max_nodes": 20},
)
st.caption(f"Rendered layout: {layout}")
"""
TYPE_CHECK = """from typing_extensions import assert_type
from st_graph_workbench import (ConnectedDragConfig, GraphEvent,
    ProgressiveLoadConfig, ToolbarConfig, graph_workbench)
from st_graph_workbench import (Elements, ExpansionController, ExpansionRequest,
    ExpansionProvider, InMemoryExpansionProvider)

config: ProgressiveLoadConfig = {"page_size": 10, "acknowledged_request_id": "request-1"}
drag: ConnectedDragConfig = {"enabled": False, "depth": 1, "max_nodes": 20}
toolbar: ToolbarConfig = {"mode": "adaptive", "collapsible": True, "sticky": True}
assert_type(graph_workbench({"nodes": [], "edges": []}, progressive_loading=config),
            GraphEvent | None)
assert_type(graph_workbench({"nodes": [], "edges": []}, connected_drag=drag),
            GraphEvent | None)
assert_type(graph_workbench({"nodes": [], "edges": []}, toolbar=toolbar),
            GraphEvent | None)
seed: Elements = {"nodes": [{"data": {"id": "a"}}], "edges": []}
controller = ExpansionController(seed)
provider: ExpansionProvider = InMemoryExpansionProvider(seed)
assert_type(controller.request("a"), ExpansionRequest | None)
assert_type(controller.view(), Elements)
assert_type(graph_workbench(controller.view(), key="managed",
    expansion=controller.describe(provider), show_selection_details=False), GraphEvent | None)
"""


def run(args, *, cwd, env=None):
    print("Running:", " ".join(map(str, args)), flush=True)
    return subprocess.run(args, cwd=cwd, env=env, check=True)


def stop_server(process):
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            capture_output=True,
        )
    else:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def smoke_test(python, workdir, output, env):
    app = workdir / "app.py"
    app.write_text(SMOKE_APP, encoding="utf-8")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with (output / "streamlit.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                str(python),
                "-I",
                "-m",
                "streamlit",
                "run",
                str(app),
                "--server.port",
                str(port),
                "--server.address",
                "127.0.0.1",
                "--server.headless",
                "true",
                "--browser.gatherUsageStats",
                "false",
                "--server.fileWatcherType",
                "none",
            ],
            cwd=workdir,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 40
            while True:
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError(
                        "Installed smoke app did not start; see streamlit.log"
                    )
                try:
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/_stcore/health", timeout=1
                    ):
                        break
                except OSError:
                    time.sleep(0.25)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    page = browser.new_page(viewport={"width": 1440, "height": 1000})
                    errors = []
                    asset_errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on(
                        "response",
                        lambda response: (
                            asset_errors.append(response.url)
                            if "bidi-components" in response.url
                            and response.status >= 400
                            else None
                        ),
                    )
                    page.goto(f"http://127.0.0.1:{port}")
                    graph = page.locator("#container")
                    cy = graph.locator("#cy")
                    for layout in (
                        "preset",
                        "grid",
                        "circle",
                        "concentric",
                        "breadthfirst",
                        "random",
                        "cose",
                        "fcose",
                        "dagre",
                        "cola",
                    ):
                        print(f"Checking installed layout: {layout}", flush=True)
                        if layout != "preset":
                            page.get_by_role("combobox", name="Layout").click()
                            page.get_by_role("option", name=layout, exact=True).click()
                        expect(
                            page.get_by_text(f"Rendered layout: {layout}", exact=True)
                        ).to_be_visible(timeout=60000)
                        expect(graph).to_have_attribute(
                            "data-ready", "true", timeout=60000
                        )
                        expect(cy).to_be_visible()
                        assert cy.evaluate("""element => {
                            const cy = element._cyreg.cy;
                            return cy.nodes().length === 2 && cy.edges().length === 1 &&
                                cy.nodes().every(n => Number.isFinite(n.position('x')) &&
                                                     Number.isFinite(n.position('y')));
                        }""")
                    assert cy.evaluate("""element => element._cyreg.cy.nodes().every(
                        n => n.style('background-image').includes('icons/'))""")
                    expect(graph.locator("#selectionShowDetails")).not_to_be_checked()
                    cy.evaluate("el => el._cyreg.cy.getElementById('vehicle').select()")
                    expect(graph.locator("#selectionStatusCount")).to_have_text(
                        "1 node selected"
                    )
                    expect(graph.locator("#infopanel")).to_be_hidden()
                    graph.locator("#selectionControls summary").click()
                    connected_drag = graph.get_by_label(
                        "Move connected nodes", exact=True
                    )
                    expect(connected_drag).to_be_enabled(timeout=10000)
                    connected_drag.check()
                    expect(graph.locator("#connectedDragDepth")).to_be_enabled()
                    graph.get_by_label("Show selection details", exact=True).check()
                    graph.locator("#selectionControls summary").click()
                    expect(graph.locator("#infopanel")).to_be_visible()
                    graph.locator("#infopanelClear").click()
                    expect(graph.locator("#selectionStatusCount")).to_have_text(
                        "0 selected"
                    )
                    expect(graph.locator("#selectionShowDetails")).to_be_checked()
                    expect(graph.locator("#infopanel")).to_have_attribute(
                        "data-expanded", "false"
                    )
                    cy.evaluate("el => el._cyreg.cy.getElementById('vehicle').select()")
                    expect(graph.locator("#infopanel")).to_be_visible()
                    expect(page.get_by_test_id("stException")).to_have_count(0)
                    cy.screenshot(path=str(output / "installed-wheel.png"))
                    assert not errors, errors
                    assert not asset_errors, asset_errors
                    with Image.open(output / "installed-wheel.png") as screenshot:
                        colors = dict(
                            (color, count)
                            for count, color in screenshot.convert("RGB").getcolors(
                                screenshot.width * screenshot.height
                            )
                        )
                        assert colors.get((42, 98, 154), 0) > 20, (
                            "Vehicle node is not rendered"
                        )
                        assert colors.get((45, 147, 108), 0) > 20, (
                            "Location node is not rendered"
                        )
                finally:
                    browser.close()
        finally:
            stop_server(process)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / ".tmp/release-verification"
    )
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="graph-workbench-release-") as temporary:
        workdir = Path(temporary)
        dist = workdir / "dist"
        run(["uv", "build", "--out-dir", str(dist)], cwd=ROOT)
        wheel = next(dist.glob("*.whl"))
        sdist = next(dist.glob("*.tar.gz"))
        environment = workdir / "venv"
        run(["uv", "venv", str(environment), "--python", sys.executable], cwd=workdir)
        python = environment / (
            "Scripts/python.exe" if os.name == "nt" else "bin/python"
        )
        env = {
            key: value
            for key, value in os.environ.items()
            if key
            not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT"}
        }
        run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(python),
                str(wheel),
                "mypy",
                "twine",
            ],
            cwd=workdir,
            env=env,
        )
        run(
            [
                str(python),
                "-I",
                "-m",
                "twine",
                "check",
                "--strict",
                str(wheel),
                str(sdist),
            ],
            cwd=workdir,
            env=env,
        )
        run(
            [
                str(python),
                "-I",
                "-c",
                "import st_graph_workbench as package; from pathlib import Path; "
                f"assert Path(package.__file__).is_relative_to(Path({str(environment)!r})); "
                "print('Installed exports:', len(package.__all__))",
            ],
            cwd=workdir,
            env=env,
        )
        consumer = workdir / "consumer.py"
        consumer.write_text(TYPE_CHECK, encoding="utf-8")
        mypy = [
            str(python),
            "-I",
            "-m",
            "mypy",
            "--strict",
            "--no-incremental",
            "--follow-imports=silent",
            "--ignore-missing-imports",
            str(consumer),
        ]
        run(mypy, cwd=workdir, env=env)
        consumer.write_text(
            TYPE_CHECK.replace('"page_size": 10', '"page_size": "bad"'),
            encoding="utf-8",
        )
        bad_type = subprocess.run(
            mypy, cwd=workdir, env=env, capture_output=True, text=True
        )
        if bad_type.returncode != 1 or "typeddict-item" not in bad_type.stdout:
            raise RuntimeError(
                f"Installed type validation did not reject bad input: {bad_type.stdout}"
            )
        smoke_test(python, workdir, output, env)
        report = {
            "wheel": wheel.name,
            "sdist": sdist.name,
            "twine": "passed",
            "installed_typing": "passed",
            "browser_smoke": "passed",
            "layouts": 10,
        }
        (output / "report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
