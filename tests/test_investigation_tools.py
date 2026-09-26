import json
import time

from playwright.sync_api import Page, expect

from graph_test_helpers import (
    drag_node,
    get_component,
    get_cy,
    get_node_view,
    get_node_pos,
    get_visible_counts,
    open_toolbox_menu,
    select_nodes,
)

PAGE_NAME = "Investigation Tools"


def get_visible_node_ids(component):
    return get_cy(component).evaluate("""(element) => {
        const cy = element._cyreg.cy;
        return cy.nodes(":visible").map((node) => node.id()).sort();
    }""")


def get_search_state(component):
    return get_cy(component).evaluate("""(element) => {
        const cy = element._cyreg.cy;
        return {
            pan: cy.pan(),
            visibleNodeIds: cy.nodes(":visible").map((node) => node.id()).sort(),
            hiddenNodeIds: cy.nodes(":hidden").map((node) => node.id()).sort(),
            searchMatchNodeIds: cy.nodes(".search-match").map((node) => node.id()).sort(),
            searchMatchEdgeIds: cy.edges(".search-match").map((edge) => edge.id()).sort(),
            selectedNodeIds: cy.nodes(":selected").map((node) => node.id()).sort(),
            selectedEdgeIds: cy.edges(":selected").map((edge) => edge.id()).sort(),
        };
    }""")


def get_rendered_node_view(component, node_id):
    return get_cy(component).evaluate(
        """(element, nodeId) => {
            const cy = element._cyreg.cy;
            const position = cy.getElementById(nodeId).renderedPosition();
            return {
                position,
                width: element.clientWidth,
                height: element.clientHeight,
                zoom: cy.zoom(),
            };
        }""",
        node_id,
    )


def wait_for_visible_node_ids(component, expected_ids):
    expected_ids = sorted(expected_ids)
    deadline = time.time() + 5
    while time.time() < deadline:
        node_ids = get_visible_node_ids(component)
        if node_ids == expected_ids:
            return
        time.sleep(0.1)
    assert get_visible_node_ids(component) == expected_ids


def wait_for_search_match_node_ids(component, expected_ids):
    expected_ids = sorted(expected_ids)
    deadline = time.time() + 5
    while time.time() < deadline:
        node_ids = get_search_state(component)["searchMatchNodeIds"]
        if node_ids == expected_ids:
            return
        time.sleep(0.1)
    assert get_search_state(component)["searchMatchNodeIds"] == expected_ids


def drag_selection_box_around_nodes(page: Page, component, node_ids):
    cy = get_cy(component)
    cy.scroll_into_view_if_needed()
    bounds = cy.evaluate(
        """(element, ids) => {
            const cy = element._cyreg.cy;
            return cy.nodes().filter(n => ids.includes(n.id()))
                .renderedBoundingBox({includeLabels: false});
        }""",
        node_ids,
    )
    box = cy.bounding_box()
    assert box is not None

    start_x = box["x"] + bounds["x1"] - 12
    start_y = box["y"] + bounds["y1"] - 12
    end_x = box["x"] + bounds["x2"] + 12
    end_y = box["y"] + bounds["y2"] + 12

    page.mouse.move(start_x, start_y)
    page.mouse.down()
    page.mouse.move(end_x, end_y, steps=20)
    page.mouse.up()
    page.wait_for_timeout(500)


def get_blank_canvas_position(component):
    return get_cy(component).evaluate("""(element) => {
        const cy = element._cyreg.cy;
        const nodes = cy.nodes(":visible");
        const bounds = element.getBoundingClientRect();
        const root = element.getRootNode();
        for (let y = 100; y < element.clientHeight - 20; y += 20) {
            for (let x = 20; x < element.clientWidth - 20; x += 20) {
                const hit = root.elementFromPoint(bounds.left + x, bounds.top + y);
                if (!hit || !element.contains(hit)) continue;
                const overNode = nodes.some((node) => {
                    const bounds = node.renderedBoundingBox();
                    return x >= bounds.x1 && x <= bounds.x2 &&
                        y >= bounds.y1 && y <= bounds.y2;
                });
                if (!overNode) {
                    return {x, y};
                }
            }
        }
        throw new Error("No blank canvas position found");
    }""")


def drag_blank_canvas(page: Page, component, dx=80, dy=45):
    cy = get_cy(component)
    cy.scroll_into_view_if_needed()
    start = get_blank_canvas_position(component)
    box = cy.bounding_box()
    assert box is not None

    page.mouse.move(box["x"] + start["x"], box["y"] + start["y"])
    page.mouse.down()
    page.mouse.move(
        box["x"] + start["x"] + dx,
        box["y"] + start["y"] + dy,
        steps=12,
    )
    page.mouse.up()
    page.wait_for_timeout(300)


def wait_for_node_near_center(component, node_id):
    deadline = time.time() + 5
    last_view = None
    while time.time() < deadline:
        view = get_rendered_node_view(component, node_id)
        last_view = view
        center_x = view["width"] / 2
        center_y = view["height"] / 2
        if (
            abs(view["position"]["x"] - center_x) <= view["width"] * 0.15
            and abs(view["position"]["y"] - center_y) <= view["height"] * 0.15
        ):
            return
        time.sleep(0.1)
    assert last_view is not None
    assert abs(last_view["position"]["x"] - last_view["width"] / 2) <= (
        last_view["width"] * 0.15
    )
    assert abs(last_view["position"]["y"] - last_view["height"] / 2) <= (
        last_view["height"] * 0.15
    )


def test_investigation_tools_render_controls(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")
    component = get_component(page)

    expect(component.locator("#searchPanel")).to_be_visible()
    expect(component.locator("#toolbox")).to_be_visible()
    expect(component.locator("#graphStatsButton")).to_be_visible()
    expect(component.locator("#canvasModeControls")).to_be_visible()
    expect(component.locator("#canvasModePan")).to_have_attribute(
        "aria-pressed", "false"
    )
    expect(component.locator("#canvasModeBox")).to_have_attribute(
        "aria-pressed", "true"
    )
    expect(component.locator("#selectionStatus")).to_be_visible()
    expect(component.locator("#selectionStatusMode")).to_have_text("Box")
    expect(component.locator("#selectionStatusCount")).to_have_text("0 selected")
    for menu_id, button_ids in {
        "exploreControls": [
            "nodeActionsNeighbors",
            "nodeActionsIncoming",
            "nodeActionsOutgoing",
        ],
        "selectionControls": [
            "selectionSelectAll",
            "selectionClear",
            "selectionFocus",
            "selectionHideUnselected",
            "selectionRestore",
        ],
        "analysisControls": [
            "analysisShortestPath",
            "analysisBfs",
            "analysisDfs",
            "analysisComponents",
            "analysisDegree",
        ],
        "toolbar": [
            "toolbarExport",
            "toolbarExportFull",
            "toolbarExportSelected",
            "toolbarExportPng",
            "toolbarExportJpg",
            "toolbarExportPositions",
        ],
    }.items():
        open_toolbox_menu(component, menu_id)
        for button_id in button_ids:
            expect(component.locator(f"#{button_id}")).to_be_visible()
    expect(page.get_by_role("heading", name="Try These Checks")).to_be_visible()


def expect_stats_match_graph(component):
    counts = get_visible_counts(component)
    component.locator("#graphStatsButton").click()
    expect(component.locator("#graphStatsDialog")).to_be_visible()
    for key, value_id in {
        "shownNodes": "graphStatsShownNodes",
        "hiddenNodes": "graphStatsHiddenNodes",
        "totalNodes": "graphStatsTotalNodes",
        "shownEdges": "graphStatsShownEdges",
        "hiddenEdges": "graphStatsHiddenEdges",
        "totalEdges": "graphStatsTotalEdges",
    }.items():
        expect(component.locator(f"#{value_id}")).to_have_text(str(counts[key]))
    component.locator("#graphStatsClose").click()
    expect(component.locator("#graphStatsDialog")).to_be_hidden()


def test_selection_payload_and_search_highlights_without_hiding(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")
    component = get_component(page)

    full_node_ids = get_visible_node_ids(component)
    vehicle_pos = get_node_pos("vehicle", component)
    get_cy(component).click(position=vehicle_pos)
    returned = page.get_by_test_id("stJson")
    expect(returned).to_contain_text("selection", timeout=10000)
    expect(returned).to_contain_text("vehicle")
    expect(returned).to_contain_text("connected_node_ids")
    expect(returned).to_contain_text("selected_elements")
    expect(
        page.get_by_role("heading", name="Returned Records As A Dataframe")
    ).to_be_visible()
    expect(
        page.get_by_text("Showing selected_elements from the latest event.")
    ).to_be_visible()

    component.locator("#graphSearchInput").fill("time")
    component.locator("#graphSearchApply").click()
    expect(component.locator("#graphSearchStatus")).to_contain_text("matches")
    state = get_search_state(component)
    assert state["visibleNodeIds"] == full_node_ids
    assert state["hiddenNodeIds"] == []
    assert "time_0814" in state["searchMatchNodeIds"]
    assert "time_0910" in state["searchMatchNodeIds"]
    assert "time_0814" in state["selectedNodeIds"]
    assert "time_0910" in state["selectedNodeIds"]
    expect(returned).to_contain_text("search", timeout=10000)
    expect(returned).to_contain_text("matched_elements")
    expect(returned).to_contain_text("time_0910")
    expect_stats_match_graph(component)

    component.locator("#graphSearchClear").click()
    wait_for_search_match_node_ids(component, [])
    state = get_search_state(component)
    assert state["visibleNodeIds"] == full_node_ids
    assert state["hiddenNodeIds"] == []
    expect_stats_match_graph(component)


def test_real_mouse_box_selection_selects_nodes_without_panning(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")
    component = get_component(page)

    before = get_search_state(component)
    drag_selection_box_around_nodes(page, component, ["vehicle", "escort_vehicle"])
    state = get_search_state(component)

    assert state["selectedNodeIds"] == ["escort_vehicle", "vehicle"]
    assert abs(state["pan"]["x"] - before["pan"]["x"]) < 1
    assert abs(state["pan"]["y"] - before["pan"]["y"]) < 1
    expect(component.locator("#selectionStatusCount")).to_have_text("2 nodes selected")
    returned = page.get_by_test_id("stJson")
    expect(returned).to_contain_text("selection", timeout=10000)
    expect(returned).to_contain_text("selected_node_ids")
    expect(returned).to_contain_text("escort_vehicle")
    expect(returned).to_contain_text("vehicle")

    before_drag = get_node_view(component, "service_depot")
    after_drag = drag_node(page, component, "service_depot", dx=-65, dy=25)
    assert after_drag["model"]["x"] < before_drag["model"]["x"] - 25
    assert after_drag["model"]["y"] > before_drag["model"]["y"] + 8


def test_canvas_mode_switch_separates_panning_from_box_selection(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")
    component = get_component(page)

    before = get_search_state(component)
    component.locator("#canvasModePan").click()
    expect(component.locator("#canvasModePan")).to_have_attribute(
        "aria-pressed", "true"
    )
    expect(component.locator("#canvasModeBox")).to_have_attribute(
        "aria-pressed", "false"
    )
    assert (
        get_cy(component).evaluate(
            "(element) => element._cyreg.cy.boxSelectionEnabled()"
        )
        is False
    )

    vehicle_pos = get_node_pos("vehicle", component)
    get_cy(component).click(position=vehicle_pos)
    expect(component.locator("#selectionStatusCount")).to_have_text("1 node selected")
    expect(component.locator("#canvasModePan")).to_have_attribute(
        "aria-pressed", "true"
    )
    assert (
        get_cy(component).evaluate(
            "(element) => element._cyreg.cy.boxSelectionEnabled()"
        )
        is False
    )
    get_cy(component).evaluate(
        '(element) => element._cyreg.cy.elements(":selected").unselect()'
    )
    expect(component.locator("#selectionStatusCount")).to_have_text("0 selected")

    drag_blank_canvas(page, component)
    after_pan = get_search_state(component)
    assert abs(after_pan["pan"]["x"] - before["pan"]["x"]) > 25
    assert abs(after_pan["pan"]["y"] - before["pan"]["y"]) > 15
    assert after_pan["selectedNodeIds"] == []

    component.locator("#canvasModeBox").click()
    expect(component.locator("#canvasModePan")).to_have_attribute(
        "aria-pressed", "false"
    )
    expect(component.locator("#canvasModeBox")).to_have_attribute(
        "aria-pressed", "true"
    )
    assert (
        get_cy(component).evaluate(
            "(element) => element._cyreg.cy.boxSelectionEnabled()"
        )
        is True
    )

    before_box = get_search_state(component)
    drag_selection_box_around_nodes(page, component, ["vehicle", "escort_vehicle"])
    after_box = get_search_state(component)
    assert after_box["selectedNodeIds"] == ["escort_vehicle", "vehicle"]
    assert abs(after_box["pan"]["x"] - before_box["pan"]["x"]) < 1
    assert abs(after_box["pan"]["y"] - before_box["pan"]["y"]) < 1


def test_box_selection_is_easy_to_clear_or_toggle(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")
    component = get_component(page)
    cy = get_cy(component)

    drag_selection_box_around_nodes(page, component, ["vehicle", "escort_vehicle"])
    expect(component.locator("#selectionStatusCount")).to_have_text("2 nodes selected")

    cy.click(position=get_blank_canvas_position(component))
    expect(component.locator("#selectionStatusCount")).to_have_text("0 selected")
    assert get_search_state(component)["selectedNodeIds"] == []

    cy.click(position=get_node_pos("vehicle", component))
    expect(component.locator("#selectionStatusCount")).to_have_text("1 node selected")
    close_panel = component.locator("#infopanelClear")
    expect(close_panel).to_be_visible()
    close_panel.click()
    expect(component.locator("#selectionStatusCount")).to_have_text("0 selected")
    expect(component.locator("#selectionShowDetails")).to_be_checked()

    toggle_node_id = "service_depot"
    cy.click(position=get_node_pos(toggle_node_id, component))
    expect(component.locator("#selectionStatusCount")).to_have_text("1 node selected")
    expect(component.locator("#infopanel")).to_be_visible()
    cy.click(position=get_node_pos(toggle_node_id, component))
    expect(component.locator("#selectionStatusCount")).to_have_text("0 selected")
    assert get_search_state(component)["selectedNodeIds"] == []


def test_text_search_focuses_matched_nodes_before_edge_context(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")
    component = get_component(page)

    full_node_ids = get_visible_node_ids(component)
    component.locator("#graphSearchInput").fill("phone")
    component.locator("#graphSearchApply").click()
    wait_for_search_match_node_ids(component, ["phone"])
    wait_for_node_near_center(component, "phone")

    state = get_search_state(component)
    assert state["visibleNodeIds"] == full_node_ids
    assert state["hiddenNodeIds"] == []
    assert "e_maya_phone" in state["searchMatchEdgeIds"]
    assert "e_omar_phone" in state["searchMatchEdgeIds"]
    assert "e_phone_tower" in state["searchMatchEdgeIds"]


def test_info_panel_follows_latest_selected_node_in_box_mode(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")
    component = get_component(page)
    props = component.locator("#infopanelProps")
    status = component.locator("#selectionStatus")

    vehicle_pos = get_node_pos("vehicle", component)
    get_cy(component).click(position=vehicle_pos)
    expect(status).to_have_attribute("data-mode", "box")
    expect(status).to_have_attribute("data-has-selection", "true")
    expect(component.locator("#selectionStatusCount")).to_have_text("1 node selected")
    expect(props).to_contain_text("ABC123", timeout=10000)
    expect(props).to_contain_text("Selection mode")
    expect(props).to_contain_text("Box")
    expect(props).to_contain_text("1 node selected")

    time_pos = get_node_pos("time_0814", component)
    get_cy(component).click(position=time_pos)
    expect(component.locator("#selectionStatusCount")).to_have_text("2 nodes selected")
    expect(props).to_contain_text("02 Sep 2024 08:14", timeout=10000)
    expect(props).to_contain_text("2 nodes selected")
    expect(props).to_contain_text("Showing")
    expect(props).not_to_contain_text("ABC123")


def test_neighbor_action_and_analysis_return_values(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")
    component = get_component(page)

    vehicle_pos = get_node_pos("vehicle", component)
    get_cy(component).click(position=vehicle_pos)
    open_toolbox_menu(component, "exploreControls")
    component.locator("#nodeActionsNeighbors").click()
    wait_for_visible_node_ids(
        component,
        ["case", "escort_vehicle", "maya", "noah", "omar", "vehicle"],
    )

    open_toolbox_menu(component, "selectionControls")
    component.locator("#selectionRestore").click()
    select_nodes(component, ["vehicle"])
    page.wait_for_timeout(500)
    open_toolbox_menu(component, "analysisControls")
    expect(component.locator("#analysisDegree")).to_be_enabled()
    component.locator("#analysisDegree").click()
    returned = page.get_by_test_id("stJson")
    expect(returned).to_contain_text("degree", timeout=10000)
    expect(returned).to_contain_text("vehicle")

    select_nodes(component, ["case", "time_0814"])
    page.wait_for_timeout(500)
    open_toolbox_menu(component, "analysisControls")
    expect(component.locator("#analysisShortestPath")).to_be_enabled()
    component.locator("#analysisShortestPath").click()
    expect(returned).to_contain_text("shortest_path", timeout=10000)
    expect(returned).to_contain_text("time_0814")


def test_each_analysis_action_returns_payload(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")
    component = get_component(page)
    returned = page.get_by_test_id("stJson")

    analysis_cases = [
        (["case", "time_0910"], "analysisShortestPath", ["shortest_path", "time_0910"]),
        (["vehicle"], "analysisBfs", ["bfs", "root_id", "vehicle"]),
        (["vehicle"], "analysisDfs", ["dfs", "root_id", "vehicle"]),
        ([], "analysisComponents", ["connected_components", "components"]),
        (["time_0814"], "analysisDegree", ["degree", "indegree", "outdegree"]),
    ]

    for selected_ids, button_id, expected_terms in analysis_cases:
        select_nodes(component, selected_ids)
        page.wait_for_timeout(500)
        open_toolbox_menu(component, "analysisControls")
        button = component.locator(f"#{button_id}")
        expect(button).to_be_enabled()
        button.click()
        for term in expected_terms:
            expect(returned).to_contain_text(term, timeout=10000)


def test_position_export_downloads_json(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")
    component = get_component(page)

    with page.expect_download() as download_info:
        open_toolbox_menu(component, "toolbar")
        component.locator("#toolbarExportPositions").click()
    download = download_info.value
    assert download.suggested_filename == "graph-positions.json"

    path = download.path()
    assert path is not None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    assert sorted(item["id"] for item in data["positions"]) == [
        "case",
        "cell_tower",
        "depot_camera",
        "escort_vehicle",
        "harbor_camera",
        "lina",
        "maya",
        "noah",
        "omar",
        "phone",
        "service_depot",
        "time_0814",
        "time_0910",
        "vehicle",
    ]
