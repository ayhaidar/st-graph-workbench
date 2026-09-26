import json
import time

from playwright.sync_api import Page, expect

from graph_test_helpers import (
    get_component,
    get_cy,
    get_visible_counts,
    open_toolbox_menu,
    select_nodes,
    wait_for_edge_ids,
    wait_for_node_ids,
)

PAGE_NAME = "Interactive CRUD / Data Loading"
DIALOG_LOCATOR = "[role='dialog']"


def get_node_data(component, node_id):
    return get_cy(component).evaluate(
        """(element, nodeId) => {
            const cy = element._cyreg.cy;
            return cy.getElementById(nodeId).data();
        }""",
        node_id,
    )


def get_dialog(page: Page, title: str):
    dialog = page.locator(DIALOG_LOCATOR).filter(has_text=title).first
    expect(dialog).to_be_visible(timeout=10000)
    return dialog


def expect_no_dialog(page: Page):
    expect(page.locator(DIALOG_LOCATOR)).to_have_count(0, timeout=10000)


def open_stats_dialog(component):
    component.locator("#graphStatsButton").click()
    expect(component.locator("#graphStatsDialog")).to_be_visible()


def expect_stats_match_graph(component):
    counts = get_visible_counts(component)
    open_stats_dialog(component)
    expect(component.locator("#graphStatsShownNodes")).to_have_text(
        str(counts["shownNodes"])
    )
    expect(component.locator("#graphStatsHiddenNodes")).to_have_text(
        str(counts["hiddenNodes"])
    )
    expect(component.locator("#graphStatsTotalNodes")).to_have_text(
        str(counts["totalNodes"])
    )
    expect(component.locator("#graphStatsShownEdges")).to_have_text(
        str(counts["shownEdges"])
    )
    expect(component.locator("#graphStatsHiddenEdges")).to_have_text(
        str(counts["hiddenEdges"])
    )
    expect(component.locator("#graphStatsTotalEdges")).to_have_text(
        str(counts["totalEdges"])
    )
    component.locator("#graphStatsClose").click()
    expect(component.locator("#graphStatsDialog")).to_be_hidden()


def test_crud_toolbox_hidden_when_not_configured(page: Page):
    page.get_by_role("link", name="Node Actions").click()
    page.wait_for_load_state("networkidle")
    component = get_component(page)

    expect(component.locator("#crudControls")).to_be_hidden()


def test_crud_toolbox_button_states(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")
    component = get_component(page)
    expect(component).to_have_attribute("data-elements-sync", "elements")
    open_toolbox_menu(component, "crudControls")

    expect(component.locator("#crudControls")).to_be_visible()
    expect(component.locator("#crudCreateNode")).to_be_enabled()
    for button_id in [
        "crudCreateEdge",
        "crudReadSelected",
        "crudUpdateSelected",
        "crudDeleteSelected",
        "crudRequestNodeData",
    ]:
        expect(component.locator(f"#{button_id}")).to_be_disabled()

    select_nodes(component, ["vehicle"])
    expect(component.locator("#crudCreateEdge")).to_be_enabled()
    expect(component.locator("#crudReadSelected")).to_be_enabled()
    expect(component.locator("#crudUpdateSelected")).to_be_enabled()
    expect(component.locator("#crudDeleteSelected")).to_be_enabled()
    expect(component.locator("#crudRequestNodeData")).to_be_enabled()


def test_read_selected_and_load_related_data(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")
    component = get_component(page)
    open_toolbox_menu(component, "crudControls")
    select_nodes(component, ["vehicle"])

    expect(component.locator("#crudReadSelected")).to_be_enabled()
    component.locator("#crudReadSelected").click()
    read_dialog = get_dialog(page, "Read selected")
    expect(read_dialog).to_contain_text("selected_elements")
    expect(read_dialog).to_contain_text("connected_node_ids")
    expect(read_dialog).to_contain_text("connected_edge_ids")
    expect(read_dialog).to_contain_text("connected_elements")
    expect(read_dialog).to_contain_text("vehicle-maya")
    read_dialog.locator("button").filter(has_text="Close").click()
    expect_no_dialog(page)

    open_toolbox_menu(component, "crudControls")
    expect(component.locator("#crudRequestNodeData")).to_be_enabled()
    component.locator("#crudRequestNodeData").click()
    load_dialog = get_dialog(page, "Load related data")
    expect(load_dialog).to_contain_text("Load related demo data")
    load_dialog.get_by_role("button", name="Load related data").click()
    wait_for_node_ids(
        component, ["case", "checkpoint", "maya", "time_window", "vehicle"]
    )
    wait_for_edge_ids(
        component,
        ["case-vehicle", "vehicle-checkpoint", "vehicle-maya", "vehicle-time"],
    )
    expect(component).to_have_attribute("data-elements-sync", "commands")
    expect(page.get_by_text("Loaded 2 node(s) and 2 edge(s)")).to_be_visible()
    expect_no_dialog(page)


def test_create_update_and_delete_with_python_forms(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")
    component = get_component(page)
    open_toolbox_menu(component, "crudControls")

    component.locator("#crudCreateNode").click()
    create_node = get_dialog(page, "Add node")
    create_node.get_by_label("Node ID").fill("analyst")
    create_node.get_by_label("Label").click()
    page.get_by_role("option", name="PERSON").click()
    create_node.get_by_label("Name").fill("Analyst One")
    create_node.get_by_role("button", name="Create node").click()
    wait_for_node_ids(component, ["analyst", "case", "maya", "vehicle"])
    wait_for_edge_ids(component, ["case-vehicle", "vehicle-maya"])
    expect(component).to_have_attribute("data-elements-sync", "commands")
    expect(component.locator("#graphStatsButton")).to_contain_text("4")
    expect_stats_match_graph(component)
    expect_no_dialog(page)

    open_toolbox_menu(component, "crudControls")
    select_nodes(component, ["vehicle"])
    component.locator("#crudCreateEdge").click()
    create_edge = get_dialog(page, "Add edge")
    create_edge.get_by_label("Edge ID").fill("vehicle-analyst")
    create_edge.get_by_label("Label").fill("RELATED_TO")
    create_edge.get_by_label("Target").click()
    page.get_by_role("option").filter(has_text="analyst").click()
    create_edge.get_by_role("button", name="Create edge").click()
    wait_for_edge_ids(component, ["case-vehicle", "vehicle-analyst", "vehicle-maya"])
    expect_no_dialog(page)

    open_toolbox_menu(component, "crudControls")
    select_nodes(component, ["vehicle"])
    component.locator("#crudUpdateSelected").click()
    update_dialog = get_dialog(page, "Update selected")
    update_dialog.get_by_label("Element data JSON").fill(
        json.dumps(
            {
                "id": "vehicle",
                "label": "MAIN_VEHICLE",
                "name": "ABC123 Updated",
                "risk": 10,
            },
            indent=2,
        )
    )
    update_dialog.get_by_role("button", name="Update element").click()
    deadline = time.time() + 5
    while time.time() < deadline:
        if get_node_data(component, "vehicle").get("name") == "ABC123 Updated":
            break
        time.sleep(0.1)
    assert get_node_data(component, "vehicle")["name"] == "ABC123 Updated"
    expect_no_dialog(page)

    open_toolbox_menu(component, "crudControls")
    select_nodes(component, ["analyst"])
    component.locator("#crudDeleteSelected").click()
    delete_dialog = get_dialog(page, "Delete selected")
    expect(delete_dialog).to_contain_text("analyst")
    wait_for_node_ids(component, ["analyst", "case", "maya", "vehicle"])
    delete_dialog.get_by_role("button", name="Confirm delete selected elements").click()
    wait_for_node_ids(component, ["case", "maya", "vehicle"])
    wait_for_edge_ids(component, ["case-vehicle", "vehicle-maya"])
    expect_no_dialog(page)
