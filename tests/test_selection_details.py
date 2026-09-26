"""Panel preferences must never take ownership of the graph's selection."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from st_graph_workbench.component import component as api
from graph_test_helpers import (
    get_component,
    get_cy,
    open_toolbox_menu,
    select_element,
    select_nodes,
    wait_for_app_idle,
    wait_for_cy_ready,
)

APP = Path(__file__).parent / "apps" / "selection_details.py"
ELEMENTS = {"nodes": [{"data": {"id": "a"}}], "edges": []}


@pytest.mark.parametrize("preference", [None, True, False])
def test_details_argument_default_and_serialization(monkeypatch, preference):
    calls = []
    monkeypatch.setattr(api.st, "session_state", {})
    monkeypatch.setattr(api, "_component_func", lambda **kwargs: calls.append(kwargs))
    options = {} if preference is None else {"show_selection_details": preference}
    api.graph_workbench(ELEMENTS, **options)
    assert calls[0]["data"]["showSelectionDetails"] is (preference is not False)


@pytest.mark.parametrize("value", [None, "false", 0, 1, [], {}])
def test_details_argument_rejects_non_booleans(value):
    with pytest.raises(TypeError, match="show_selection_details must be a bool"):
        api.graph_workbench(ELEMENTS, show_selection_details=value)


def runtime(component):
    return get_cy(component).evaluate("""el => {
        const cy = el._cyreg.cy;
        return {selected: cy.elements(':selected').map(e => e.id()),
            zoom: cy.zoom(), pan: cy.pan(),
            positions: cy.nodes().map(n => ({id: n.id(), position: n.position()})),
            marker: cy.scratch('details-test')};
    }""")


def toggle(component, visible):
    component.locator("#selectionControls summary").evaluate(
        "el => el.scrollIntoView({block: 'center'})"
    )
    open_toolbox_menu(component, "selectionControls")
    component.get_by_label("Show selection details", exact=True).set_checked(visible)
    component.locator("#selectionControls summary").click()


def set_app_preference(page, visible):
    control = page.get_by_role("checkbox", name="Python details preference", exact=True)
    if control.is_checked() != visible:
        page.get_by_text("Python details preference", exact=True).click()
    expect(control).to_be_checked(checked=visible)
    wait_for_app_idle(page)


@pytest.mark.parametrize("clear_control", ["selectionClear", "infopanelClear"])
def test_explicit_clear_removes_analysis_but_preserves_search_and_other_graph(
    page, serve_streamlit, clear_control
):
    port = serve_streamlit(APP)
    page.goto(f"http://localhost:{port}")
    graph, other = get_component(page), get_component(page, 1)
    for component in (graph, other):
        select_nodes(component, ["a"])
        open_toolbox_menu(component, "analysisControls")
        component.locator("#analysisDegree").click()
        expect(page.get_by_test_id("stMetricValue")).to_be_visible()
        assert (
            get_cy(component).evaluate(
                "el => el._cyreg.cy.edges('.analysis-result').length"
            )
            == 1
        )
    graph.locator("#graphSearchInput").fill("Record A")
    graph.locator("#graphSearchApply").click()
    expect(graph.locator("#graphSearchStatus")).to_contain_text("1")
    # Wait for the search-focus animation before comparing viewport state.
    page.wait_for_function(
        "el => !el._cyreg.cy.animated()", arg=get_cy(graph).element_handle()
    )
    wait_for_app_idle(page)
    before, other_before = runtime(graph), runtime(other)
    if clear_control == "selectionClear":
        # Ordinary deselection leaves analysis visible; explicit Clear still works.
        get_cy(graph).evaluate("el => el._cyreg.cy.elements(':selected').unselect()")
        expect(graph.locator("#selectionStatusCount")).to_have_text("0 selected")
        assert (
            get_cy(graph).evaluate(
                "el => el._cyreg.cy.edges('.analysis-result').length"
            )
            == 1
        )
        open_toolbox_menu(graph, "selectionControls")
    graph.locator(f"#{clear_control}").click()
    expect(graph.locator("#selectionStatusCount")).to_have_text("0 selected")
    assert (
        get_cy(graph).evaluate("el => el._cyreg.cy.elements('.analysis-result').length")
        == 0
    )
    assert get_cy(graph).evaluate(
        "el => el._cyreg.cy.nodes('.search-match').map(n => n.id())"
    ) == ["a"]
    page.get_by_role("button", name="Rerun", exact=True).click()
    wait_for_app_idle(page)
    assert (
        get_cy(graph).evaluate("el => el._cyreg.cy.elements('.analysis-result').length")
        == 0
    )
    assert runtime(graph) == {**before, "selected": []}
    assert runtime(other) == other_before
    assert (
        get_cy(other).evaluate("el => el._cyreg.cy.edges('.analysis-result').length")
        == 1
    )


@pytest.mark.parametrize("mode", ["single", "multiple", "box"])
@pytest.mark.parametrize("record", ["a", "ab"])
def test_checkbox_preserves_selection_and_x_clears_without_disabling_details(
    page, serve_streamlit, mode, record
):
    port = serve_streamlit(APP)
    page.goto(f"http://localhost:{port}")
    page.get_by_role("combobox", name="Selection mode", exact=True).click()
    page.get_by_role("option", name=mode, exact=True).click()
    graph = get_component(page)
    wait_for_app_idle(page)
    get_cy(graph).evaluate("el => el._cyreg.cy.scratch('details-test', true)")
    select_element(graph, record)
    expect(graph.locator("#infopanel")).to_be_visible()
    expect(page.get_by_test_id("stMetricValue")).to_have_text("1")
    wait_for_app_idle(page)
    before = runtime(graph)
    events = page.get_by_test_id("stMetricValue").inner_text()
    toggle(graph, False)
    expect(graph.locator("#infopanel")).to_be_hidden()
    assert runtime(graph) == before
    expect(page.get_by_test_id("stMetricValue")).to_have_text(events)
    toggle(graph, True)
    expect(graph.locator("#infopanel")).to_be_visible()
    assert runtime(graph) == before
    expect(page.get_by_test_id("stMetricValue")).to_have_text(events)
    graph.locator("#infopanelClear").click()
    expect(graph.locator("#selectionControls summary")).to_be_focused()
    expect(graph.locator("#selectionShowDetails")).to_be_checked()
    expect(graph.locator("#selectionStatusCount")).to_have_text("0 selected")
    expect(graph.locator("#infopanel")).to_have_attribute("data-expanded", "false")
    expect(page.get_by_test_id("stMetricValue")).to_have_text(str(int(events) + 1))
    wait_for_app_idle(page)
    assert runtime(graph) == {**before, "selected": []}
    select_element(graph, record)
    expect(graph.locator("#infopanel")).to_be_visible()
    assert runtime(graph) == before
    toggle(graph, False)
    select_nodes(graph, ["b"])
    expect(graph.locator("#infopanel")).to_be_hidden()
    expect(graph.locator("#nodeActions")).to_have_attribute("data-expanded", "true")
    open_toolbox_menu(graph, "crudControls")
    expect(graph.locator("#crudReadSelected")).to_be_enabled()
    open_toolbox_menu(graph, "analysisControls")
    expect(graph.locator("#analysisDegree")).to_be_enabled()
    open_toolbox_menu(graph, "selectionControls")
    graph.locator("#selectionClear").click()
    expect(graph.locator("#selectionStatusCount")).to_have_text("0 selected")
    expect(graph.locator("#infopanel")).to_be_hidden()
    toggle(graph, True)
    expect(graph.locator("#infopanel")).to_have_attribute("data-expanded", "false")


def test_preferences_survive_reruns_updates_and_are_instance_local(
    page, serve_streamlit
):
    port = serve_streamlit(APP)
    page.goto(f"http://localhost:{port}")
    first, second = get_component(page), get_component(page, 1)
    select_nodes(first, ["a"])
    toggle(first, False)
    select_nodes(second, ["b"])
    expect(second.locator("#infopanel")).to_be_visible()
    get_cy(first).evaluate("el => el._cyreg.cy.scratch('details-test', true)")
    before = runtime(first)
    page.get_by_role("button", name="Rerun", exact=True).click()
    wait_for_app_idle(page)
    expect(first.locator("#infopanel")).to_be_hidden()
    assert runtime(first) == before
    page.get_by_role("button", name="Update records", exact=True).click()
    expect(first.locator("#selectionShowDetails")).not_to_be_checked()
    page.wait_for_function(
        "el => el._cyreg.cy.getElementById('b').data('name') === 'Updated B'",
        arg=get_cy(first).element_handle(),
    )
    assert runtime(first) == before
    set_app_preference(page, False)
    toggle(first, True)
    expect(first.locator("#infopanel")).to_be_visible()
    page.get_by_role("button", name="Rerun", exact=True).click()
    wait_for_app_idle(page)
    expect(first.locator("#infopanel")).to_be_visible()
    toggle(first, False)
    set_app_preference(page, True)
    expect(first.locator("#infopanel")).to_be_visible()
    assert runtime(first) == before
    toggle(first, False)
    page.reload()
    first = get_component(page)
    expect(first.locator("#selectionShowDetails")).to_be_checked()
    set_app_preference(page, False)
    expect(first.locator("#infopanel")).to_be_hidden()
    toggle(first, True)
    page.get_by_role("button", name="New graph key", exact=True).click()
    wait_for_app_idle(page)
    wait_for_cy_ready(first)
    expect(first.locator("#selectionShowDetails")).not_to_be_checked()
    expect(second.locator("#selectionShowDetails")).to_be_checked()
    select_nodes(first, ["a"])
    page.get_by_role("button", name="Remove selected record", exact=True).click()
    expect(first.locator("#selectionStatusCount")).to_have_text("0 selected")
    toggle(first, True)
    expect(first.locator("#infopanel")).to_have_attribute("data-expanded", "false")


def test_hidden_details_still_populate_the_tutorial_table(page, run_streamlit):
    page.goto(f"http://localhost:{run_streamlit}/learn_selection")
    graph = get_component(page)
    select_nodes(graph, ["ABC123"])
    expect(page.get_by_test_id("stMetricValue")).to_have_text("2")
    toggle(graph, False)
    select_nodes(graph, ["ABC123", "ALPHA"])
    expect(page.get_by_test_id("stMetricValue")).to_have_text("3")
    expect(graph.locator("#infopanel")).to_be_hidden()
    open_toolbox_menu(graph, "selectionControls")
    graph.get_by_label("Show selection details", exact=True).focus()
    page.keyboard.press("Space")
    expect(graph.locator("#infopanel")).to_be_visible()
    graph.locator("#selectionControls summary").click()
    graph.locator("#infopanelClear").focus()
    page.keyboard.press("Enter")
    expect(page.get_by_test_id("stMetricValue")).to_have_text("0")
    expect(graph.locator("#selectionShowDetails")).to_be_checked()
    select_nodes(graph, ["ABC123"])
    expect(graph.locator("#infopanel")).to_be_visible()
    expect(page.get_by_test_id("stMetricValue")).to_have_text("2")
