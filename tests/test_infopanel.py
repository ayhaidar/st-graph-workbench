"""Selection details must have a readable, scrollable area inside the graph."""

import pytest
from playwright.sync_api import expect

from graph_test_helpers import get_component, get_cy, select_nodes, open_toolbox_menu


@pytest.mark.parametrize("route", ["learn_expansion", "branch_expansion"])
@pytest.mark.parametrize("width", [1440, 390])
def test_managed_selection_details_are_readable_and_scrollable(
    page, run_streamlit, tmp_path, route, width
):
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(f"http://localhost:{run_streamlit}/{route}")
    component = get_component(page)
    panel = component.locator("#infopanel")
    expect(panel).to_be_hidden()
    get_cy(component).evaluate("""el => {
        const node = el._cyreg.cy.getElementById('ABC123');
        node.data('reference', 'reference'.repeat(40));
        for (let i = 0; i < 8; i++) node.data(`detail_${i}`, `Record detail ${i}`);
    }""")
    select_nodes(component, ["ABC123"])
    expect(panel).to_be_visible()
    props = component.locator("#infopanelProps")
    page.wait_for_function("el => el.clientHeight >= 160", arg=props.element_handle())
    panel.scroll_into_view_if_needed()
    assert panel.bounding_box()["width"] >= 300
    assert props.evaluate("el => el.scrollWidth <= el.clientWidth + 1")
    assert panel.evaluate("""el => {
        const graph = el.closest('.st-graph-workbench');
        const panel = el.getBoundingClientRect();
        const bounds = graph.getBoundingClientRect();
        const topbar = graph.querySelector('.graph-topbar').getBoundingClientRect();
        const bottomBar = graph.querySelector('.managed-expansion-bar').getBoundingClientRect();
        const icon = el.querySelector('.infopanel__icon').getBoundingClientRect();
        const close = el.querySelector('.infopanel__close').getBoundingClientRect();
        return panel.left >= bounds.left && panel.right <= bounds.right
            && panel.top >= topbar.bottom && panel.bottom <= bottomBar.top
            && icon.right <= close.left;
    }""")
    component.screenshot(path=tmp_path / f"selection-details-{route}-{width}.png")
    zoom = get_cy(component).evaluate("el => el._cyreg.cy.zoom()")
    props.hover()
    page.mouse.wheel(0, 5000)
    page.wait_for_function(
        "el => el.scrollTop > 0 && el.scrollTop + el.clientHeight >= el.scrollHeight - 2",
        arg=props.element_handle(),
    )
    expect(props.locator(".infopanel__val").last).to_be_in_viewport()
    assert get_cy(component).evaluate("el => el._cyreg.cy.zoom()") == zoom
    component.locator("#infopanelClear").click()
    expect(panel).to_be_hidden()
    expect(component.locator("#selectionStatusCount")).to_have_text("0 selected")
    expect(component.get_by_label("Show selection details")).to_be_checked()
    select_nodes(component, ["ABC123"])
    expect(panel).to_be_visible()
    open_toolbox_menu(component, "selectionControls")
    component.get_by_label("Show selection details").uncheck()
    expect(panel).to_be_hidden()
    expect(component.locator("#selectionStatusCount")).to_have_text("1 node selected")
    component.get_by_label("Show selection details").check()
    expect(panel).to_be_visible()
    expect(component.locator("#selectionStatusCount")).to_have_text("1 node selected")
    component.locator("#selectionClear").click()
    expect(component.locator("#selectionStatusCount")).to_have_text("0 selected")
    expect(page.get_by_test_id("stException")).to_have_count(0)
