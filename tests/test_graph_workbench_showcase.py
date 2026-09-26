from playwright.sync_api import Page, expect

from graph_test_helpers import (
    IFRAME_LOCATOR,
    click_nav,
    get_badge,
    get_component,
    get_node_ids,
    open_toolbox_menu,
    select_nodes,
    wait_for_node,
)


PAGE_NAME = "Graph Workbench Showcase"


def test_showcase_exposes_workbench_controls(page: Page):
    click_nav(page, PAGE_NAME)
    page.wait_for_load_state("networkidle")
    component = get_component(page)

    expect(page.locator(IFRAME_LOCATOR)).to_have_count(0)
    expect(component.locator("#searchPanel")).to_be_visible()
    expect(component.locator("#toolbox")).to_be_visible()
    expect(component.locator("#selectionStatus")).to_be_visible()
    expect(component.locator("#crudControls > summary")).to_be_visible()
    expect(component.locator("#analysisControls > summary")).to_be_visible()
    expect(component.locator("#toolbar > summary")).to_be_visible()
    expect(get_badge(component, "vehicle")).to_have_text("+2")


def test_showcase_expands_and_loads_related_data(page: Page):
    click_nav(page, PAGE_NAME)
    page.wait_for_load_state("networkidle")
    component = get_component(page)

    select_nodes(component, ["vehicle"])
    component.locator("#nodeActionsExpand").click()
    expect(get_badge(component, "vehicle")).to_have_text("-2", timeout=10000)
    assert "checkpoint" in get_node_ids(component)
    assert "time_window" in get_node_ids(component)

    open_toolbox_menu(component, "crudControls")
    component.locator("#crudRequestNodeData").click()
    wait_for_node(component, "document")
    expect(page.get_by_text("Loaded 1 related node(s)").first).to_be_visible()
