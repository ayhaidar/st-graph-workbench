"""The learning path is directly navigable and its interactions are real."""

import pytest
import re
from playwright.sync_api import expect
from examples.page_catalog import TUTORIAL_PAGES
from graph_test_helpers import (
    get_component,
    get_cy,
    get_total_counts,
    select_nodes,
    wait_for_app_idle,
)


@pytest.mark.parametrize("guide", TUTORIAL_PAGES, ids=lambda guide: str(guide.lesson))
def test_every_lesson_opens_directly(page, run_streamlit, guide):
    page.goto(
        f"http://localhost:{run_streamlit}/" + ("" if guide.default else guide.url_path)
    )
    expect(page.get_by_role("heading", name=guide.title, exact=True)).to_be_visible(
        timeout=20000
    )
    component = get_component(page)
    assert get_total_counts(component)["nodes"] > 0
    expect(
        page.get_by_role("heading", name="Learning objectives", exact=True)
    ).to_have_count(1)
    for target in guide.learning_objectives:
        # The second copy is in the optional end-of-lesson review.
        expect(page.get_by_text(target, exact=True).first).to_be_visible()
    expect(
        page.get_by_role("heading", name="Code in practice", exact=True)
    ).to_have_count(1)
    assert page.get_by_test_id("stCode").count() >= 2
    expect(page.get_by_text("Check your understanding", exact=True)).to_be_visible()
    expect(
        page.get_by_role("heading", name="Data and practical result", exact=True)
    ).to_be_visible()
    expect(
        page.get_by_role("heading", name="Returned dictionary", exact=True)
    ).to_have_count(0)
    if guide.lesson == 1:
        expect(
            page.get_by_role("heading", name="Input graph dictionary", exact=True)
        ).to_be_visible()
    for heading in ("How this example works", "Try it and check the result"):
        explanation = page.get_by_role("heading", name=heading, exact=True)
        expect(explanation).to_have_count(1)
        expect(explanation).to_be_visible()
    expect(
        page.get_by_role("heading", name="Common mistakes and next step", exact=True)
    ).to_be_visible()
    expect(page.get_by_test_id("stException")).to_have_count(0)
    assert page.evaluate("""() => {
        const table = document.querySelector('[data-testid="stDataFrame"]');
        const graph = document.querySelector('#container');
        const headings = [...document.querySelectorAll('h2, h3')];
        const explanation = headings.find(el => el.textContent === 'How this example works');
        const exercise = headings.find(el => el.textContent === 'Try it and check the result');
        const follows = (first, second) => Boolean(
            first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING
        );
        return follows(table, explanation) && follows(explanation, graph)
            && follows(graph, exercise);
    }""")


def test_navigation_modes_and_previous_next(page):
    get_component(page)
    sidebar = page.get_by_test_id("stSidebar")
    expect(
        sidebar.get_by_role("link", name=re.compile("Investigation Tools$"))
    ).to_have_count(0)
    page.get_by_role("link", name=re.compile("Next lesson$")).click()
    expect(page).to_have_title("Change nodes and edges")
    page.get_by_role("link", name=re.compile("Previous lesson$")).click()
    expect(page).to_have_title("Build your first graph")
    sidebar.get_by_role("radio", name="Feature Lab", exact=True).click()
    expect(page).to_have_title("Feature finder")
    expect(
        sidebar.get_by_role("link", name=re.compile("1. Build your first graph$"))
    ).to_have_count(0)
    expect(
        sidebar.get_by_role("link", name=re.compile("Investigation Tools$"))
    ).to_be_visible()
    sidebar.get_by_role("radio", name="Tutorials", exact=True).click()
    expect(page).to_have_title("Build your first graph")


def test_checkpoint_mutations_survive_navigation_and_reset_is_local(page):
    sidebar = page.get_by_test_id("stSidebar")
    sidebar.get_by_role("link", name=re.compile("2. Change nodes and edges$")).click()
    expect(page).to_have_title("Change nodes and edges")
    get_component(page)
    expect(page.get_by_test_id("stApp")).to_have_attribute(
        "data-test-script-state", "notRunning"
    )
    operation = page.get_by_role("combobox", name="Record operation")
    operation.evaluate("el => el.scrollIntoView({block: 'center'})")
    operation.click()
    page.get_by_role("option", name="Add", exact=True).click()
    expect(operation).to_have_value("Add")
    expect(page.get_by_test_id("stApp")).to_have_attribute(
        "data-test-script-state", "notRunning"
    )
    page.get_by_role("button", name=re.compile("Apply operation$")).click()
    page.wait_for_function(
        "document.querySelector('#cy')?._cyreg?.cy?.getElementById('checkpoint').length === 1"
    )
    sidebar.get_by_role("link", name=re.compile("3. Style your graph$")).click()
    other = get_component(page)
    assert get_total_counts(other)["nodes"] == 7
    page.get_by_role("button", name=re.compile("Reset lesson$")).click()
    sidebar.get_by_role("link", name=re.compile("2. Change nodes and edges$")).click()
    component = get_component(page)
    assert get_total_counts(component)["nodes"] == 8
    page.get_by_role("button", name=re.compile("Reset lesson$")).click()
    page.wait_for_function(
        "document.querySelector('#cy')?._cyreg?.cy?.nodes().length === 7"
    )


def test_selection_drives_records_and_clears(page, run_streamlit):
    page.goto(f"http://localhost:{run_streamlit}/learn_selection")
    component = get_component(page)
    select_nodes(component, ["ABC123"])
    expect(page.get_by_test_id("stMetricValue")).to_have_text("2")
    select_nodes(component, [])
    expect(page.get_by_test_id("stMetricValue")).to_have_text("0")
    assert get_cy(component).evaluate("el => el._cyreg.cy.nodes().length") == 7


@pytest.mark.parametrize("width", [1440, 390])
def test_record_controls_follow_description_and_target_checkpoint(
    page, run_streamlit, tmp_path, width
):
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(f"http://localhost:{run_streamlit}/learn_change_records")
    component = get_component(page)
    wait_for_app_idle(page)
    expect(
        page.locator("p").filter(has_text="All four operations target one node")
    ).to_be_visible()
    control = page.get_by_role("combobox", name="Record operation", exact=True)
    assert page.get_by_test_id("stCode").first.evaluate(
        "(code, control) => Boolean(code.compareDocumentPosition(control) & Node.DOCUMENT_POSITION_FOLLOWING)",
        control.element_handle(),
    )
    control.evaluate("el => el.scrollIntoView({block: 'center'})")
    assert (
        0
        < component.bounding_box()["y"]
        - (control.bounding_box()["y"] + control.bounding_box()["height"])
        < 180
    )
    page.screenshot(path=tmp_path / f"record-controls-{width}.png")

    def apply(operation):
        wait_for_app_idle(page)
        control.click()
        page.get_by_role("option", name=operation, exact=True).click()
        expect(control).to_have_value(operation)
        wait_for_app_idle(page)
        page.get_by_role("button", name=re.compile("Apply operation$")).click()
        wait_for_app_idle(page)

    selected_result = page.get_by_test_id("stJson").first
    apply("Get")
    expect(selected_result).to_contain_text(re.compile('"element":null', re.IGNORECASE))
    apply("Add")
    expect(selected_result).to_contain_text('"id":"checkpoint"')
    assert get_total_counts(component) == {"nodes": 8, "edges": 6}
    select_nodes(component, ["ABC123"])
    apply("Update")
    expect(selected_result).to_contain_text("Updated checkpoint")
    assert (
        get_cy(component).evaluate(
            "el => el._cyreg.cy.getElementById('ABC123').data('name')"
        )
        == "ABC123"
    )
    apply("Delete")
    expect(selected_result).to_contain_text(re.compile('"element":null', re.IGNORECASE))
    assert get_total_counts(component) == {"nodes": 7, "edges": 5}
    expect(page.get_by_test_id("stException")).to_have_count(0)


@pytest.mark.parametrize("width", [1440, 390])
@pytest.mark.parametrize("route", ["", "learn_selection", "learn_loading"])
def test_learning_objectives_and_code_are_readable(
    page, run_streamlit, tmp_path, route, width
):
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(f"http://localhost:{run_streamlit}/{route}")
    get_component(page)
    wait_for_app_idle(page)
    objectives = page.get_by_role("heading", name="Learning objectives", exact=True)
    objectives.evaluate("el => el.scrollIntoView({block: 'start'})")
    page.screenshot(path=tmp_path / f"{route or 'first_graph'}-objectives-{width}.png")
    assert page.evaluate("""() => {
        const heading = [...document.querySelectorAll('h2,h3')].find(
            el => el.textContent === 'Learning objectives');
        const table = document.querySelector('[data-testid="stDataFrame"]');
        return Boolean(heading.compareDocumentPosition(table) & Node.DOCUMENT_POSITION_FOLLOWING);
    }""")
    practice = page.get_by_role("heading", name="Code in practice", exact=True)
    practice.evaluate("el => el.scrollIntoView({block: 'start'})")
    page.screenshot(path=tmp_path / f"{route or 'first_graph'}-code-{width}.png")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    for heading in page.get_by_role("heading").all():
        assert heading.evaluate("el => el.scrollWidth <= el.clientWidth + 1")
    expect(page.get_by_test_id("stException")).to_have_count(0)
