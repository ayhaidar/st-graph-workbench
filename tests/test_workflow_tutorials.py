"""Teach the difference between accepted Python records and immediate browser drafts."""

from io import BytesIO
import re

import pytest
from PIL import Image, ImageStat
from playwright.sync_api import Locator, expect

from graph_test_helpers import (
    get_component,
    get_cy,
    get_total_counts,
    drag_node,
    open_toolbox_menu,
    select_nodes,
    wait_for_app_idle,
    wait_for_cy_ready,
)


def open_lesson(page, port, slug):
    page.goto(f"http://localhost:{port}/learn_{slug}")
    component = get_component(page)
    wait_for_app_idle(page)
    return component


def open_crud_dialog(page, graph, button_id):
    # A completed Streamlit rerun gives the component its current trigger bridge.
    wait_for_app_idle(page)
    wait_for_cy_ready(graph)
    open_toolbox_menu(graph, "crudControls")
    button = graph.locator(f"#{button_id}")
    expect(button).to_be_visible(timeout=15000)
    expect(button).to_be_enabled(timeout=15000)
    button.scroll_into_view_if_needed()
    expect(button).to_be_attached()
    # Opening a native details menu is synchronous, but the component may have
    # just received new data. Do not click through an unfinished app rerun.
    wait_for_app_idle(page)
    button.click()
    dialog = page.get_by_role("dialog")
    # Attachment proves that Python received the CRUD intent and rendered the
    # dialog; visibility then verifies that it is ready for user interaction.
    expect(dialog).to_have_count(1, timeout=15000)
    expect(dialog).to_be_visible(timeout=15000)
    wait_for_app_idle(page)
    return dialog


def choose(page, label, value, *, within: Locator | None = None):
    scope = within if within is not None else page
    combobox = scope.get_by_role("combobox", name=label, exact=True)
    expect(combobox).to_be_visible()
    expect(combobox).to_be_enabled()
    combobox.scroll_into_view_if_needed()
    combobox.click()
    option = page.get_by_role("option", name=value, exact=True)
    expect(option).to_be_visible()
    option.click()


def confirm(page):
    dialog = page.get_by_role("dialog")
    dialog.get_by_role("button", name=re.compile("Confirm$")).click()
    expect(dialog).to_have_count(0)
    wait_for_app_idle(page)


def edit(page, component, button):
    open_toolbox_menu(component, "editControls")
    component.locator(f"#{button}").click()
    wait_for_app_idle(page)


def test_crud_accepts_each_node_and_relationship_type(page, run_streamlit):
    graph = open_lesson(page, run_streamlit, "crud")
    cy = get_cy(graph)
    cy.evaluate("el => el._cyreg.cy.scratch('workflow', true)")
    node_types = [
        "Location (PLACE)",
        "Vehicle (VEHICLE)",
        "Person (PERSON)",
        "Phone (PHONE)",
        "Camera (CAMERA)",
        "Time (TIME)",
        "Checkpoint (CHECKPOINT)",
    ]
    for index, choice in enumerate(node_types):
        dialog = open_crud_dialog(page, graph, "crudCreateNode")
        choose(page, "Node type", choice, within=dialog)
        dialog.get_by_role("textbox", name="Record ID", exact=True).fill(
            f"record-{index}"
        )
        dialog.get_by_role("textbox", name="Name", exact=True).fill(f"Record {index}")
        assert get_total_counts(graph) == {"nodes": 7 + index, "edges": 5}
        confirm(page)
        expect(
            page.get_by_text(
                f"Accepted records: {8 + index} nodes / 5 edges", exact=True
            )
        ).to_be_visible()
        assert (
            cy.evaluate(
                "(el, id) => el._cyreg.cy.getElementById(id).data('label')",
                f"record-{index}",
            )
            == choice.split("(")[1][:-1]
        )
        assert cy.evaluate(
            "(el, id) => el._cyreg.cy.getElementById(id).style('background-image').includes('icons/')",
            f"record-{index}",
        )
        assert cy.evaluate("el => el._cyreg.cy.scratch('workflow')")
    for index, label in enumerate(
        ["Seen At", "Registered To", "Uses", "Seen Near", "Related"]
    ):
        select_nodes(graph, ["ABC123", f"record-{index}"])
        dialog = open_crud_dialog(page, graph, "crudCreateEdge")
        expect(dialog.get_by_role("combobox", name="Source", exact=True)).to_have_value(
            "ABC123"
        )
        expect(dialog.get_by_role("combobox", name="Target", exact=True)).to_have_value(
            f"record-{index}"
        )
        choose(page, "Relationship type", label, within=dialog)
        choose(page, "Source", "ABC123", within=dialog)
        choose(page, "Target", f"record-{index}", within=dialog)
        dialog.get_by_role("textbox", name="Record ID", exact=True).fill(
            f"typed-edge-{index}"
        )
        confirm(page)
        expect(
            page.get_by_text(
                f"Accepted records: 14 nodes / {6 + index} edges", exact=True
            )
        ).to_be_visible()
        edge = cy.evaluate(
            "(el, id) => el._cyreg.cy.getElementById(id).data()", f"typed-edge-{index}"
        )
        assert (edge["label"], edge["source"], edge["target"]) == (
            label,
            "ABC123",
            f"record-{index}",
        )
        assert cy.evaluate("el => el._cyreg.cy.scratch('workflow')")
    dialog = open_crud_dialog(page, graph, "crudCreateNode")
    dialog.get_by_role("textbox", name="Record ID", exact=True).fill("ABC123")
    dialog.get_by_role("button", name=re.compile("Confirm$")).click()
    expect(
        page.get_by_text("Use a non-empty, unique record ID.", exact=True)
    ).to_be_visible()
    assert get_total_counts(graph) == {"nodes": 14, "edges": 10}
    page.get_by_role("dialog").get_by_role("button", name="Cancel", exact=True).click()
    expect(page.get_by_test_id("stException")).to_have_count(0)


def test_browser_drafts_and_reports_do_not_mutate_python_checkpoint(
    page, run_streamlit
):
    graph = open_lesson(page, run_streamlit, "editing")
    edit(page, graph, "editAddNode")
    expect(
        page.get_by_text("Browser report: 8 nodes / 5 edges", exact=True)
    ).to_be_visible()
    expect(
        page.get_by_text("Python records: 7 nodes / 5 edges", exact=True)
    ).to_be_visible()
    draft = get_cy(graph).evaluate("""el => {
        const n = el._cyreg.cy.getElementById('node-1');
        return {type:n.data('label'), name:n.data('name'), caption:n.style('label'),
            color:n.style('background-color'), icon:n.style('background-image')};
    }""")
    assert draft["type"] == "NODE" and draft["name"] == "node-1"
    assert draft["caption"] == "Draft node" and draft["color"] == "rgb(220,167,44)"
    assert "description.svg" in draft["icon"]
    select_nodes(graph, ["ABC123", "node-1"])
    expect(
        page.get_by_text("Browser report: 8 nodes / 5 edges", exact=True)
    ).to_be_visible()
    edit(page, graph, "editConnectSelected")
    expect(
        page.get_by_text("Browser report: 8 nodes / 6 edges", exact=True)
    ).to_be_visible()
    edit(page, graph, "editUndo")
    expect(
        page.get_by_text("Browser report: 8 nodes / 5 edges", exact=True)
    ).to_be_visible()
    edit(page, graph, "editRedo")
    expect(
        page.get_by_text("Browser report: 8 nodes / 6 edges", exact=True)
    ).to_be_visible()
    select_nodes(graph, ["node-1"])
    edit(page, graph, "editDeleteSelected")
    expect(
        page.get_by_text("Browser report: 7 nodes / 5 edges", exact=True)
    ).to_be_visible()
    expect(
        page.get_by_text("Python records: 7 nodes / 5 edges", exact=True)
    ).to_be_visible()
    page.get_by_role("link").filter(
        has_text="Compare with validated CRUD changes"
    ).click()
    expect(page).to_have_url(re.compile("/learn_crud$"))
    expect(
        page.get_by_text("Accepted records: 7 nodes / 5 edges", exact=True)
    ).to_be_visible()
    page.get_by_role("link").filter(
        has_text="Compare with immediate browser edits"
    ).click()
    expect(page).to_have_url(re.compile("/learn_editing$"))
    expect(page.get_by_test_id("stException")).to_have_count(0)


@pytest.mark.parametrize("slug", ["crud", "editing"])
@pytest.mark.parametrize("width", [1440, 390])
def test_workflow_lessons_have_readable_outputs(
    page, run_streamlit, tmp_path, slug, width
):
    page.set_viewport_size({"width": width, "height": 1000})
    graph = open_lesson(page, run_streamlit, slug)
    expect(
        page.get_by_role("heading", name="CRUD or browser editing?", exact=True)
    ).to_be_visible()
    if slug == "crud":
        dialog = open_crud_dialog(page, graph, "crudCreateNode")
        choose(page, "Node type", "Camera (CAMERA)", within=dialog)
        dialog.get_by_role("textbox", name="Record ID", exact=True).fill("camera-8")
        dialog.screenshot(path=tmp_path / f"crud-types-{width}.png")
        confirm(page)
        section = "Accepted Python records"
    else:
        edit(page, graph, "editAddNode")
        open_toolbox_menu(graph, "selectionControls")
        graph.get_by_label("Show selection details", exact=True).uncheck()
        graph.locator("#selectionControls summary").click()
        drag_node(page, graph, "node-1", dx=65, dy=90)
        section = "Python records and browser edit report"
    graph.screenshot(path=tmp_path / f"{slug}-graph-{width}.png")
    pixels = Image.open(BytesIO(get_cy(graph).screenshot())).convert("RGB")
    assert max(ImageStat.Stat(pixels).stddev) > 5
    heading = page.get_by_role("heading", name=section, exact=True)
    heading.evaluate("el => el.scrollIntoView({block:'start'})")
    page.evaluate("window.scrollBy(0, -70)")
    page.screenshot(path=tmp_path / f"{slug}-records-{width}.png")
    if slug == "editing":
        page.get_by_text("Latest browser edit", exact=True).evaluate(
            "el => el.scrollIntoView({block:'center'})"
        )
        page.screenshot(path=tmp_path / f"{slug}-browser-records-{width}.png")
    assert page.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth + 1"
    )
    for heading in page.get_by_role("heading").all():
        assert heading.evaluate("el => el.scrollWidth <= el.clientWidth + 1")
    expect(page.get_by_test_id("stException")).to_have_count(0)
