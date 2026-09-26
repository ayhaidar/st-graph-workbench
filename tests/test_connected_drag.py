"""Connected records move rigidly without changing graph selection or data."""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from st_graph_workbench.component import component as api
from graph_test_helpers import (
    get_component,
    get_cy,
    get_node_pos,
    open_toolbox_menu,
    select_nodes,
    wait_for_app_idle,
)

APP = Path(__file__).parent / "apps" / "connected_drag.py"
ELEMENTS = {"nodes": [{"data": {"id": "a"}}], "edges": []}


def positions(component):
    return get_cy(component).evaluate(
        """element => Object.fromEntries(
            element._cyreg.cy.nodes().map(node => [node.id(), node.position()])
        )"""
    )


def drag_without_click(page: Page, component, node_id: str, *, dx: int, dy: int):
    cy = get_cy(component)
    cy.scroll_into_view_if_needed()
    position = get_node_pos(node_id, component)
    box = cy.bounding_box()
    assert box is not None
    start_x = box["x"] + position["x"]
    start_y = box["y"] + position["y"]
    page.mouse.move(start_x, start_y)
    page.mouse.down()
    page.mouse.move(start_x + dx, start_y + dy, steps=15)
    page.mouse.up()
    page.wait_for_timeout(500)


def enable_connected_drag(component, depth: int = 1):
    open_toolbox_menu(component, "selectionControls")
    toggle = component.get_by_label("Move connected nodes", exact=True)
    expect(toggle).to_be_enabled(timeout=10000)
    toggle.set_checked(True)
    component.locator("#connectedDragDepth").select_option(str(depth))
    expect(toggle).to_be_checked()
    expect(component.locator("#connectedDragDepth")).to_have_value(str(depth))
    component.page.wait_for_timeout(250)
    expect(toggle).to_be_checked()
    expect(component.locator("#connectedDragDepth")).to_have_value(str(depth))
    component.locator("#selectionControls summary").click()


def delta(before, after, node_id):
    return (
        after[node_id]["x"] - before[node_id]["x"],
        after[node_id]["y"] - before[node_id]["y"],
    )


def assert_same_delta(before, after, *node_ids):
    anchor_delta = delta(before, after, node_ids[0])
    assert abs(anchor_delta[0]) > 5 or abs(anchor_delta[1]) > 5
    for node_id in node_ids[1:]:
        node_delta = delta(before, after, node_id)
        assert node_delta == pytest.approx(anchor_delta, abs=1.5)


def assert_fixed(before, after, *node_ids):
    for node_id in node_ids:
        assert after[node_id] == pytest.approx(before[node_id], abs=0.5)


@pytest.mark.parametrize(
    "config",
    [
        {"enabled": False},
        {"enabled": True, "depth": 2, "max_depth": 3, "max_nodes": 40},
    ],
)
def test_connected_drag_serializes_normalized_configuration(monkeypatch, config):
    calls = []
    monkeypatch.setattr(api.st, "session_state", {})
    monkeypatch.setattr(api, "_component_func", lambda **kwargs: calls.append(kwargs))

    api.graph_workbench(ELEMENTS, connected_drag=config)

    assert calls[0]["data"]["connectedDrag"] == api._normalize_connected_drag(config)


def test_connected_drag_controls_are_opt_in(page: Page, serve_streamlit):
    port = serve_streamlit(APP)
    page.goto(f"http://localhost:{port}")
    graph = get_component(page)
    open_toolbox_menu(graph, "selectionControls")
    expect(graph.locator("#connectedDragControls")).to_be_visible()
    graph.locator("#selectionControls summary").click()

    page.get_by_text("Configure connected dragging", exact=True).click()
    expect(
        page.get_by_label("Configure connected dragging", exact=True)
    ).not_to_be_checked()
    wait_for_app_idle(page)
    open_toolbox_menu(graph, "selectionControls")
    expect(graph.locator("#connectedDragControls")).to_be_hidden()


@pytest.mark.parametrize(
    ("depth", "moving", "fixed"),
    [
        (1, ["a", "b"], ["c", "d", "branch", "locked", "fixed", "unrelated"]),
        (2, ["a", "b", "c", "branch"], ["d", "locked", "fixed", "unrelated"]),
        (3, ["a", "b", "c", "d", "branch"], ["locked", "fixed", "unrelated"]),
    ],
)
def test_connected_drag_uses_visible_undirected_hops(
    page: Page, serve_streamlit, depth, moving, fixed
):
    port = serve_streamlit(APP)
    page.goto(f"http://localhost:{port}")
    graph = get_component(page)
    enable_connected_drag(graph, depth)
    before = positions(graph)

    drag_without_click(page, graph, "a", dx=70, dy=45)

    after = positions(graph)
    assert_same_delta(before, after, *moving)
    assert_fixed(before, after, *fixed)
    expect(page.get_by_test_id("stJson").first).to_contain_text("connected_drag")
    expect(page.get_by_test_id("stJson").first).to_contain_text(f'"depth":{depth}')


def test_selected_group_moves_once_and_followers_are_not_selected(
    page: Page, serve_streamlit
):
    port = serve_streamlit(APP)
    page.goto(f"http://localhost:{port}")
    graph = get_component(page)
    enable_connected_drag(graph)
    select_nodes(graph, ["a", "d"])
    before = positions(graph)

    drag_without_click(page, graph, "a", dx=60, dy=-35)

    after = positions(graph)
    assert_same_delta(before, after, "a", "b", "d")
    assert_fixed(before, after, "c", "branch", "locked", "fixed", "unrelated")
    selected = get_cy(graph).evaluate(
        "el => el._cyreg.cy.nodes(':selected').map(node => node.id()).sort()"
    )
    assert selected == ["a", "d"]


def test_hidden_nodes_break_the_visible_drag_scope(page: Page, serve_streamlit):
    port = serve_streamlit(APP)
    page.goto(f"http://localhost:{port}")
    graph = get_component(page)
    enable_connected_drag(graph, depth=3)
    get_cy(graph).evaluate("el => el._cyreg.cy.getElementById('b').hide()")
    before = positions(graph)

    drag_without_click(page, graph, "a", dx=50, dy=25)

    after = positions(graph)
    assert_same_delta(before, after, "a")
    assert_fixed(before, after, "b", "c", "d", "branch", "locked", "fixed", "unrelated")


def test_over_limit_refuses_followers_atomically(page: Page, serve_streamlit):
    port = serve_streamlit(APP)
    page.goto(f"http://localhost:{port}")
    graph = get_component(page, 2)
    open_toolbox_menu(graph, "selectionControls")
    expect(graph.get_by_label("Move connected nodes", exact=True)).to_be_enabled(
        timeout=10000
    )
    expect(graph.get_by_label("Move connected nodes", exact=True)).to_be_checked()
    expect(graph.locator("#connectedDragDepth")).to_have_value("2")
    graph.locator("#selectionControls summary").click()
    before = positions(graph)

    drag_without_click(page, graph, "a", dx=55, dy=30)

    after = positions(graph)
    assert_same_delta(before, after, "a")
    assert_fixed(before, after, "b", "c", "d", "branch", "locked", "fixed", "unrelated")
    open_toolbox_menu(graph, "selectionControls")
    expect(graph.locator("#connectedDragStatus")).to_contain_text(
        "connected nodes exceed the 1 node limit"
    )
    expect(page.get_by_test_id("stJson").last).to_contain_text("limit_exceeded")


def test_connected_drag_preferences_are_instance_local_and_python_overrides(
    page: Page, serve_streamlit
):
    port = serve_streamlit(APP)
    page.goto(f"http://localhost:{port}")
    first, second = get_component(page), get_component(page, 1)
    enable_connected_drag(first, depth=2)
    open_toolbox_menu(second, "selectionControls")
    expect(second.get_by_label("Move connected nodes", exact=True)).to_be_checked()
    expect(second.locator("#connectedDragDepth")).to_have_value("1")
    second.locator("#selectionControls summary").click()

    page.get_by_role("button", name="Rerun", exact=True).click()
    wait_for_app_idle(page)
    open_toolbox_menu(first, "selectionControls")
    expect(first.get_by_label("Move connected nodes", exact=True)).to_be_checked()
    expect(first.locator("#connectedDragDepth")).to_have_value("2")
    first.locator("#selectionControls summary").click()

    page.get_by_text("Python connected-drag default", exact=True).click()
    expect(
        page.get_by_label("Python connected-drag default", exact=True)
    ).to_be_checked()
    wait_for_app_idle(page)
    open_toolbox_menu(first, "selectionControls")
    expect(first.get_by_label("Move connected nodes", exact=True)).to_be_checked()
    expect(first.locator("#connectedDragDepth")).to_have_value("1")


@pytest.mark.parametrize("width", [390, 768])
def test_connected_drag_toolbar_wraps_and_supports_keyboard(
    page: Page, serve_streamlit, width
):
    page.set_viewport_size({"width": width, "height": 900})
    port = serve_streamlit(APP)
    page.goto(f"http://localhost:{port}")
    graph = get_component(page)
    open_toolbox_menu(graph, "selectionControls")
    toggle = graph.get_by_label("Move connected nodes", exact=True)
    expect(toggle).to_be_enabled(timeout=10000)
    toggle.focus()
    page.keyboard.press("Space")
    expect(toggle).to_be_checked()
    depth = graph.locator("#connectedDragDepth")
    depth.focus()
    page.keyboard.press("ArrowDown")
    expect(depth).to_have_value("2")
    assert graph.locator("#selectionControls .toolbox__menu-content").evaluate(
        """menu => {
            const graph = menu.closest('#container').getBoundingClientRect();
            const box = menu.getBoundingClientRect();
            return box.left >= graph.left && box.right <= graph.right;
        }"""
    )
