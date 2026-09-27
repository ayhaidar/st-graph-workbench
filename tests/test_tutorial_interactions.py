"""End-to-end examples of the stateful workflows taught by the curriculum."""

from io import BytesIO
import json
import re

import pytest
from PIL import Image, ImageStat
from playwright.sync_api import expect

from graph_test_helpers import (
    click_node,
    drag_node,
    get_badge,
    get_component,
    get_cy,
    get_node_view,
    get_total_counts,
    open_context_menu_for_node,
    open_toolbox_menu,
    select_nodes,
    wait_for_node_ids,
    wait_for_app_idle as idle,
)


def open_lesson(page, port, slug):
    page.goto(f"http://localhost:{port}/learn_{slug}")
    component = get_component(page)
    idle(page)
    return component


def choose(page, label, value):
    idle(page)
    control = page.get_by_role("combobox", name=label, exact=True)
    control.evaluate("el => el.scrollIntoView({block: 'center'})")
    control.click()
    page.get_by_role("option", name=value, exact=True).click()
    expect(control).to_have_value(value)
    idle(page)


def counts(page, nodes, edges):
    page.wait_for_function(
        """expected => {
        const cy = document.querySelector('#cy')?._cyreg?.cy;
        return cy && cy.nodes().length === expected.nodes && cy.edges().length === expected.edges;
    }""",
        arg={"nodes": nodes, "edges": edges},
    )


def test_crud_node_then_edge_and_cancel(page, run_streamlit):
    component = open_lesson(page, run_streamlit, "crud")
    get_cy(component).evaluate("el => el._cyreg.cy.scratch('tutorialTest', true)")
    open_toolbox_menu(component, "crudControls")
    component.locator("#crudCreateNode").click()
    dialog = page.get_by_role("dialog")
    expect(dialog).to_be_visible()
    dialog.get_by_role("button", name="Cancel", exact=True).click()
    expect(dialog).to_have_count(0)
    idle(page)
    counts(page, 7, 5)
    open_toolbox_menu(component, "crudControls")
    component.locator("#crudCreateNode").click()
    dialog.get_by_role("textbox", name="Record ID", exact=True).fill("added-node")
    dialog.get_by_role("button", name=re.compile("Confirm$")).click()
    counts(page, 8, 5)
    idle(page)
    assert get_cy(component).evaluate("el => el._cyreg.cy.scratch('tutorialTest')")
    select_nodes(component, ["ABC123", "added-node"])
    open_toolbox_menu(component, "crudControls")
    component.locator("#crudCreateEdge").click()
    expect(dialog).to_be_visible()
    dialog.get_by_role("button", name=re.compile("Confirm$")).click()
    counts(page, 8, 6)
    assert get_cy(component).evaluate("el => el._cyreg.cy.scratch('tutorialTest')")
    expect(page.get_by_test_id("stException")).to_have_count(0)


def test_expansion_drag_counts_and_collapse(page, run_streamlit):
    component = open_lesson(page, run_streamlit, "expansion")
    expect(get_badge(component, "ABC123")).to_have_text("+2n/2e")
    expect(component.locator(".expansion-badge")).to_have_count(1)
    get_cy(component).evaluate("el => el._cyreg.cy.scratch('tutorialTest', true)")
    drag_node(page, component, "ABC123", dx=45, dy=25)
    menu = open_context_menu_for_node(component, "ABC123")
    idle(page)
    moved = get_node_view(component, "ABC123")
    menu.locator('[data-operation="expand"]').click()
    wait_for_node_ids(component, ["ABC123", "location-1", "location-2"])
    expect(get_badge(component, "ABC123")).to_have_text("-2n/2e")
    after = get_node_view(component, "ABC123")
    assert after["model"] == pytest.approx(moved["model"], abs=1)
    assert get_cy(component).evaluate("el => el._cyreg.cy.scratch('tutorialTest')")
    open_context_menu_for_node(component, "ABC123").locator(
        '[data-operation="collapse"]'
    ).click()
    wait_for_node_ids(component, ["ABC123"])
    expect(get_badge(component, "ABC123")).to_have_text("+2n/2e")


@pytest.mark.parametrize(
    "title,button,selected,expected",
    [
        ("Shortest path", "analysisShortestPath", ["ALPHA", "BETA"], "distance"),
        ("Breadth-first search", "analysisBfs", ["ABC123"], "root_id"),
        ("Depth-first search", "analysisDfs", ["ABC123"], "root_id"),
        ("Connected components", "analysisComponents", [], "components"),
        ("Degree", "analysisDegree", ["ABC123"], "indegree"),
    ],
)
def test_analysis_scenarios_return_results(
    page, run_streamlit, title, button, selected, expected
):
    component = open_lesson(page, run_streamlit, "analysis")
    choose(page, "Analysis scenario", title)
    select_nodes(component, selected)
    open_toolbox_menu(component, "analysisControls")
    component.locator(f"#{button}").click()
    actual = page.get_by_test_id("stJson").first
    expect(actual).to_contain_text("timestamp", timeout=15000)
    expect(actual).to_contain_text(expected)


def test_loading_failure_retry_completion_and_restart(page, run_streamlit):
    component = open_lesson(page, run_streamlit, "loading")
    get_cy(component).evaluate(
        "el => { const cy=el._cyreg.cy; cy.scratch('tutorialTest',true); cy.pan({x:30,y:40}); }"
    )
    before = get_cy(component).evaluate("el => el._cyreg.cy.pan()")
    choose(page, "Next response", "Fail once")
    page.get_by_role("button", name=re.compile("Arm next response$")).click()
    idle(page)
    button = component.locator("#progressiveLoadingButton")
    button.click()
    expect(
        page.get_by_text(
            "Simulated data-source failure. Retry the same cursor.", exact=True
        )
    ).to_be_visible()
    expect(button).to_be_enabled()
    counts(page, 33, 30)
    button.click()
    expect(component.locator("#progressiveLoadingStatus")).to_have_text("60 / 180")
    for count in range(90, 181, 30):
        button.click()
        expect(component.locator("#progressiveLoadingStatus")).to_have_text(
            f"{count} / 180", timeout=15000
        )
    counts(page, 183, 180)
    expect(button).to_be_disabled()
    assert get_cy(component).evaluate("el => el._cyreg.cy.pan()") == pytest.approx(
        before
    )
    page.get_by_role("button", name=re.compile("Restart loading$")).click()
    counts(page, 33, 30)
    expect(button).to_be_enabled()
    assert get_cy(component).evaluate("el => el._cyreg.cy.scratch('tutorialTest')")


def test_exports_and_position_restore(page, run_streamlit):
    component = open_lesson(page, run_streamlit, "exports")
    page.get_by_role("button", name=re.compile("Save positions$")).click()
    idle(page)
    original = get_node_view(component, "ABC123")["model"]
    moved = drag_node(page, component, "ABC123", dx=50, dy=30)
    assert moved["model"] != pytest.approx(original, abs=1)

    # The drag returns positions to Python and reruns Streamlit. Wait for that
    # update before clicking a Python widget that could otherwise be replaced.
    idle(page)
    component = get_component(page)
    restore = page.get_by_role("button", name=re.compile("Restore positions$"))
    expect(restore).to_be_enabled(timeout=15000)
    restore.click()
    idle(page)

    component = get_component(page)
    cy_element = get_cy(component).element_handle()
    assert cy_element is not None
    page.wait_for_function(
        """payload => {
        const cy = payload.element._cyreg?.cy;
        const actual = cy?.getElementById('ABC123').position();
        return actual && Math.abs(actual.x-payload.position.x)<1
            && Math.abs(actual.y-payload.position.y)<1;
    }""",
        arg={"element": cy_element, "position": original},
    )
    select_nodes(component, ["ABC123"])
    for selector, suffix in [
        ("toolbarExport", ".json"),
        ("toolbarExportFull", ".json"),
        ("toolbarExportSelected", ".json"),
        ("toolbarExportPositions", ".json"),
        ("toolbarExportPng", ".png"),
        ("toolbarExportJpg", ".jpg"),
    ]:
        open_toolbox_menu(component, "toolbar")
        with page.expect_download() as received:
            component.locator(f"#{selector}").click()
        download = received.value
        assert download.suggested_filename.endswith(suffix)
        if suffix == ".json":
            with open(download.path(), encoding="utf-8") as file:
                assert json.load(file)


def test_custom_events_and_options_stay_with_their_instance(page, run_streamlit):
    first = open_lesson(page, run_streamlit, "events")
    second = get_component(page, 1)
    get_cy(second).evaluate("el => el._cyreg.cy.scratch('secondInstance', true)")
    click_node(first, "ABC123")
    expect(first.locator("#selectionStatusCount")).to_have_text("1 node selected")
    expect(second.locator("#selectionStatusCount")).to_have_text("0 selected")
    click_node(second, "ALPHA")
    expect(second.locator("#selectionStatusCount")).to_have_text("1 node selected")
    expect(first.locator("#selectionStatusCount")).to_have_text("1 node selected")
    idle(page)
    page.get_by_text("Search on the first graph", exact=True).click()
    idle(page)
    assert get_cy(second).evaluate("el => el._cyreg.cy.scratch('secondInstance')")
    expect(second.locator("#selectionStatusCount")).to_have_text("1 node selected")
    expect(page.get_by_test_id("stException")).to_have_count(0)


@pytest.mark.parametrize("width,height", [(1440, 1000), (390, 844)])
def test_tutorial_layout_and_nonblank_canvas(
    page, run_streamlit, tmp_path, width, height
):
    page.set_viewport_size({"width": width, "height": height})
    component = open_lesson(page, run_streamlit, "style_graph")
    page.screenshot(path=str(tmp_path / f"tutorial-{width}-page.png"), full_page=True)
    png = component.screenshot(path=str(tmp_path / f"tutorial-{width}-graph.png"))
    assert get_cy(component).evaluate("""el => {
        const cy = el._cyreg.cy, rect = el.getBoundingClientRect();
        return cy.nodes().every(node => {
            const point = node.renderedPosition();
            const hit = document.elementFromPoint(rect.x + point.x, rect.y + point.y);
            return hit?.tagName === 'CANVAS';
        });
    }"""), "Every node must be visible below the toolbar, including on mobile."
    with Image.open(BytesIO(png)) as image:
        assert max(ImageStat.Stat(image.convert("RGB")).stddev) > 10
    assert get_total_counts(component)["nodes"] == 7
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    expect(page.get_by_test_id("stException")).to_have_count(0)
