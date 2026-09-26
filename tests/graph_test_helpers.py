import time
import runpy
import re
from pathlib import Path
from urllib.parse import urlsplit
from typing import Any

from playwright.sync_api import Locator, Page, expect


COMPONENT_LOCATOR = "#container"
CY_LOCATOR = "#cy"
IFRAME_LOCATOR = "iframe[title*='st_graph_workbench']"


def click_nav(page: Page, name: str) -> None:
    catalog = runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "examples" / "page_catalog.py")
    )["PAGE_CATALOG"]
    guide = next(guide for guide in catalog if guide.title == name)
    if guide.area == "Reference":
        url = urlsplit(page.url)
        page.goto(f"{url.scheme}://{url.netloc}/{guide.url_path}")
        expect(page).to_have_title(name)
        return
    sidebar = page.get_by_test_id("stSidebar")
    # The accessible label includes a Material icon. Match text separately;
    # embedding a Python regex containing '/' in an ARIA selector is ambiguous.
    label = re.compile(rf"{re.escape(name)}$")
    link = sidebar.get_by_role("link").filter(has_text=label)
    if not link.count():
        sidebar.get_by_role("radio", name=guide.area, exact=True).click()
    link.click()
    expect(page).to_have_title(name)


def get_component(page: Page, index: int = 0, *, wait_for_cy: bool = True) -> Locator:
    component = page.locator(COMPONENT_LOCATOR).nth(index)
    # Streamlit navigation finishes over its websocket, after HTTP network idle.
    expect(component).to_be_visible(timeout=30000)
    if wait_for_cy:
        wait_for_cy_ready(component)
    return component


def get_cy(component: Locator) -> Locator:
    return component.locator(CY_LOCATOR)


def wait_for_app_idle(page: Page) -> None:
    """Wait for Streamlit's Python widgets, not only the browser graph, to update."""
    expect(page.get_by_test_id("stApp")).to_have_attribute(
        "data-test-script-state", "notRunning", timeout=15000
    )


def wait_for_cy_ready(component: Locator, *, timeout: float = 10) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        ready = get_cy(component).evaluate(
            """(element) => {
                const container = element.closest("#container");
                return Boolean(element._cyreg?.cy) &&
                    container?.dataset.ready === "true";
            }"""
        )
        if ready:
            return
        time.sleep(0.1)
    assert get_cy(component).evaluate(
        """(element) => {
            const container = element.closest("#container");
            return Boolean(element._cyreg?.cy) &&
                container?.dataset.ready === "true";
        }"""
    )


def get_node_ids(component: Locator) -> list[str]:
    return get_cy(component).evaluate("""(element) => {
        const cy = element._cyreg?.cy;
        if (!cy) {
            return [];
        }
        return cy.nodes().map((node) => node.id()).sort();
    }""")


def get_edge_ids(component: Locator) -> list[str]:
    return get_cy(component).evaluate("""(element) => {
        const cy = element._cyreg?.cy;
        if (!cy) {
            return [];
        }
        return cy.edges().map((edge) => edge.id()).sort();
    }""")


def get_total_counts(component: Locator) -> dict[str, int]:
    return get_cy(component).evaluate("""(element) => {
        const cy = element._cyreg.cy;
        return {
            nodes: cy.nodes().length,
            edges: cy.edges().length,
        };
    }""")


def get_visible_counts(component: Locator) -> dict[str, int]:
    return get_cy(component).evaluate("""(element) => {
        const cy = element._cyreg.cy;
        return {
            shownNodes: cy.nodes(":visible").length,
            hiddenNodes: cy.nodes().length - cy.nodes(":visible").length,
            totalNodes: cy.nodes().length,
            shownEdges: cy.edges(":visible").length,
            hiddenEdges: cy.edges().length - cy.edges(":visible").length,
            totalEdges: cy.edges().length,
        };
    }""")


def get_badge(component: Locator, node_id: str) -> Locator:
    return component.locator(f".expansion-badge[data-node-id='{node_id}']")


def open_toolbox_menu(component: Locator, menu_id: str) -> None:
    component.locator("#toolbox").evaluate(
        """(toolbox, menuId) => {
            toolbox.querySelectorAll("details").forEach((menu) => {
                menu.open = menu.id === menuId;
            });
        }""",
        menu_id,
    )
    expect(component.locator(f"#{menu_id}")).to_have_attribute("open", "")


def wait_for_info_panel_selection(
    component: Locator,
    expected_text: str | None = None,
) -> None:
    expect(component.locator("#infopanel")).to_have_attribute(
        "data-expanded",
        "true",
    )
    if expected_text is not None:
        expect(component.locator("#infopanelProps")).to_contain_text(expected_text)


def select_nodes(component: Locator, node_ids: list[str]) -> None:
    get_cy(component).evaluate(
        """(element, nodeIds) => {
            const cy = element._cyreg.cy;
            cy.elements(":selected").unselect();
            nodeIds.forEach((id) => cy.getElementById(id).select());
        }""",
        node_ids,
    )
    selected_count = len(node_ids)
    expected_text = (
        "0 selected"
        if selected_count == 0
        else f"{selected_count} node{'s' if selected_count != 1 else ''} selected"
    )
    expect(component.locator("#selectionStatusCount")).to_have_text(
        expected_text,
        timeout=10000,
    )
    time.sleep(0.5)
    wait_for_cy_ready(component)


def select_node(component: Locator, node_id: str) -> None:
    select_nodes(component, [node_id])
    wait_for_info_panel_selection(component, node_id)


def select_element(component: Locator, element_id: str) -> None:
    get_cy(component).evaluate(
        """(element, elementId) => {
            const cy = element._cyreg.cy;
            cy.elements(":selected").unselect();
            cy.getElementById(elementId).select();
        }""",
        element_id,
    )
    time.sleep(0.3)


def click_node(component: Locator, node_id: str, *, button: str = "left") -> None:
    get_cy(component).click(position=get_node_pos(node_id, component), button=button)


def double_click_node(component: Locator, node_id: str) -> None:
    get_cy(component).dblclick(position=get_node_pos(node_id, component))


def emit_cytoscape_event(
    component: Locator,
    element_id: str,
    event_type: str,
) -> None:
    get_cy(component).evaluate(
        """(element, args) => {
            const cy = element._cyreg.cy;
            cy.getElementById(args.elementId).emit(args.eventType);
        }""",
        {"elementId": element_id, "eventType": event_type},
    )


def open_context_menu_for_node(component: Locator, node_id: str) -> Locator:
    click_node(component, node_id, button="right")
    managed = component.get_attribute("data-managed-expansion") == "true"
    menu = component.locator(
        "#managedExpansionMenu" if managed else "#graphContextMenu"
    )
    expect(menu).to_be_visible()
    return menu


def wait_for_node_ids(
    component: Locator,
    expected_ids: list[str],
    *,
    timeout: float = 10,
) -> list[str]:
    expected_ids = sorted(expected_ids)
    deadline = time.time() + timeout
    while time.time() < deadline:
        node_ids = get_node_ids(component)
        if node_ids == expected_ids:
            return node_ids
        time.sleep(0.1)
    actual = get_node_ids(component)
    assert actual == expected_ids, (
        f"Displayed nodes: {actual}; expected: {expected_ids}"
    )
    return expected_ids


def wait_for_edge_ids(
    component: Locator,
    expected_ids: list[str],
    *,
    timeout: float = 10,
) -> list[str]:
    expected_ids = sorted(expected_ids)
    deadline = time.time() + timeout
    while time.time() < deadline:
        edge_ids = get_edge_ids(component)
        if edge_ids == expected_ids:
            return edge_ids
        time.sleep(0.1)
    assert get_edge_ids(component) == expected_ids
    return expected_ids


def wait_for_node(component: Locator, node_id: str, *, timeout: float = 10) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if node_id in get_node_ids(component):
            return
        time.sleep(0.1)
    assert node_id in get_node_ids(component)


def get_node_pos(node_id: str, component: Locator) -> dict[str, Any]:
    wait_for_cy_ready(component)
    get_cy(component).scroll_into_view_if_needed()
    time.sleep(0.2)
    return get_cy(component).evaluate(
        """(element, nodeId) => {
            const cy = element._cyreg.cy;
            return cy.getElementById(nodeId).renderedPosition();
        }""",
        node_id,
    )


def get_node_view(component: Locator, node_id: str) -> dict[str, Any]:
    wait_for_cy_ready(component)
    return get_cy(component).evaluate(
        """(element, nodeId) => {
            const cy = element._cyreg.cy;
            const node = cy.getElementById(nodeId);
            return {
                model: node.position(),
                rendered: node.renderedPosition(),
                selected: node.selected(),
                pan: cy.pan(),
                zoom: cy.zoom(),
            };
        }""",
        node_id,
    )


def get_viewport(component: Locator) -> dict[str, Any]:
    wait_for_cy_ready(component)
    return get_cy(component).evaluate("""(element) => {
        const cy = element._cyreg.cy;
        return {
            pan: cy.pan(),
            zoom: cy.zoom(),
            userPanning: cy.userPanningEnabled(),
            userZooming: cy.userZoomingEnabled(),
            nodes: cy.nodes().length,
            edges: cy.edges().length,
        };
    }""")


def drag_node(
    page: Page,
    component: Locator,
    node_id: str,
    *,
    dx: float,
    dy: float,
) -> dict[str, Any]:
    cy = get_cy(component)
    cy.scroll_into_view_if_needed()
    start_position = get_node_pos(node_id, component)
    cy.click(position=start_position)
    box = cy.bounding_box()
    assert box is not None
    start_x = box["x"] + start_position["x"]
    start_y = box["y"] + start_position["y"]

    page.mouse.move(start_x, start_y)
    page.mouse.down()
    page.mouse.move(start_x + dx, start_y + dy, steps=15)
    page.mouse.up()
    page.wait_for_timeout(300)
    return get_node_view(component, node_id)


def drag_canvas(
    page: Page,
    component: Locator,
    *,
    dx: float,
    dy: float,
) -> dict[str, Any]:
    cy = get_cy(component)
    cy.scroll_into_view_if_needed()
    box = cy.bounding_box()
    assert box is not None
    start_x = box["x"] + box["width"] - 40
    start_y = box["y"] + box["height"] - 40

    page.mouse.move(start_x, start_y)
    page.mouse.down()
    page.mouse.move(start_x + dx, start_y + dy, steps=15)
    page.mouse.up()
    page.wait_for_timeout(300)
    return get_viewport(component)


def get_edge_pos(edge_id: str, component: Locator) -> dict[str, Any]:
    wait_for_cy_ready(component)
    get_cy(component).scroll_into_view_if_needed()
    time.sleep(0.2)
    return get_cy(component).evaluate(
        """(element, edgeId) => {
            const cy = element._cyreg.cy;
            return cy.getElementById(edgeId).renderedMidpoint();
        }""",
        edge_id,
    )
