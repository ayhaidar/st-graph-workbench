import time

from playwright.sync_api import Page, expect

from graph_test_helpers import (
    drag_canvas,
    drag_node,
    get_component,
    get_cy,
    get_node_view,
    get_total_counts,
    get_viewport,
    open_toolbox_menu,
    select_nodes,
)


PAGE_NAME = "Editing And Viewport Tools"


def graph_counts(component):
    return get_total_counts(component)


def wait_for_counts(component, *, nodes=None, edges=None):
    deadline = time.time() + 10
    while time.time() < deadline:
        counts = graph_counts(component)
        if (nodes is None or counts["nodes"] == nodes) and (
            edges is None or counts["edges"] == edges
        ):
            return
        time.sleep(0.1)
    counts = graph_counts(component)
    if nodes is not None:
        assert counts["nodes"] == nodes
    if edges is not None:
        assert counts["edges"] == edges


def get_node_interaction_state(component, node_id):
    return get_cy(component).evaluate(
        """(element, nodeId) => {
            const cy = element._cyreg.cy;
            const node = cy.getElementById(nodeId);
            return {
                locked: node.locked(),
                grabbable: node.grabbable(),
                selected: node.selected(),
                position: node.position(),
            };
        }""",
        node_id,
    )


def test_browser_edit_tools_add_connect_delete_and_undo(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")
    component = get_component(page)
    get_cy(component).scroll_into_view_if_needed()

    counts = graph_counts(component)
    open_toolbox_menu(component, "editControls")
    expect(component.locator("#editAddNode")).to_be_visible()
    component.locator("#editAddNode").click()
    wait_for_counts(component, nodes=counts["nodes"] + 1)
    expect(page.get_by_test_id("stJson").first).to_contain_text(
        "add_node", timeout=10000
    )

    select_nodes(component, ["case", "vehicle"])
    open_toolbox_menu(component, "editControls")
    expect(component.locator("#editConnectSelected")).to_be_enabled()
    component.locator("#editConnectSelected").click()
    wait_for_counts(component, edges=counts["edges"] + 1)
    expect(page.get_by_test_id("stJson").first).to_contain_text(
        "connect_selected", timeout=10000
    )

    select_nodes(component, ["node-1"])
    open_toolbox_menu(component, "editControls")
    expect(component.locator("#editDeleteSelected")).to_be_enabled()
    component.locator("#editDeleteSelected").click()
    wait_for_counts(component, nodes=counts["nodes"])
    expect(page.get_by_test_id("stJson").first).to_contain_text(
        "delete_selected", timeout=10000
    )

    open_toolbox_menu(component, "editControls")
    expect(component.locator("#editUndo")).to_be_enabled()
    component.locator("#editUndo").click()
    wait_for_counts(component, nodes=counts["nodes"] + 1)
    expect(page.get_by_test_id("stJson").first).to_contain_text("undo", timeout=10000)


def test_edit_tools_restore_node_dragging_after_fixed_states(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")
    component = get_component(page)
    get_cy(component).scroll_into_view_if_needed()

    select_nodes(component, ["vehicle"])
    open_toolbox_menu(component, "editControls")
    expect(component.locator("#editLockSelected")).to_be_enabled()
    component.locator("#editLockSelected").click()
    expect(page.get_by_test_id("stJson").first).to_contain_text(
        "lock_selected", timeout=10000
    )
    locked_state = get_node_interaction_state(component, "vehicle")
    assert locked_state["locked"] is True
    assert locked_state["selected"] is True

    open_toolbox_menu(component, "editControls")
    expect(component.locator("#editUnlockSelected")).to_be_enabled()
    component.locator("#editUnlockSelected").click()
    expect(page.get_by_test_id("stJson").first).to_contain_text(
        "unlock_selected", timeout=10000
    )
    unlocked_state = get_node_interaction_state(component, "vehicle")
    assert unlocked_state["locked"] is False

    open_toolbox_menu(component, "editControls")
    expect(component.locator("#editMakeUngrabbable")).to_be_enabled()
    component.locator("#editMakeUngrabbable").click()
    expect(page.get_by_test_id("stJson").first).to_contain_text(
        "make_ungrabbable", timeout=10000
    )
    fixed_state = get_node_interaction_state(component, "vehicle")
    assert fixed_state["grabbable"] is False

    open_toolbox_menu(component, "editControls")
    expect(component.locator("#editMakeGrabbable")).to_be_enabled()
    component.locator("#editMakeGrabbable").click()
    expect(page.get_by_test_id("stJson").first).to_contain_text(
        "make_grabbable", timeout=10000
    )
    restored_state = get_node_interaction_state(component, "vehicle")
    assert restored_state["locked"] is False
    assert restored_state["grabbable"] is True
    assert component.locator("#editControls").evaluate("(menu) => menu.open") is False

    before = get_node_view(component, "vehicle")
    after = drag_node(page, component, "vehicle", dx=80, dy=40)

    assert after["model"]["x"] > before["model"]["x"] + 35
    assert after["model"]["y"] > before["model"]["y"] + 15
    expect(page.get_by_test_id("stJson").first).to_contain_text(
        "positions",
        timeout=10000,
    )


def test_viewport_tools_save_restore_and_toggle_zoom(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")
    component = get_component(page)
    cy = get_cy(component)
    cy.scroll_into_view_if_needed()

    open_toolbox_menu(component, "viewportControls")
    expect(component.locator("#viewportSave")).to_be_visible()
    component.locator("#viewportSave").click()
    expect(page.get_by_test_id("stJson").first).to_contain_text(
        "save_viewport", timeout=10000
    )

    before = cy.evaluate("""(element) => {
        const cy = element._cyreg.cy;
        return {pan: cy.pan(), zoom: cy.zoom()};
    }""")
    cy.evaluate("""(element) => {
        const cy = element._cyreg.cy;
        cy.pan({x: 25, y: -45});
        cy.zoom(0.7);
    }""")

    open_toolbox_menu(component, "viewportControls")
    expect(component.locator("#viewportRestore")).to_be_enabled()
    component.locator("#viewportRestore").click()
    expect(page.get_by_test_id("stJson").first).to_contain_text(
        "restore_viewport", timeout=10000
    )
    page.wait_for_timeout(300)
    restored = cy.evaluate("""(element) => {
        const cy = element._cyreg.cy;
        return {pan: cy.pan(), zoom: cy.zoom()};
    }""")
    assert abs(restored["zoom"] - before["zoom"]) < 0.01
    assert abs(restored["pan"]["x"] - before["pan"]["x"]) < 1
    assert abs(restored["pan"]["y"] - before["pan"]["y"]) < 1

    open_toolbox_menu(component, "viewportControls")
    component.locator("#viewportToggleZoom").click()
    expect(component.locator("#viewportToggleZoom")).to_have_attribute(
        "aria-pressed", "false"
    )
    zoom_enabled = component.locator("#viewportToggleZoom").evaluate(
        """(button) => {
            return button
                .closest("#container")
                .querySelector("#cy")
                ._cyreg.cy.userZoomingEnabled();
        }"""
    )
    assert zoom_enabled is False


def test_real_mouse_pan_moves_canvas_without_losing_graph(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")
    component = get_component(page)

    before = get_viewport(component)
    after = drag_canvas(page, component, dx=-90, dy=-55)

    assert after["userPanning"] is True
    assert after["nodes"] == before["nodes"]
    assert after["edges"] == before["edges"]
    assert abs(after["zoom"] - before["zoom"]) < 0.01
    assert abs((after["pan"]["x"] - before["pan"]["x"]) + 90) < 2
    assert abs((after["pan"]["y"] - before["pan"]["y"]) + 55) < 2
