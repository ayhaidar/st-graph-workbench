from playwright.sync_api import Page, expect
import json
from graph_test_helpers import (
    IFRAME_LOCATOR,
    emit_cytoscape_event,
    get_component,
    get_cy,
    select_element,
    wait_for_info_panel_selection,
)


PAGE_NAME = "Event Listeners"
NODE_ID = "ABC123"
EDGE_ID = "ABC123-Person_MReed"


def AWAIT_RETURN_ACTION(page):
    page.get_by_text('"action":"').click()


def get_return_json(page: Page):
    data = (
        page.get_by_test_id("stJson")
        .last.text_content()
        .replace('""', '","')
        .replace('}"', '},"')
    )
    return json.loads(data)


def wait_for_return_action(page: Page, action: str) -> None:
    expect(page.get_by_test_id("stJson").last).to_contain_text(
        f'"action":"{action}"',
        timeout=10000,
    )


def test_component_renders_without_v1_iframe(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")
    get_component(page)
    expect(page.locator(IFRAME_LOCATOR)).to_have_count(0)


def test_single_click_node_event(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    component = get_component(page)
    component.click(position={"x": 0, "y": 0})  # await and scroll to view

    emit_cytoscape_event(component, NODE_ID, "click")
    AWAIT_RETURN_ACTION(page)
    data = get_return_json(page)

    assert data["data"]["target_id"] == NODE_ID
    assert data["data"]["target_group"] == "nodes"
    assert data["action"] == "clicked_node"


def test_double_click_edge_event(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    component = get_component(page)
    component.click(position={"x": 0, "y": 0})  # await and scroll to view

    emit_cytoscape_event(component, EDGE_ID, "dblclick")
    AWAIT_RETURN_ACTION(page)
    data = get_return_json(page)

    assert data["data"]["target_id"] == EDGE_ID
    assert data["data"]["target_group"] == "edges"
    assert data["action"] == "double_clicked_anything"


def test_single_click_edge_no_event(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    component = get_component(page)
    component.click(position={"x": 0, "y": 0})  # await and scroll to view

    select_element(component, EDGE_ID)
    emit_cytoscape_event(component, EDGE_ID, "click")
    wait_for_info_panel_selection(component)
    AWAIT_RETURN_ACTION(page)

    returned = page.get_by_test_id("stJson").last
    expect(returned).to_contain_text("selection")
    expect(returned).to_contain_text(EDGE_ID)


def test_event_listeners_update_without_remount(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")
    component = get_component(page)

    get_cy(component).evaluate(
        """(element) => {
            element._cyreg.cy.__listenerSyncProbe = "same-instance";
        }"""
    )
    emit_cytoscape_event(component, "Person_MReed", "click")
    wait_for_return_action(page, "clicked_node")

    page.get_by_text("High-priority selector", exact=True).click()
    expect(page.get_by_test_id("stJson").first).to_contain_text(
        "main_vehicle_click",
        timeout=10000,
    )
    component = get_component(page)
    assert (
        get_cy(component).evaluate(
            """(element) => element._cyreg.cy.__listenerSyncProbe"""
        )
        == "same-instance"
    )

    returned_value = page.get_by_test_id("stJson").last
    unchanged_text = returned_value.text_content()
    emit_cytoscape_event(component, "Person_MReed", "click")
    page.wait_for_timeout(700)
    assert returned_value.text_content() == unchanged_text

    emit_cytoscape_event(component, NODE_ID, "click")
    wait_for_return_action(page, "main_vehicle_click")

    page.get_by_text("Node and edge", exact=True).click()
    expect(page.get_by_test_id("stJson").first).to_contain_text(
        "edge_click",
        timeout=10000,
    )
    component = get_component(page)
    assert (
        get_cy(component).evaluate(
            """(element) => element._cyreg.cy.__listenerSyncProbe"""
        )
        == "same-instance"
    )

    emit_cytoscape_event(component, EDGE_ID, "click")
    wait_for_return_action(page, "edge_click")
