from pathlib import Path
import csv
import re
import time

import pytest

from playwright.sync_api import Page, expect

from graph_test_helpers import (
    get_component,
    get_cy,
    get_total_counts,
    open_toolbox_menu,
    select_nodes,
    wait_for_app_idle,
)


ROOT_DIR = Path(__file__).resolve().parents[1]


def mark_instance(component):
    get_cy(component).evaluate(
        "element => element._cyreg.cy.scratch('_loadingTest', true)"
    )


def assert_same_instance(component):
    assert get_cy(component).evaluate(
        "element => element._cyreg.cy.scratch('_loadingTest') === true"
    )


def positions(component):
    return get_cy(component).evaluate(
        """element => Object.fromEntries(element._cyreg.cy.nodes().map(
            node => [node.id(), { ...node.position() }]))"""
    )


def wait_for_counts(component, expected):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if get_total_counts(component) == expected:
            return
        time.sleep(0.1)
    assert get_total_counts(component) == expected


def viewport(component):
    return get_cy(component).evaluate(
        """(element) => {
            const cy = element._cyreg.cy;
            return { zoom: cy.zoom(), pan: cy.pan() };
        }"""
    )


def drag_without_click(page: Page, component, node_id: str, *, dx: int, dy: int):
    cy = get_cy(component)
    cy.scroll_into_view_if_needed()
    rendered = cy.evaluate(
        "(element, id) => element._cyreg.cy.getElementById(id).renderedPosition()",
        node_id,
    )
    box = cy.bounding_box()
    assert box is not None
    start_x = box["x"] + rendered["x"]
    start_y = box["y"] + rendered["y"]
    page.mouse.move(start_x, start_y)
    page.mouse.down()
    page.mouse.move(start_x + dx, start_y + dy, steps=15)
    page.mouse.up()
    page.wait_for_timeout(500)


def test_connected_location_drag_survives_the_next_batch(page: Page, run_streamlit):
    page.goto(f"http://localhost:{run_streamlit}/progressive_loading")
    component = get_component(page)
    open_toolbox_menu(component, "selectionControls")
    toggle = component.get_by_label("Move connected nodes", exact=True)
    expect(toggle).to_be_enabled(timeout=10000)
    toggle.set_checked(True)
    component.locator("#connectedDragDepth").select_option("1")
    component.locator("#selectionControls summary").click()

    follower_ids = get_cy(component).evaluate(
        """element => {
            const cy = element._cyreg.cy;
            const root = cy.getElementById('location-north');
            return root.connectedEdges(':visible').connectedNodes(':visible')
                .difference(root).map(node => node.id()).sort();
        }"""
    )
    assert len(follower_ids) == 20
    before = positions(component)

    drag_without_click(page, component, "location-north", dx=55, dy=30)
    wait_for_app_idle(page)
    moved = positions(component)
    root_delta = {
        axis: moved["location-north"][axis] - before["location-north"][axis]
        for axis in ("x", "y")
    }
    assert abs(root_delta["x"]) > 5 or abs(root_delta["y"]) > 5
    for node_id in follower_ids:
        for axis in ("x", "y"):
            assert moved[node_id][axis] - before[node_id][axis] == pytest.approx(
                root_delta[axis], abs=1.5
            )

    component.locator("#progressiveLoadingButton").click()
    wait_for_counts(component, {"nodes": 123, "edges": 120})
    after_load = positions(component)
    for node_id in ["location-north", *follower_ids]:
        assert after_load[node_id] == pytest.approx(moved[node_id], abs=0.5)


@pytest.mark.parametrize("width", [1440, 768, 390])
def test_load_more_button_stays_compact(page: Page, run_streamlit, tmp_path, width):
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(f"http://localhost:{run_streamlit}/progressive_loading")
    component = get_component(page)
    wait_for_app_idle(page)
    button = component.locator("#progressiveLoadingButton")
    icon = button.locator("svg")

    for count in (60, 120, 180):
        if count > 60:
            button.click()
        expect(component.locator("#progressiveLoadingStatus")).to_have_text(
            f"{count} / 600", timeout=15000
        )
        wait_for_counts(component, {"nodes": count + 3, "edges": count})
        expect(button).to_be_enabled()
        icon_box = icon.bounding_box()
        button_box = button.bounding_box()
        assert 18 <= icon_box["width"] <= 24, icon_box
        assert 18 <= icon_box["height"] <= 24, icon_box
        assert button_box["height"] <= 44, button_box
        assert button.evaluate("el => el.scrollWidth <= el.clientWidth")
        assert component.locator("#progressiveLoading").evaluate("""el => {
            const group = el.getBoundingClientRect();
            const graph = el.closest('#container').getBoundingClientRect();
            return group.height <= 56 && group.left >= graph.left &&
                group.right <= graph.right;
        }""")

    component.screenshot(path=tmp_path / f"progressive-loading-{width}.png")
    expect(page.get_by_test_id("stException")).to_have_count(0)


def test_progressive_loading_adds_a_batch_without_replacing_viewport(page: Page):
    page.locator('a[href="progressive_loading"]').click()
    page.wait_for_load_state("networkidle")
    component = get_component(page)

    expect(component.locator("#progressiveLoading")).to_be_visible()
    expect(component.locator("#progressiveLoadingStatus")).to_have_text("60 / 600")
    assert get_total_counts(component) == {"nodes": 63, "edges": 60}

    get_cy(component).evaluate(
        """(element) => {
            const cy = element._cyreg.cy;
            cy.zoom(1.15);
            cy.pan({ x: 37, y: 24 });
        }"""
    )
    before = viewport(component)
    component.locator("#progressiveLoadingButton").click()

    expect(component.locator("#progressiveLoadingStatus")).to_have_text(
        "120 / 600", timeout=10000
    )
    expect(component.locator("#progressiveLoadingButton")).to_be_enabled()
    assert get_total_counts(component) == {"nodes": 123, "edges": 120}
    after = viewport(component)
    assert abs(after["zoom"] - before["zoom"]) < 0.01
    assert abs(after["pan"]["x"] - before["pan"]["x"]) < 0.01
    assert abs(after["pan"]["y"] - before["pan"]["y"]) < 0.01


def test_progressive_loading_can_update_layout_without_replacing_graph(page: Page):
    page.locator('a[href="progressive_loading"]').click()
    page.wait_for_load_state("networkidle")
    component = get_component(page)
    wait_for_app_idle(page)
    mark_instance(component)
    before = positions(component)

    for choice in ("Circle", "fCoSE physics"):
        layout = page.get_by_role("combobox", name="Layout to apply", exact=True)
        layout.click()
        layout.fill(choice)
        layout.press("Enter")
        expect(layout).to_have_value(choice)
        page.get_by_role("button", name=re.compile("Apply layout$")).click()
        expect(
            page.get_by_text(f"Applied {choice}. The records did not change.")
        ).to_be_visible()

        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if positions(component) != before:
                break
            time.sleep(0.1)

        assert positions(component) != before
        before = positions(component)
        wait_for_app_idle(page)

    assert get_total_counts(component) == {"nodes": 63, "edges": 60}
    assert_same_instance(component)


def test_showcase_vehicle_style_keeps_its_icon_shape():
    source = open("examples/demos/graph_workbench_showcase.py", encoding="utf-8").read()

    risk_rule = source.split('StyleRule(\n        "node[risk >= 8]"', 1)[1].split(
        "),", 1
    )[0]
    assert '"shape"' not in risk_rule


def test_progressive_loading_can_load_after_repeated_resets(page: Page):
    page.locator('a[href="progressive_loading"]').click()
    component = get_component(page)
    mark_instance(component)
    for _ in range(3):
        component.locator("#progressiveLoadingButton").click()
        expect(component.locator("#progressiveLoadingStatus")).to_have_text(
            "120 / 600", timeout=15000
        )
        expect(component.locator("#progressiveLoadingButton")).to_be_enabled()
        wait_for_counts(component, {"nodes": 123, "edges": 120})
        assert_same_instance(component)
        page.get_by_role("button", name="Reset progressive graph").click()
        expect(component.locator("#progressiveLoadingStatus")).to_have_text("60 / 600")
        wait_for_counts(component, {"nodes": 63, "edges": 60})
        assert_same_instance(component)


def test_progressive_snippet_positions_batches_without_moving_existing_nodes(
    page: Page, serve_streamlit
):
    port = serve_streamlit(ROOT_DIR / "docs/snippets/progressive_loading.py")
    page.goto(f"http://localhost:{port}")
    component = get_component(page)
    component.locator("#progressiveLoadingButton").click()
    expect(component.locator("#progressiveLoadingStatus")).to_have_text("100 / 10,000")
    expect(component.locator("#progressiveLoadingButton")).to_be_enabled()
    wait_for_counts(component, {"nodes": 100, "edges": 0})
    first_positions = positions(component)
    assert len(first_positions) == 100
    assert len({(p["x"], p["y"]) for p in first_positions.values()}) == 100
    mark_instance(component)
    before = viewport(component)
    component.locator("#progressiveLoadingButton").click()
    expect(component.locator("#progressiveLoadingStatus")).to_have_text("200 / 10,000")
    expect(component.locator("#progressiveLoadingButton")).to_be_enabled()
    wait_for_counts(component, {"nodes": 200, "edges": 0})
    after_positions = positions(component)
    assert len(after_positions) == 200
    assert all(after_positions[key] == value for key, value in first_positions.items())
    assert viewport(component) == before
    assert_same_instance(component)


@pytest.fixture
def loading_fixture(page: Page, serve_streamlit):
    port = serve_streamlit(ROOT_DIR / "tests/apps/progressive_loading.py")
    page.goto(f"http://localhost:{port}")
    component = get_component(page)
    mark_instance(component)
    return component


def test_loading_requests_retry_on_non_localhost_http(http_page, serve_streamlit):
    page = http_page
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    port = serve_streamlit(ROOT_DIR / "tests/apps/progressive_loading.py")
    page.goto(f"http://workbench.test:{port}")
    component = get_component(page)
    assert page.evaluate(
        "!window.isSecureContext && typeof crypto.randomUUID === 'undefined'"
    )
    mark_instance(component)
    button = component.locator("#progressiveLoadingButton")
    button.click()
    expect(page.get_by_text("Source unavailable", exact=True)).to_be_visible()
    expect(button).to_be_enabled()
    assert get_total_counts(component) == {"nodes": 1, "edges": 0}
    page.get_by_role("button", name="Rerun unchanged").click()
    expect(page.get_by_test_id("stMetricValue")).to_have_text("1")
    page.get_by_role("combobox", name="Response").click()
    page.get_by_role("option", name="Success", exact=True).click()
    for count in (2, 3):
        button.click()
        wait_for_counts(component, {"nodes": count, "edges": 0})
        expect(button).to_be_enabled()
        expect(page.get_by_test_id("stMetricValue")).to_have_text(str(count))
        assert_same_instance(component)
    expect(page.get_by_test_id("stException")).to_have_count(0)
    assert not errors


def test_failed_load_can_retry_without_remount(page: Page, loading_fixture):
    component = loading_fixture
    button = component.locator("#progressiveLoadingButton")
    button.click()
    expect(page.get_by_text("Source unavailable", exact=True)).to_be_visible()
    expect(button).to_be_enabled()
    assert get_total_counts(component) == {"nodes": 1, "edges": 0}
    page.get_by_role("button", name="Rerun unchanged").click()
    expect(button).to_be_enabled()
    page.get_by_role("combobox", name="Response").click()
    page.get_by_role("option", name="Success", exact=True).click()
    button.click()
    wait_for_counts(component, {"nodes": 2, "edges": 0})
    expect(button).to_be_enabled()
    expect(page.get_by_test_id("stMetricValue")).to_have_text("2")
    assert_same_instance(component)


def test_pending_load_ignores_stale_ack_reruns_and_duplicate_clicks(
    page: Page, loading_fixture
):
    component = loading_fixture
    page.get_by_role("combobox", name="Response").click()
    page.get_by_role("option", name="Deferred", exact=True).click()
    button = component.locator("#progressiveLoadingButton")
    button.evaluate("button => { button.click(); button.click(); }")
    expect(page.get_by_text("Waiting for response", exact=True)).to_be_visible()
    expect(button).to_be_disabled()
    for name in ("Rerun unchanged", "Send stale acknowledgment"):
        page.get_by_role("button", name=name).click()
        expect(button).to_be_disabled()
    expect(page.get_by_test_id("stMetricValue")).to_have_text("1")
    page.get_by_role("button", name="Complete pending request").click()
    expect(button).to_be_enabled()
    button.click()
    expect(page.get_by_test_id("stMetricValue")).to_have_text("2")
    expect(button).to_be_disabled()
    assert_same_instance(component)


@pytest.mark.parametrize("response", ["Empty", "Duplicate"])
def test_load_can_complete_without_new_nodes(page: Page, loading_fixture, response):
    component = loading_fixture
    page.get_by_role("combobox", name="Response").click()
    page.get_by_role("option", name=response, exact=True).click()
    button = component.locator("#progressiveLoadingButton")
    button.click()
    expect(page.get_by_text("Completed", exact=True)).to_be_visible()
    expect(button).to_have_attribute("data-pending", "false")
    if response == "Empty":
        expect(button).to_be_disabled()
        expect(button).to_have_attribute("title", "All records loaded")
    else:
        expect(button).to_be_enabled()
    assert get_total_counts(component) == {"nodes": 1, "edges": 0}
    assert_same_instance(component)


def test_progressive_loading_reaches_last_page_without_losing_state(page: Page):
    page.locator('a[href="progressive_loading"]').click()
    component = get_component(page)
    mark_instance(component)
    initial_positions = positions(component)
    for count in range(120, 601, 60):
        component.locator("#progressiveLoadingButton").click()
        expect(component.locator("#progressiveLoadingStatus")).to_have_text(
            f"{count} / 600", timeout=15000
        )
        wait_for_counts(component, {"nodes": count + 3, "edges": count})
    expect(component.locator("#progressiveLoadingButton")).to_be_disabled()
    expect(component.locator("#progressiveLoadingButton")).to_have_attribute(
        "title", "All records loaded"
    )
    final_positions = positions(component)
    assert all(
        final_positions[key] == value for key, value in initial_positions.items()
    )
    component.locator("#graphSearchInput").fill("vehicle-0600")
    component.locator("#graphSearchApply").click()
    page.wait_for_function(
        """element => {
            const cy = element._cyreg.cy;
            const matches = cy.nodes('.search-match');
            const node = cy.getElementById('vehicle-0600');
            return matches.length === 1 && matches[0].id() === node.id() &&
                Math.abs(node.renderedPosition('x') - cy.width() / 2) < 50 &&
                Math.abs(node.renderedPosition('y') - cy.height() / 2) < 50;
        }""",
        arg=get_cy(component).element_handle(),
        timeout=10000,
    )
    select_nodes(component, ["vehicle-0600"])
    open_toolbox_menu(component, "analysisControls")
    component.locator("#analysisDegree").click()
    expect(page.get_by_test_id("stJson").last).to_contain_text("degree", timeout=10000)
    open_toolbox_menu(component, "selectionControls")
    component.locator("#selectionClear").click()
    expect(component.locator("#selectionStatusCount")).to_have_text("0 selected")
    assert get_total_counts(component) == {"nodes": 603, "edges": 600}
    assert_same_instance(component)


def run_demo_bfs(page, component, root, expected_count):
    select_nodes(component, [root])
    open_toolbox_menu(component, "analysisControls")
    expect(component.locator("#analysisBfs")).to_be_enabled()
    component.locator("#analysisBfs").click()
    expect(
        page.get_by_text(
            re.compile(
                rf"^BFS root: {re.escape(root)} \| Reached: {expected_count} nodes \|"
            )
        )
    ).to_be_visible(timeout=15000)
    expect(page.get_by_test_id("stException")).to_have_count(0)


def downloaded_bfs_rows(page):
    with page.expect_download() as download:
        page.get_by_role("button", name="Download BFS records").click()
    with download.value.path().open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def test_progressive_bfs_compares_roots_and_returns_records(page: Page, run_streamlit):
    page.goto(f"http://localhost:{run_streamlit}/progressive_loading")
    component = get_component(page)
    wait_for_app_idle(page)
    mark_instance(component)
    expect(component.locator("#selectionStatusMode")).to_have_text("Single")
    open_toolbox_menu(component, "analysisControls")
    expect(component.locator("#analysisBfs")).to_be_disabled()
    for root, max_hops in [
        ("location-north", 1),
        ("vehicle-0001", 2),
        ("vehicle-0002", 2),
    ]:
        run_demo_bfs(page, component, root, 21)
        rows = downloaded_bfs_rows(page)
        assert len(rows) == 21
        assert rows[0]["id"] == root and rows[0]["hops"] == "0"
        assert max(int(row["hops"]) for row in rows) == max_hops
        expected_hub = (
            "location-central" if root == "vehicle-0002" else "location-north"
        )
        assert {row["id"] for row in rows if row["type"] == "LOCATION"} == {
            expected_hub
        }
        assert_same_instance(component)


def test_progressive_bfs_changes_when_new_connections_arrive(page: Page, run_streamlit):
    page.goto(f"http://localhost:{run_streamlit}/progressive_loading")
    component = get_component(page)
    wait_for_app_idle(page)
    mark_instance(component)
    page.get_by_test_id("stCheckbox").get_by_text(
        "Include cross-location sightings", exact=True
    ).click()
    expect(
        page.get_by_label("Include cross-location sightings", exact=True)
    ).to_be_checked()
    wait_for_app_idle(page)
    for loaded, edges, reached, groups, hops in [
        (60, 60, 21, 3, 1),
        (120, 121, 82, 2, 3),
        (180, 182, 183, 1, 5),
    ]:
        if loaded > 60:
            component.locator("#progressiveLoadingButton").click()
            expect(
                page.get_by_test_id("stAlertContentWarning").get_by_text(
                    "More records have been loaded since this BFS. Run BFS again to update the result."
                )
            ).to_be_visible()
        wait_for_counts(component, {"nodes": loaded + 3, "edges": edges})
        run_demo_bfs(page, component, "location-north", reached)
        assert (
            get_cy(component).evaluate(
                "el => el._cyreg.cy.elements().components().length"
            )
            == groups
        )
        rows = downloaded_bfs_rows(page)
        assert len(rows) == reached
        assert max(int(row["hops"]) for row in rows) == hops
        assert_same_instance(component)
    page.get_by_test_id("stCheckbox").get_by_text(
        "Include cross-location sightings", exact=True
    ).click()
    expect(
        page.get_by_label("Include cross-location sightings", exact=True)
    ).not_to_be_checked()
    wait_for_counts(component, {"nodes": 63, "edges": 60})
    expect(page.get_by_role("button", name="Download BFS records")).to_have_count(0)
    assert_same_instance(component)
    component.locator("#progressiveLoadingButton").click()
    wait_for_counts(component, {"nodes": 123, "edges": 120})
    run_demo_bfs(page, component, "location-north", 41)


def test_progressive_shortest_path_connects_after_loading(page: Page, run_streamlit):
    page.goto(f"http://localhost:{run_streamlit}/progressive_loading")
    component = get_component(page)
    wait_for_app_idle(page)
    mark_instance(component)
    page.get_by_test_id("stCheckbox").get_by_text(
        "Include cross-location sightings", exact=True
    ).click()
    page.get_by_role("radio", name="Two nodes", exact=True).click()
    expect(component.locator("#selectionStatusMode")).to_have_text("Multiple")
    select_nodes(component, ["location-north"])
    open_toolbox_menu(component, "analysisControls")
    expect(component.locator("#analysisShortestPath")).to_be_disabled()
    select_nodes(component, ["location-north", "location-south"])
    initial_view = viewport(component)
    initial_positions = positions(component)
    for count in (60, 120, 180):
        if count > 60:
            component.locator("#progressiveLoadingButton").click()
            wait_for_counts(
                component, {"nodes": count + 3, "edges": count + count // 60 - 1}
            )
        open_toolbox_menu(component, "analysisControls")
        expect(component.locator("#analysisShortestPath")).to_be_enabled()
        component.locator("#analysisShortestPath").click()
        expect(
            page.get_by_text(
                f"Shortest path: location-north to location-south | Snapshot: {count} loaded vehicles",
                exact=True,
            )
        ).to_be_visible(timeout=15000)
        if count < 180:
            expect(
                page.get_by_test_id("stAlertContentInfo").get_by_text(
                    "No path between these nodes in the displayed graph at this checkpoint.",
                    exact=True,
                )
            ).to_be_visible()
            expect(
                page.get_by_role("button", name="Download path relationships")
            ).to_have_count(0)
        else:
            expect(page.get_by_test_id("stAlertContentSuccess")).to_contain_text(
                "Shortest path found: 4 relationships."
            )
        assert_same_instance(component)
        assert viewport(component) == initial_view
        current_positions = positions(component)
        assert all(
            current_positions[key] == value for key, value in initial_positions.items()
        )
    with page.expect_download() as download:
        page.get_by_role("button", name="Download path relationships").click()
    with download.value.path().open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    assert {row["id"] for row in rows} == {
        "assignment-0061",
        "sighting-0061",
        "assignment-0122",
        "sighting-0122",
    }
    assert (
        get_cy(component).evaluate(
            "el => el._cyreg.cy.edges('.analysis-result').length"
        )
        == 4
    )
    open_toolbox_menu(component, "selectionControls")
    component.locator("#selectionClear").click()
    expect(component.locator("#selectionStatusCount")).to_have_text("0 selected")
    expect(page.get_by_test_id("stJson").last).to_contain_text('"action":"selection"')
    assert (
        get_cy(component).evaluate(
            "el => el._cyreg.cy.elements('.analysis-result').length"
        )
        == 0
    )
    expect(
        page.get_by_role("button", name="Download path relationships")
    ).to_be_visible()
    wait_for_app_idle(page)
    assert viewport(component) == initial_view
    assert_same_instance(component)
    select_nodes(component, ["vehicle-0001", "vehicle-0004"])
    open_toolbox_menu(component, "analysisControls")
    component.locator("#analysisShortestPath").click()
    expect(page.get_by_test_id("stAlertContentSuccess")).to_contain_text(
        "Shortest path found: 2 relationships."
    )
    page.get_by_role("radio", name="One node", exact=True).click()
    expect(component.locator("#selectionStatusMode")).to_have_text("Single")
    run_demo_bfs(page, component, "location-north", 183)
    page.get_by_role("button", name="Reset progressive graph").click()
    wait_for_counts(component, {"nodes": 63, "edges": 60})
    expect(
        page.get_by_role("button", name="Download path relationships")
    ).to_have_count(0)
    expect(page.get_by_role("button", name="Download BFS records")).to_have_count(0)
    expect(page.get_by_test_id("stException")).to_have_count(0)


def test_progressive_loading_links_to_scale_activity(page: Page, run_streamlit):
    page.goto(f"http://localhost:{run_streamlit}/progressive_loading")
    scale = page.get_by_text("Open the Progressive Loading Scale Test", exact=True)
    expect(scale).to_be_visible(timeout=30000)
    scale.click()
    expect(page).to_have_url(
        f"http://localhost:{run_streamlit}/progressive_loading_scale", timeout=30000
    )
    expect(page).to_have_title("Progressive Loading Scale Test")
    expect(page.get_by_label("Graph size", exact=True)).to_be_visible()
