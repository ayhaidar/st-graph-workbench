"""Adaptive toolbar layout, preference, and canvas-space regressions."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from graph_test_helpers import get_component, get_cy, wait_for_app_idle
from st_graph_workbench.component import component as api

APP = Path(__file__).parent / "apps" / "toolbar_layout.py"
ELEMENTS = {"nodes": [{"data": {"id": "a"}}], "edges": []}


def set_python_mode(page, mode):
    page.get_by_role("combobox", name="Python toolbar mode").click()
    page.get_by_role("option", name=mode, exact=True).click()
    wait_for_app_idle(page)


def test_toolbar_argument_serializes_normalized_defaults(monkeypatch):
    calls = []
    monkeypatch.setattr(api.st, "session_state", {})
    monkeypatch.setattr(api, "_component_func", lambda **kwargs: calls.append(kwargs))

    api.graph_workbench(ELEMENTS)
    assert calls[0]["data"]["toolbar"] == {
        "mode": "adaptive",
        "position": "top",
        "collapsible": True,
        "sticky": True,
    }


def test_adaptive_toolbar_reserves_space_and_minimizes_without_graph_changes(
    page, serve_streamlit
):
    port = serve_streamlit(APP)
    page.goto(f"http://localhost:{port}")
    component = get_component(page)
    cy = get_cy(component)
    expect(component).to_have_attribute("data-toolbar-effective-mode", "expanded")

    before = cy.evaluate(
        """el => ({zoom: el._cyreg.cy.zoom(), pan: el._cyreg.cy.pan(),
            ids: el._cyreg.cy.elements().map(item => item.id())})"""
    )
    geometry = component.evaluate(
        """el => { const topbar = el.querySelector('#graphTopbar').getBoundingClientRect();
            const cy = el.querySelector('#cy').getBoundingClientRect();
            return {topbarBottom: topbar.bottom, cyTop: cy.top}; }"""
    )
    assert geometry["cyTop"] >= geometry["topbarBottom"]

    component.get_by_role("button", name="Minimize toolbar").click()
    expect(component).to_have_attribute("data-toolbar-effective-mode", "minimized")
    expect(component.get_by_role("button", name="Restore toolbar")).to_be_focused()
    assert (
        cy.evaluate(
            """el => ({zoom: el._cyreg.cy.zoom(), pan: el._cyreg.cy.pan(),
            ids: el._cyreg.cy.elements().map(item => item.id())})"""
        )
        == before
    )

    page.get_by_role("button", name="Rerun", exact=True).click()
    wait_for_app_idle(page)
    expect(component).to_have_attribute("data-toolbar-effective-mode", "minimized")

    set_python_mode(page, "compact")
    expect(component).to_have_attribute("data-toolbar-effective-mode", "compact")
    component.get_by_role("button", name="Open search controls").click()
    expect(component.locator("#graphSearchInput")).to_be_visible()
    expect(component.locator("#graphSearchInput")).to_be_focused()


def test_toolbar_configuration_controls_overlay_and_collapse_button(
    page, serve_streamlit
):
    port = serve_streamlit(APP)
    page.goto(f"http://localhost:{port}")
    component = get_component(page)

    reserve_space = page.get_by_role("checkbox", name="Reserve toolbar space")
    reserve_space.evaluate("el => el.click()")
    expect(reserve_space).not_to_be_checked()
    wait_for_app_idle(page)
    expect(component).to_have_attribute("data-toolbar-sticky", "false")
    geometry = component.evaluate(
        """el => { const container = el.getBoundingClientRect();
            const cy = el.querySelector('#cy').getBoundingClientRect();
            return {containerTop: container.top, cyTop: cy.top}; }"""
    )
    # The dashed component border accounts for the remaining few CSS pixels.
    assert geometry["cyTop"] == pytest.approx(geometry["containerTop"], abs=4)

    collapsible = page.get_by_role("checkbox", name="Allow minimizing")
    collapsible.evaluate("el => el.click()")
    expect(collapsible).not_to_be_checked()
    wait_for_app_idle(page)
    expect(component.locator("#toolbarCollapse")).to_be_hidden()


def test_adaptive_toolbar_switches_to_compact_at_narrow_width(page, serve_streamlit):
    port = serve_streamlit(APP)
    page.set_viewport_size({"width": 720, "height": 900})
    page.goto(f"http://localhost:{port}")
    component = get_component(page)
    expect(component).to_have_attribute("data-toolbar-effective-mode", "compact")
    expect(component.get_by_role("button", name="Open search controls")).to_be_visible()
    expect(component.locator(".toolbox__menu-label").first).to_be_hidden()
