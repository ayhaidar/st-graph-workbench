"""Real browser coverage for the opt-in branch workflow and reliable delivery."""

import pytest
import re
import json
import time
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageStat
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, expect
from graph_test_helpers import (
    get_component,
    get_cy,
    get_node_ids,
    get_node_view,
    drag_node,
    open_toolbox_menu,
    select_nodes,
    click_node,
    wait_for_app_idle,
)


def open_managed(page, port):
    page.goto(f"http://localhost:{port}/learn_expansion")
    component = get_component(page)
    expect(component.locator("#managedExpansionBar")).to_be_visible()
    return component


def open_graph_search(component):
    search = component.locator("#searchPanel")
    if not search.is_visible():
        component.get_by_role("button", name="Open search controls").click()
    expect(search).to_be_visible()


def test_toolbar_collapse_control_stays_aligned_with_toolbox(page, run_streamlit):
    component = open_managed(page, run_streamlit)
    toolbox = component.locator("#toolbox").bounding_box()
    toolbar_chrome = component.locator("#toolbarChrome").bounding_box()

    assert toolbox is not None
    assert toolbar_chrome is not None
    assert toolbar_chrome["y"] == pytest.approx(toolbox["y"], abs=1)
    assert toolbar_chrome["x"] >= toolbox["x"] + toolbox["width"]


def action(component, node_id, operation):
    get_cy(component).evaluate(
        """(el, id) => {
        const cy = el._cyreg.cy;
        const node = cy.getElementById(id);
        node.emit({type:'cxttap', renderedPosition:node.renderedPosition()});
    }""",
        node_id,
    )
    menu = component.locator("#managedExpansionMenu")
    expect(menu).to_be_visible()
    menu.locator(f'[data-operation="{operation}"]').click()


def wait_nodes(component, expected):
    component.page.wait_for_function(
        """({el, ids}) => {
        const actual = el._cyreg.cy.nodes().map(n=>n.id()).sort();
        return JSON.stringify(actual) === JSON.stringify([...ids].sort());
    }""",
        arg={"el": get_cy(component).element_handle(), "ids": list(expected)},
    )


@pytest.mark.parametrize("entry", ["context_menu", "dialog"])
def test_managed_requests_work_on_non_localhost_http(http_page, run_streamlit, entry):
    page = http_page
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(f"http://workbench.test:{run_streamlit}/learn_expansion")
    component = get_component(page)
    assert page.evaluate(
        "!window.isSecureContext && typeof crypto.randomUUID === 'undefined'"
    )
    get_cy(component).evaluate("el => el._cyreg.cy.scratch('http', true)")
    # Repeating expand after collapse also checks that each action gets a fresh ID.
    for operation, nodes in [
        ("expand", {"ABC123", "location-1", "location-2"}),
        ("collapse", {"ABC123"}),
        ("expand", {"ABC123", "location-1", "location-2"}),
    ]:
        if entry == "context_menu":
            action(component, "ABC123", operation)
        else:
            select_nodes(component, ["ABC123"])
            component.get_by_role(
                "button", name="Explore connections", exact=True
            ).click()
            dialog = component.locator("#expansionDialog")
            dialog.locator(
                f'.expansion-dialog-actions [data-operation="{operation}"]'
            ).click()
            expect(dialog.locator(".expansion-error")).to_be_empty()
            expect(dialog).to_be_hidden()
        wait_nodes(component, nodes)
        wait_for_app_idle(page)
        assert get_cy(component).evaluate("el => el._cyreg.cy.scratch('http')")
    expect(page.get_by_test_id("stException")).to_have_count(0)
    assert not errors


def test_independent_shared_branches_and_reopening(page, run_streamlit):
    component = open_managed(page, run_streamlit)
    get_cy(component).evaluate("el => el._cyreg.cy.scratch('stable',true)")
    action(component, "ABC123", "expand")
    wait_nodes(component, {"ABC123", "location-1", "location-2"})
    for node_id in ("location-1", "location-2"):
        action(component, node_id, "expand")
        expect(
            component.locator(f'.expansion-badge[data-node-id="{node_id}"]')
        ).to_be_visible()
        action(component, node_id, "load_more")
    wait_nodes(
        component,
        {
            "ABC123",
            "location-1",
            "location-2",
            "camera-1",
            "camera-2",
            "shared",
            "time-0814",
            "AB123",
        },
    )
    action(component, "location-1", "collapse")
    wait_nodes(
        component, {"ABC123", "location-1", "location-2", "camera-2", "shared", "AB123"}
    )
    action(component, "location-1", "expand")
    assert get_cy(component).evaluate("el => el._cyreg.cy.scratch('stable')")
    page.wait_for_function(
        "el => el._cyreg.cy.getElementById('camera-1').length===1",
        arg=get_cy(component).element_handle(),
    )
    expect(page.get_by_test_id("stException")).to_have_count(0)


def test_bulk_completes_and_collapse_all_keeps_start(page, run_streamlit):
    component = open_managed(page, run_streamlit)
    page.get_by_role(
        "button", name=re.compile("Expand all within scope$")
    ).first.click()
    expect(component.locator("#managedExpansionBar")).to_contain_text(
        "complete", timeout=45000
    )
    assert len(get_node_ids(component)) >= 10
    page.get_by_role("button", name=re.compile("Collapse all$")).first.click()
    wait_nodes(component, {"ABC123"})


def test_positions_scopes_and_cached_search(page, run_streamlit):
    component = open_managed(page, run_streamlit)
    action(component, "ABC123", "expand")
    wait_nodes(component, {"ABC123", "location-1", "location-2"})
    moved = drag_node(page, component, "ABC123", dx=35, dy=20)
    action(component, "ABC123", "collapse")
    wait_nodes(component, {"ABC123"})
    assert get_node_view(component, "ABC123")["model"] == pytest.approx(
        moved["model"], abs=1
    )
    select_nodes(component, ["ABC123"])
    component.get_by_label("Analysis scope", exact=True).select_option("loaded")
    open_toolbox_menu(component, "analysisControls")
    component.locator("#analysisDegree").click()
    expect(page.get_by_test_id("stJson").first).to_contain_text(
        '"scope":"loaded"', timeout=10000
    )
    open_graph_search(component)
    component.locator("#graphSearchScope").select_option("loaded")
    component.locator("#graphSearchInput").fill("Location 1")
    component.locator("#graphSearchApply").click()
    expect(component.locator("#graphSearchResults")).to_have_value("location-1")
    component.locator("#graphSearchReveal").click()
    wait_nodes(component, {"ABC123", "location-1", "location-2"})


@pytest.mark.parametrize("scope", ["visible", "loaded"])
@pytest.mark.parametrize(
    "operation,selection",
    [
        ("ShortestPath", ["location-1", "location-2"]),
        ("Bfs", ["ABC123"]),
        ("Dfs", ["ABC123"]),
        ("Components", []),
        ("Degree", ["ABC123"]),
    ],
)
def test_all_analysis_scopes(page, run_streamlit, scope, operation, selection):
    component = open_managed(page, run_streamlit)
    action(component, "ABC123", "expand")
    wait_nodes(component, {"ABC123", "location-1", "location-2"})
    select_nodes(component, selection)
    component.get_by_label("Analysis scope", exact=True).select_option(scope)
    open_toolbox_menu(component, "analysisControls")
    component.locator(f"#analysis{operation}").click()
    output = page.get_by_test_id("stJson").first
    expect(output).to_contain_text(f'"scope":"{scope}"', timeout=15000)
    expect(output).to_contain_text('"node_count":3')
    expect(output).to_contain_text('"complete":true')
    if operation == "ShortestPath":
        expect(output).to_contain_text('"source_id":"location-1"')
        expect(output).to_contain_text('"distance":2')


def test_filtered_dialog_and_right_click_preserve_selection(page, run_streamlit):
    component = open_managed(page, run_streamlit)
    action(component, "ABC123", "expand")
    wait_nodes(component, {"ABC123", "location-1", "location-2"})
    select_nodes(component, ["location-1", "location-2"])
    click_node(component, "location-1", button="right")
    expect(component.locator("#managedExpansionMenu")).to_be_visible()
    assert get_cy(component).evaluate("el=>el._cyreg.cy.nodes(':selected').length") == 2
    component.locator("#managedExpansionMenu").get_by_role(
        "button", name="Explore connections..."
    ).click()
    dialog = component.locator("#expansionDialog")
    expect(dialog).to_be_visible()
    dialog.get_by_label("Direction", exact=True).select_option("outgoing")
    dialog.get_by_label("Exact-match attributes").fill('{"label":"DOCUMENT"}')
    dialog.locator('[data-operation="expand"]').click()
    wait_nodes(component, {"ABC123", "location-1", "location-2", "shared"})
    select_nodes(component, ["location-1"])
    action(component, "location-1", "collapse")
    wait_nodes(component, {"ABC123", "location-1", "location-2", "shared"})
    action(component, "location-2", "collapse")
    wait_nodes(component, {"ABC123", "location-1", "location-2"})


def test_collapse_all_returns_cleared_selection(page, run_streamlit):
    component = open_managed(page, run_streamlit)
    action(component, "ABC123", "expand")
    wait_nodes(component, {"ABC123", "location-1", "location-2"})
    select_nodes(component, ["location-1"])
    page.get_by_role("button", name=re.compile("Collapse all$")).first.click()
    wait_nodes(component, {"ABC123"})
    assert (
        get_cy(component).evaluate("el=>el._cyreg.cy.elements(':selected').length") == 0
    )
    expect(page.get_by_test_id("stJson").first).to_contain_text(
        '"selected_node_ids":[]', timeout=15000
    )


def test_dialog_closes_only_the_chosen_filtered_branch(page, run_streamlit):
    component = open_managed(page, run_streamlit)
    action(component, "ABC123", "expand")
    wait_nodes(component, {"ABC123", "location-1", "location-2"})
    select_nodes(component, ["ABC123"])
    component.get_by_role("button", name="Explore connections", exact=True).click()
    dialog = component.locator("#expansionDialog")
    dialog.get_by_label("Direction", exact=True).select_option("outgoing")
    dialog.locator('[data-operation="expand"]').click()
    component.get_by_role("button", name="Explore connections", exact=True).click()
    outgoing = dialog.locator(".expansion-branch-list > div").filter(
        has_text="ABC123 | outgoing"
    )
    expect(outgoing).to_contain_text("Open")
    outgoing.get_by_role("button", name="Collapse branch").click()
    expect(outgoing).to_contain_text("Cached")
    expect(
        dialog.locator(".expansion-branch-list > div").filter(has_text="ABC123 | both")
    ).to_contain_text("Open")
    dialog.get_by_role("button", name="Close", exact=True).click()
    wait_nodes(component, {"ABC123", "location-1", "location-2"})


def test_managed_instances_are_isolated(page, serve_streamlit):
    port = serve_streamlit(Path(__file__).parent / "apps" / "managed_expansion.py")
    page.goto(f"http://localhost:{port}")
    first, second = get_component(page, 0), get_component(page, 1)
    action(first, "root", "expand")
    wait_nodes(first, {"root", "child"})
    wait_nodes(second, {"root"})
    action(second, "root", "expand")
    wait_nodes(second, {"root", "child"})
    action(first, "root", "collapse")
    wait_nodes(first, {"root"})
    wait_nodes(second, {"root", "child"})


def test_edit_collapse_and_snapshot_restore(page, run_streamlit):
    component = open_managed(page, run_streamlit)
    action(component, "ABC123", "expand")
    wait_nodes(component, {"ABC123", "location-1", "location-2"})
    action(component, "location-1", "expand")
    page.wait_for_function(
        "el=>el._cyreg.cy.getElementById('camera-1').length===1",
        arg=get_cy(component).element_handle(),
    )
    wait_for_app_idle(page)
    section = page.get_by_test_id("stExpander").filter(
        has=page.locator("summary").get_by_text(
            "Edit cached records and save exploration", exact=True
        )
    )
    section.locator("summary").click()
    wait_for_app_idle(page)
    loaded_records = section.get_by_role("combobox", name="Loaded record")
    camera_option = page.get_by_role("option", name="camera-1", exact=True)
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            loaded_records.click(timeout=1000)
            if camera_option.is_visible():
                camera_option.click()
                break
        except PlaywrightTimeoutError:
            pass
        page.wait_for_timeout(250)
        wait_for_app_idle(page)
    else:
        raise AssertionError("camera-1 did not reach the loaded-record selector")
    section.get_by_role("button", name="Edit record", exact=True).click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_label("Display name").fill("Reviewed camera")
    dialog.get_by_role("button", name="Save record").click()
    expect(dialog).to_have_count(0)
    action(component, "location-1", "collapse")
    wait_nodes(component, {"ABC123", "location-1", "location-2"})
    action(component, "location-1", "expand")
    page.wait_for_function(
        "el=>el._cyreg.cy.getElementById('camera-1').data('name')==='Reviewed camera'",
        arg=get_cy(component).element_handle(),
    )
    open_toolbox_menu(component, "viewportControls")
    component.locator("#viewportSave").click()
    expect(page.get_by_test_id("stJson").first).to_contain_text(
        '"action":"viewport"', timeout=15000
    )
    wait_for_app_idle(page)
    with page.expect_download() as saved:
        section.get_by_role("button", name="Download exploration snapshot").click()
    snapshot = json.loads(Path(saved.value.path()).read_text(encoding="utf-8"))
    assert snapshot["viewport"]["zoom"] > 0
    page.get_by_role("button", name=re.compile("Collapse all$")).first.click()
    wait_nodes(component, {"ABC123"})
    section.locator('input[type="file"]').set_input_files(
        {
            "name": "exploration.json",
            "mimeType": "application/json",
            "buffer": json.dumps(snapshot).encode(),
        }
    )
    section.get_by_role("button", name="Restore snapshot", exact=True).click()
    wait_nodes(component, {"ABC123", "location-1", "location-2", "camera-1"})
    assert (
        get_cy(component).evaluate(
            "el=>el._cyreg.cy.getElementById('camera-1').data('name')"
        )
        == "Reviewed camera"
    )


@pytest.mark.parametrize("width,height", [(1440, 1000), (390, 844)])
def test_managed_graph_and_dialog_screenshots(
    page, run_streamlit, tmp_path, width, height
):
    page.set_viewport_size({"width": width, "height": height})
    component = open_managed(page, run_streamlit)
    image = component.screenshot(path=tmp_path / f"managed-{width}.png")
    assert max(ImageStat.Stat(Image.open(BytesIO(image)).convert("RGB")).var) > 20
    assert get_cy(component).evaluate("""el => {
        const cy = el._cyreg.cy, point = cy.getElementById('ABC123').renderedPosition();
        const rect = el.getBoundingClientRect();
        return el.contains(document.elementFromPoint(rect.left + point.x, rect.top + point.y));
    }""")
    component.get_by_role("button", name="Explore connections", exact=True).click()
    dialog = component.locator("#expansionDialog")
    expect(dialog).to_be_visible()
    box = dialog.bounding_box()
    assert 0 <= box["x"] and box["x"] + box["width"] <= width + 1
    assert 0 <= box["y"] and box["y"] + box["height"] <= height + 1
    dialog.screenshot(path=tmp_path / f"managed-dialog-{width}.png")
    assert dialog.evaluate("el=>el.scrollWidth<=el.clientWidth+1")


def test_source_search_reveals_real_context_and_analysis_stays_source_scoped(
    page, run_streamlit
):
    component = open_managed(page, run_streamlit)
    open_graph_search(component)
    component.locator("#graphSearchScope").select_option("source")
    component.locator("#graphSearchInput").fill("08:40")
    component.locator("#graphSearchApply").click()
    expect(component.locator("#graphSearchResults")).to_have_value(
        "time-0840", timeout=15000
    )
    component.locator("#graphSearchReveal").click()
    wait_nodes(component, {"ABC123", "location-1", "camera-1", "time-0840"})
    select_nodes(component, ["ABC123"])
    component.get_by_label("Analysis scope", exact=True).select_option("source")
    open_toolbox_menu(component, "analysisControls")
    component.locator("#analysisDegree").click()
    output = page.get_by_test_id("stJson").filter(has_text='"scope":"source"')
    expect(output.first).to_contain_text('"node_count":12', timeout=15000)
    expect(output.first).to_contain_text('"source_complete":true')
    open_toolbox_menu(component, "selectionControls")
    component.locator("#selectionClear").click()
    expect(component.locator("#selectionStatusCount")).to_have_text("0 selected")
    # A new selection reruns Python with the same source result; do not replay it.
    select_nodes(component, ["ABC123"])
    assert (
        get_cy(component).evaluate(
            "el => el._cyreg.cy.elements('.analysis-result').length"
        )
        == 0
    )
    open_toolbox_menu(component, "analysisControls")
    component.locator("#analysisDegree").click()
    page.wait_for_function(
        "el => el._cyreg.cy.nodes('.analysis-result').length > 0",
        arg=get_cy(component).element_handle(),
    )
    open_toolbox_menu(component, "analysisControls")
    component.locator("#analysisBfs").click()
    expect(component.locator("#managedExpansionBar")).to_contain_text(
        "supports source degree only", timeout=15000
    )


def test_restore_hidden_does_not_reopen_closed_branches(page, run_streamlit):
    component = open_managed(page, run_streamlit)
    action(component, "ABC123", "expand")
    wait_nodes(component, {"ABC123", "location-1", "location-2"})
    action(component, "location-1", "expand")
    page.wait_for_function(
        "el=>el._cyreg.cy.getElementById('camera-1').length===1",
        arg=get_cy(component).element_handle(),
    )
    action(component, "location-1", "collapse")
    wait_nodes(component, {"ABC123", "location-1", "location-2"})
    select_nodes(component, ["ABC123"])
    open_toolbox_menu(component, "selectionControls")
    component.locator("#selectionHideUnselected").click()
    wait_nodes(component, {"ABC123"})
    open_toolbox_menu(component, "selectionControls")
    component.locator("#selectionRestore").click()
    wait_nodes(component, {"ABC123", "location-1", "location-2"})
