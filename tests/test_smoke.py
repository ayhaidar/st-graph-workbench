import time
import re
from math import hypot
from pathlib import Path

from playwright.sync_api import Page, expect

from graph_test_helpers import (
    click_nav,
    get_edge_ids as get_cy_edge_ids,
    get_node_ids as get_cy_node_ids,
    open_context_menu_for_node,
    open_toolbox_menu as open_component_menu,
    select_node,
    select_nodes,
    wait_for_app_idle,
    wait_for_cy_ready,
    wait_for_node_ids as wait_for_cy_node_ids,
)


def get_cy_visible_counts(component):
    return component.locator("#cy").evaluate("""(element) => {
        const cy = element._cyreg?.cy;
        if (!cy) {
            return {
                nodes: 0,
                edges: 0,
                visible_nodes: 0,
                visible_edges: 0,
            };
        }
        return {
            nodes: cy.nodes().length,
            edges: cy.edges().length,
            visible_nodes: cy.nodes(":visible").length,
            visible_edges: cy.edges(":visible").length,
        };
    }""")


def wait_for_cy_edge_count(component, expected_count):
    deadline = time.time() + 10
    while time.time() < deadline:
        edge_ids = get_cy_edge_ids(component)
        if len(edge_ids) == expected_count:
            return edge_ids
        time.sleep(0.1)
    assert len(get_cy_edge_ids(component)) == expected_count


def expand_cy_node(component, node_id):
    select_node(component, node_id)
    expect(component.locator("#selectionStatusCount")).to_have_text("1 node selected")

    expand = component.locator("#nodeActionsExpand")
    expect(expand).to_be_enabled(timeout=10000)
    expand.click()


def right_click_expand_cy_node(component, node_id):
    menu = open_context_menu_for_node(component, node_id)
    action = menu.locator("#graphContextMenuExpand")
    expect(action).to_be_enabled(timeout=10000)
    action.click()


def test_run(page: Page):
    expect(page).to_have_title("Build your first graph")


def test_readme_page_shows_code_output(page: Page):
    click_nav(page, "Readme")
    page.wait_for_load_state("networkidle")

    expect(page.locator("img").first).to_be_visible()
    expect(page.get_by_role("heading", name="Library stack").first).to_be_visible()
    expect(page.get_by_text("Cytoscape.js").first).to_be_visible()
    expect(page.get_by_text("Pandas").first).to_be_visible()
    expect(page.get_by_text("Components v2").first).to_be_visible()
    expect(page.get_by_role("heading", name="On this page")).to_be_visible()
    expect(
        page.get_by_role("heading", name="What the library provides")
    ).to_be_visible()
    expect(page.get_by_role("heading", name="Quick start code output")).to_be_visible()
    expect(page.locator("#container").first).to_be_visible(timeout=10000)
    expect(
        page.get_by_role("heading", name="Record helper code output")
    ).to_be_visible()
    expect(page.get_by_text("records_to_dataframe(...) output")).to_be_visible()
    expect(page.get_by_text("Dictionary description").first).to_be_visible()
    expect(page.locator("#container")).to_have_count(2)
    assert page.evaluate("""() => {
        const table = document.querySelector('[data-testid="stDataFrame"]');
        const graph = document.querySelector('#container');
        return Boolean(table.compareDocumentPosition(graph) & Node.DOCUMENT_POSITION_FOLLOWING);
    }""")
    expect(page.get_by_test_id("stException")).to_have_count(0)
    assert "<!-- example:" not in page.locator("body").inner_text()
    assert "<!-- live-output:" not in page.locator("body").inner_text()


def test_readme_screenshots_render_from_local_assets(page: Page):
    # The visual README must not depend on remote image hosting.
    page.route("https://raw.githubusercontent.com/**", lambda route: route.abort())
    click_nav(page, "Readme")
    captions = [
        "Shortest-path analysis highlights the four-edge route",
        "After collapsing Location 1, the graph retains both locations",
        "The CRUD tutorial's Graph record dialog prepares a Camera node",
    ]
    for caption in captions:
        image = page.get_by_test_id("stImage").filter(has_text=caption).locator("img")
        expect(image).to_be_visible(timeout=20000)
        expect(image).to_have_js_property("complete", True)
        assert image.evaluate("img => img.naturalWidth >= 450")
        assert "/media/" in image.get_attribute("src")
    expect(page.get_by_test_id("stException")).to_have_count(0)


def test_readme_selection_filters_evidence_and_clears(page: Page):
    click_nav(page, "Readme")
    component = page.locator("#container").nth(1)
    expect(component).to_be_visible(timeout=30000)
    wait_for_cy_ready(component)
    assert get_cy_node_ids(component) == ["ABC123", "camera-7"]
    assert get_cy_edge_ids(component) == ["sighting-1"]
    assert component.locator("#cy").evaluate("""element => {
        const cy = element._cyreg.cy;
        cy.scratch('_readmeTest', true);
        return cy.getElementById('ABC123').style('background-image').includes('directions_car');
    }""")
    expect(page.get_by_test_id("stMetricValue")).to_have_text("0")
    select_node(component, "ABC123")
    expect(page.get_by_test_id("stMetricValue")).to_have_text("2", timeout=15000)
    expect(page.get_by_test_id("stDataFrame")).to_have_count(5)
    select_nodes(component, [])
    expect(page.get_by_test_id("stMetricValue")).to_have_text("0", timeout=15000)
    expect(page.get_by_text("No element records selected.", exact=True)).to_be_visible()
    assert component.locator("#cy").evaluate(
        "element => element._cyreg.cy.scratch('_readmeTest') === true"
    )
    expect(page.get_by_test_id("stException")).to_have_count(0)


def test_component_renders_without_v1_iframe(page: Page):
    click_nav(page, "Node Styles")
    page.wait_for_load_state("networkidle")
    expect(page.locator("#container").first).to_be_visible(timeout=10000)
    expect(page.locator("iframe[title*='st_graph_workbench']")).to_have_count(0)


def test_investigation_tools_exposes_box_selection(page: Page):
    click_nav(page, "Investigation Tools")
    page.wait_for_load_state("networkidle")
    component = page.locator("#container").first
    expect(component).to_be_visible(timeout=10000)
    expect(component.locator("#selectionStatusMode")).to_have_text("Box")

    box_selection_enabled = component.locator("#cy").evaluate("""(element) => {
        return element._cyreg.cy.boxSelectionEnabled();
    }""")
    assert box_selection_enabled is True


def test_examples_docs_and_demos_render(page: Page):
    page_names = [
        "Graph Data Format",
        "Styling Guide",
        "Frontend Architecture",
        "Interactive CRUD",
        "Changelog",
        "Supported Icons",
        "Feature finder",
        "Graph Workbench Showcase",
        "Data Helpers And Commands",
        "Node Styles",
        "Edge Styles",
        "Layout Algorithms",
        "Investigation Tools",
        "Compound And Performance",
        "Interactive CRUD / Data Loading",
        "Editing And Viewport Tools",
        "Node Actions",
        "Components V2 Validation",
        "Event Listeners",
    ]

    for page_name in page_names:
        click_nav(page, page_name)
        page.wait_for_load_state("networkidle")
        expect(page.locator("[data-testid='stException']")).to_have_count(0)


def test_feature_finder_lists_and_filters_working_examples(page: Page):
    click_nav(page, "Feature finder")
    page.wait_for_load_state("networkidle")
    main = page.get_by_test_id("stMain")
    expect(main.get_by_role("link", name=re.compile("Node Styles$"))).to_be_visible()
    expect(main.get_by_role("heading", name="Complete page directory")).to_have_count(0)
    page.get_by_role("textbox", name="Find a feature", exact=True).fill("zz-no-match")
    page.get_by_role("textbox", name="Find a feature", exact=True).press("Enter")
    expect(main.get_by_text("No matching playgrounds.")).to_be_visible()


def test_data_helpers_commands_demo_renders_helper_api(page: Page):
    click_nav(page, "Data Helpers And Commands")
    page.wait_for_load_state("networkidle")

    expect(page.locator("#container").first).to_be_visible(timeout=10000)
    expect(page.get_by_role("heading", name="Validation")).to_be_visible()
    expect(page.get_by_text("The live sections below run").first).to_be_visible()
    expect(page.get_by_role("heading", name="Conversion options")).to_be_visible()
    expect(page.get_by_text("drop_missing=True").first).to_be_visible()


def assert_circle_positions(component):
    positions = component.locator("#cy").evaluate(
        "el => el._cyreg.cy.nodes().map(node => node.position())"
    )
    assert len(positions) == 7
    center_x = sum(position["x"] for position in positions) / len(positions)
    center_y = sum(position["y"] for position in positions) / len(positions)
    radii = [
        hypot(position["x"] - center_x, position["y"] - center_y)
        for position in positions
    ]
    assert min(radii) > 1
    assert max(radii) - min(radii) < 0.1, positions


def test_data_helpers_named_layout_command_reaches_cytoscape(page: Page):
    click_nav(page, "Data Helpers And Commands")
    page.wait_for_load_state("networkidle")
    component = page.locator("#container").first
    expect(component).to_be_visible(timeout=10000)
    wait_for_app_idle(page)
    wait_for_cy_ready(component)

    component.locator("#cy").evaluate(
        """(element) => {
            const cy = element._cyreg.cy;
            const originalLayout = cy.layout.bind(cy);
            cy.layout = (options) => {
                cy.__lastLayoutOptions = options;
                return originalLayout(options);
            };
        }"""
    )
    page.get_by_role("button", name="Run circle layout").click()

    deadline = time.time() + 10
    while time.time() < deadline:
        component = page.locator("#container").first
        layout_name = component.locator("#cy").evaluate(
            """(element) => element._cyreg?.cy?.__lastLayoutOptions?.name || null"""
        )
        if layout_name == "circle":
            break
        page.wait_for_timeout(100)
    else:
        assert layout_name == "circle"

    assert_circle_positions(component)
    expect(page.locator("[data-testid='stException']")).to_have_count(0)


def test_data_helpers_circle_layout_keeps_graph_during_slow_rerun(
    page: Page, serve_streamlit
):
    port = serve_streamlit(Path(__file__).parent / "apps" / "layout_command_rerun.py")
    page.goto(f"http://localhost:{port}")
    component = page.locator("#container").first
    wait_for_cy_ready(component)
    wait_for_app_idle(page)
    component.locator("#cy").evaluate(
        "el => el._cyreg.cy.scratch('circle-command-instance', true)"
    )
    page.get_by_role("button", name="Run circle layout").click()
    expect(
        page.get_by_test_id("stJson").filter(has_text="circle-layout-1")
    ).to_have_count(1)
    wait_for_app_idle(page)
    wait_for_cy_ready(component)
    assert component.locator("#cy").evaluate(
        "el => el._cyreg.cy.scratch('circle-command-instance') === true"
    )
    assert_circle_positions(component)
    expect(page.get_by_test_id("stException")).to_have_count(0)


def test_crud_data_loading_direct_route(page: Page, run_streamlit):
    page.goto(f"http://localhost:{run_streamlit}/crud_data_loading")
    page.wait_for_load_state("networkidle")

    expect(page).to_have_title("Interactive CRUD / Data Loading")
    expect(
        page.get_by_role("heading", name="Interactive CRUD / Data Loading")
    ).to_be_visible()
    expect(page.locator("#container").first).to_be_visible(timeout=10000)
    expect(page.get_by_text("Page not found")).to_have_count(0)


def test_crud_demo_opens_add_node_dialog(page: Page):
    click_nav(page, "Interactive CRUD / Data Loading")
    page.wait_for_load_state("networkidle")
    component = page.locator("#container").first
    expect(component).to_be_visible(timeout=10000)

    open_component_menu(component, "crudControls")
    component.locator("#crudCreateNode").click()

    add_node = page.locator("[role='dialog']").filter(has_text="Node ID").first
    expect(add_node).to_be_visible(timeout=10000)
    expect(add_node.get_by_label("Node ID")).to_be_visible()


def test_crud_demo_add_node_then_edge_keeps_canvas_graph(page: Page):
    click_nav(page, "Interactive CRUD / Data Loading")
    page.wait_for_load_state("networkidle")
    component = page.locator("#container").first
    expect(component).to_be_visible(timeout=10000)

    open_component_menu(component, "crudControls")
    component.locator("#crudCreateNode").click()
    add_node = page.locator("[role='dialog']").filter(has_text="Add node").first
    expect(add_node).to_be_visible(timeout=10000)
    add_node.get_by_label("Node ID").fill("Lead_Test")
    add_node.get_by_label("Name").fill("Lead Test")
    add_node.get_by_role("button", name="Create node").click()

    wait_for_cy_node_ids(component, ["Lead_Test", "case", "maya", "vehicle"])
    counts = get_cy_visible_counts(component)
    assert counts["nodes"] == 4
    assert counts["visible_nodes"] == 4
    assert counts["edges"] == 2

    select_node(component, "case")
    open_component_menu(component, "crudControls")
    add_edge_button = component.locator("#crudCreateEdge")
    expect(add_edge_button).to_be_enabled(timeout=10000)
    add_edge_button.click()
    add_edge = page.locator("[role='dialog']").filter(has_text="Add edge").first
    expect(add_edge).to_be_visible(timeout=10000)
    add_edge.get_by_role("button", name="Create edge").click()

    wait_for_cy_edge_count(component, 3)
    counts = get_cy_visible_counts(component)
    assert counts["nodes"] == 4
    assert counts["visible_nodes"] == 4
    assert counts["edges"] == 3
    assert counts["visible_edges"] == 3


def test_node_actions_demo_preserves_dragged_positions(page: Page):
    click_nav(page, "Node Actions")
    page.wait_for_load_state("networkidle")

    component = page.locator("#container").first
    expect(component).to_be_visible(timeout=10000)
    cy = component.locator("#cy")
    wait_for_cy_ready(component)

    cy.evaluate(
        """(element) => {
            const cy = element._cyreg.cy;
            const node = cy.getElementById("ABC123");
            node.position({ x: 520, y: 260 });
            node.emit("dragfree");
        }"""
    )
    expect(page.get_by_test_id("stJson").first).to_contain_text("520", timeout=10000)

    cy.evaluate(
        """(element) => {
            const cy = element._cyreg.cy;
            cy.elements(":selected").unselect();
            cy.getElementById("ABC123").select();
        }"""
    )
    expand = component.locator("#nodeActionsExpand")
    expect(expand).to_be_enabled(timeout=10000)
    expand.click()

    deadline = time.time() + 10
    while time.time() < deadline:
        node_exists = cy.evaluate(
            """(element) => {
            const cy = element._cyreg?.cy;
                return Boolean(cy?.getElementById("Person_MReed").length);
        }"""
        )
        if node_exists:
            break
        page.wait_for_timeout(100)
    else:
        assert node_exists

    wait_for_cy_ready(component)
    position = cy.evaluate(
        """(element) => {
            const cy = element._cyreg.cy;
            return cy.getElementById("ABC123").position();
        }"""
    )
    assert abs(position["x"] - 520) < 5
    assert abs(position["y"] - 260) < 5


def test_node_actions_demo_expansion_increases_nodes(page: Page):
    click_nav(page, "Node Actions")
    page.wait_for_load_state("networkidle")

    component = page.locator("#container").first
    expect(component).to_be_visible(timeout=10000)

    initial_ids = get_cy_node_ids(component)
    right_click_expand_cy_node(component, "ABC123")
    first_expansion_ids = wait_for_cy_node_ids(
        component,
        [
            "12VEC",
            "ABC123",
            "ALPHA",
            "BETA",
            "Person_MReed",
            "Phone_0412",
            "location_1",
            "location_2",
            "location_3",
        ],
    )

    assert len(first_expansion_ids) > len(initial_ids)
    assert "Person_MReed" in first_expansion_ids
    assert "Phone_0412" in first_expansion_ids


def test_showcase_terminal_expansion_children_do_not_show_badges(page: Page):
    click_nav(page, "Graph Workbench Showcase")
    page.wait_for_load_state("networkidle")

    component = page.locator("#container").first
    expect(component).to_be_visible(timeout=10000)

    wait_for_cy_node_ids(component, ["case", "maya", "vehicle"])
    expand_cy_node(component, "vehicle")
    wait_for_cy_node_ids(
        component, ["case", "checkpoint", "maya", "time_window", "vehicle"]
    )

    expect(component.locator(".expansion-badge[data-node-id='vehicle']")).to_have_text(
        "-2"
    )
    expect(
        component.locator(".expansion-badge[data-node-id='checkpoint']")
    ).to_have_count(0)
    expect(
        component.locator(".expansion-badge[data-node-id='time_window']")
    ).to_have_count(0)

    select_node(component, "checkpoint")
    expect(component.locator("#nodeActionsExpand")).to_be_disabled()
