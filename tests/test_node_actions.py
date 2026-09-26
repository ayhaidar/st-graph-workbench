from playwright.sync_api import Page, expect

from graph_test_helpers import (
    IFRAME_LOCATOR,
    click_node,
    drag_node,
    double_click_node,
    get_badge,
    get_component,
    get_cy,
    get_node_view,
    open_context_menu_for_node,
    open_toolbox_menu,
    select_node,
    wait_for_info_panel_selection,
    wait_for_node_ids,
)

PAGE_NAME = "Node Actions"
NODE_ID = "ABC123"
INITIAL_NODE_IDS = [
    "12VEC",
    "ABC123",
    "ALPHA",
    "BETA",
    "location_1",
    "location_2",
    "location_3",
]
EXPANDED_NODE_IDS = sorted([*INITIAL_NODE_IDS, "Person_MReed", "Phone_0412"])


def get_toolbox_button(component, button_id):
    return component.locator(f"#{button_id}")


def test_component_renders_without_v1_iframe(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")
    get_component(page)
    expect(page.locator(IFRAME_LOCATOR)).to_have_count(0)


def test_toolbox_groups_controls_and_disables_node_actions(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    component = get_component(page)
    component.click(position={"x": 0, "y": 0})  # await and scroll to view

    expect(component.locator("#toolbox")).to_be_visible()
    expect(component.locator("#selectionStatus")).to_be_visible()
    expect(component.locator("#selectionStatusMode")).to_have_text("Multiple")
    expect(component.locator("#selectionStatusCount")).to_have_text("0 selected")
    expect(component.locator(".bar")).to_have_count(0)
    for button_id in [
        "nodeActionsRemove",
        "nodeActionsExpand",
        "viewbarPlus",
        "viewbarMinus",
        "viewbarFit",
        "viewbarCenter",
        "toolbarRefresh",
        "toolbarFullscreen",
        "expansionBadgeToggle",
    ]:
        expect(get_toolbox_button(component, button_id)).to_be_visible()
    expect(component.locator("#toolbar > summary")).to_be_visible()
    open_toolbox_menu(component, "toolbar")
    expect(get_toolbox_button(component, "toolbarExport")).to_be_visible()

    expect(get_toolbox_button(component, "nodeActionsRemove")).to_be_disabled()
    expect(get_toolbox_button(component, "nodeActionsExpand")).to_be_disabled()
    expect(get_toolbox_button(component, "expansionBadgeToggle")).to_have_attribute(
        "aria-pressed", "true"
    )


def test_expand_dblclick(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    component = get_component(page)
    component.click(position={"x": 0, "y": 0})  # await and scroll to view

    select_node(component, NODE_ID)
    double_click_node(component, NODE_ID)
    wait_for_node_ids(component, EXPANDED_NODE_IDS)
    returned = page.get_by_test_id("stJson").first
    expect(returned).to_contain_text("expand", timeout=10000)
    expect(returned).to_contain_text(NODE_ID)


def test_expand_button(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    component = get_component(page)
    component.click(position={"x": 0, "y": 0})  # await and scroll to view

    select_node(component, NODE_ID)
    expand = get_toolbox_button(component, "nodeActionsExpand")
    expect(expand).to_have_attribute("title", "Expand Node")
    expand.click()
    wait_for_node_ids(component, EXPANDED_NODE_IDS)
    expect(get_badge(component, NODE_ID)).to_have_text("-2")


def test_expand_context_menu(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    component = get_component(page)
    component.click(position={"x": 0, "y": 0})  # await and scroll to view

    wait_for_node_ids(component, INITIAL_NODE_IDS)
    menu = open_context_menu_for_node(component, NODE_ID)
    expand = menu.locator("#graphContextMenuExpand")
    expect(expand).to_have_text("Expand node")
    expand.click()
    wait_for_node_ids(component, EXPANDED_NODE_IDS)

    menu = open_context_menu_for_node(component, NODE_ID)
    collapse = menu.locator("#graphContextMenuExpand")
    expect(collapse).to_have_text("Collapse node")
    collapse.click()
    wait_for_node_ids(component, INITIAL_NODE_IDS)


def test_real_mouse_drag_updates_positions_without_panning(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    component = get_component(page)
    component.click(position={"x": 0, "y": 0})  # await and scroll to view

    before = get_node_view(component, NODE_ID)
    after = drag_node(page, component, NODE_ID, dx=70, dy=45)

    expect(page.get_by_test_id("stJson").first).to_contain_text(
        "positions",
        timeout=10000,
    )
    expect(page.get_by_test_id("stJson").first).to_contain_text(NODE_ID)
    assert after["selected"] is True
    assert after["model"]["x"] > before["model"]["x"] + 30
    assert after["model"]["y"] > before["model"]["y"] + 20
    assert abs(after["pan"]["x"] - before["pan"]["x"]) < 1
    assert abs(after["pan"]["y"] - before["pan"]["y"]) < 1


def test_expand_action_can_collapse_rendered_nodes(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    component = get_component(page)
    component.click(position={"x": 0, "y": 0})  # await and scroll to view

    wait_for_node_ids(component, INITIAL_NODE_IDS)
    expect(get_badge(component, NODE_ID)).to_have_text("+2")
    select_node(component, NODE_ID)
    expect(get_toolbox_button(component, "nodeActionsExpand")).to_have_attribute(
        "title", "Expand Node"
    )
    double_click_node(component, NODE_ID)
    wait_for_node_ids(component, EXPANDED_NODE_IDS)
    expect(get_badge(component, NODE_ID)).to_have_text("-2")
    select_node(component, NODE_ID)
    expect(get_toolbox_button(component, "nodeActionsExpand")).to_have_attribute(
        "title", "Collapse Node"
    )

    double_click_node(component, NODE_ID)
    wait_for_node_ids(component, INITIAL_NODE_IDS)
    expect(get_badge(component, NODE_ID)).to_have_text("+2")


def test_expansion_badge_compacts_large_counts(
    page: Page,
):
    page.get_by_role("link", name=PAGE_NAME).click()
    component = get_component(page)
    component.click(position={"x": 0, "y": 0})  # await and scroll to view

    get_cy(component).evaluate(f"""(element) => {{
        const cy = element._cyreg.cy;
        cy.getElementById("{NODE_ID}").data("expansion", {{
            state: "collapsed",
            next_count: 2,
            total_count: 1250,
            depth: 4,
        }});
    }}""")
    expect(get_badge(component, NODE_ID)).to_have_text("+2/1.2k")


def test_expansion_badge_toggle_hides_and_restores_badges(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    component = get_component(page)
    component.click(position={"x": 0, "y": 0})  # await and scroll to view

    wait_for_node_ids(component, INITIAL_NODE_IDS)
    expect(get_badge(component, NODE_ID)).to_have_text("+2")
    toggle = get_toolbox_button(component, "expansionBadgeToggle")

    toggle.click()
    expect(toggle).to_have_attribute("aria-pressed", "false")
    expect(toggle).to_have_attribute("title", "Show Expansion Counts")
    expect(get_badge(component, NODE_ID)).to_be_hidden()

    select_node(component, NODE_ID)
    expand = get_toolbox_button(component, "nodeActionsExpand")
    expect(expand).to_be_enabled()
    expand.click()
    wait_for_node_ids(component, EXPANDED_NODE_IDS)
    expect(get_badge(component, NODE_ID)).to_be_hidden()

    toggle.click()
    expect(toggle).to_have_attribute("aria-pressed", "true")
    expect(get_badge(component, NODE_ID)).to_have_text("-2")


def test_remove_keydown(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    component = get_component(page)
    component.click(position={"x": 0, "y": 0})  # await and scroll to view

    click_node(component, NODE_ID)
    wait_for_info_panel_selection(component)
    page.keyboard.down("Delete")
    wait_for_node_ids(
        component,
        [node_id for node_id in INITIAL_NODE_IDS if node_id != NODE_ID],
    )


def test_remove_button(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    component = get_component(page)
    component.click(position={"x": 0, "y": 0})  # await and scroll to view

    click_node(component, NODE_ID)
    wait_for_info_panel_selection(component)
    remove = get_toolbox_button(component, "nodeActionsRemove")
    expect(remove).to_have_attribute("title", "Remove Nodes")
    remove.click()
    wait_for_node_ids(
        component,
        [node_id for node_id in INITIAL_NODE_IDS if node_id != NODE_ID],
    )
    expect(
        page.get_by_test_id("stAlertContentInfo")
        .get_by_text("Removed selected node(s) in Python state.")
        .first
    ).to_be_visible(timeout=10000)
