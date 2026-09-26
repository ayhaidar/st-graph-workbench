from pathlib import Path
import time

from playwright.sync_api import Page, expect

from graph_test_helpers import (
    COMPONENT_LOCATOR,
    IFRAME_LOCATOR,
    get_badge,
    get_component,
    get_cy,
    get_node_ids,
    get_node_pos,
    open_toolbox_menu,
)

PAGE_NAME = "Components V2 Validation"
ROOT = Path(__file__).resolve().parents[1]


def test_frontend_html_templates_do_not_contain_invalid_attributes() -> None:
    frontend_src = ROOT / "st_graph_workbench" / "frontend" / "src"

    for template in (frontend_src / "component.html", frontend_src / "index.html"):
        html = template.read_text(encoding="utf-8")
        assert 'id="infopanel" ,' not in html


def test_validation_demo_uses_collision_prone_keys() -> None:
    demo = (ROOT / "examples" / "demos" / "component_v2_validation.py").read_text(
        encoding="utf-8"
    )

    assert 'key="V2_VALIDATION__GRAPH"' in demo
    assert 'key="V2_VALIDATION--GRAPH"' in demo
    assert "lossy key normalization bugs" in demo


def test_frontend_lifecycle_cleanup_cancels_pending_callbacks() -> None:
    frontend_src = ROOT / "st_graph_workbench" / "frontend" / "src"
    helpers = (frontend_src / "utils" / "helpers.js").read_text(encoding="utf-8")
    index = (frontend_src / "index.js").read_text(encoding="utf-8")
    graph = (frontend_src / "components" / "graph.js").read_text(encoding="utf-8")
    badges = (frontend_src / "components" / "expansionBadges.js").read_text(
        encoding="utf-8"
    )
    layouts = (frontend_src / "utils" / "layouts.js").read_text(encoding="utf-8")

    assert "cleanupCallbacks: new Set()" in helpers
    assert "context.debouncedSetValue?.cancel?.()" in helpers
    assert "if (context.isDestroyed)" in helpers
    assert "instance.context.cleanup?.()" in index
    assert "cancelAnimationFrame(instance.resizeFrameId)" in index
    assert "updateExpansionBadges.cancel = function ()" in badges
    assert "cancelAnimationFrame(animationFrameState.current)" in badges
    assert "context?.addCleanup?.(cleanupReadyWait)" in layouts
    assert "if (context?.isDestroyed)" in layouts
    assert "context.addCleanup?.(() => clearCustomEventListeners(context, cy))" in graph
    assert "cy.off(binding.event_type, binding.selector, binding.handler)" in graph


def get_node_background_image(component, node_id):
    return get_cy(component).evaluate(f"""(element) => {{
        const cy = element._cyreg.cy;
        return cy.getElementById("{node_id}").style("background-image");
    }}""")


def get_selection_runtime(component):
    return get_cy(component).evaluate("""(element) => {
        const cy = element._cyreg.cy;
        return {
            boxSelectionEnabled: cy.boxSelectionEnabled(),
            selectionType: cy.selectionType(),
        };
    }""")


def get_zoom_bounds(component):
    return get_cy(component).evaluate("""(element) => {
        const cy = element._cyreg.cy;
        return {
            minZoom: cy.minZoom(),
            maxZoom: cy.maxZoom(),
        };
    }""")


def wait_for_zoom_bounds(component, *, min_zoom, max_zoom):
    deadline = time.time() + 10
    while time.time() < deadline:
        bounds = get_zoom_bounds(component)
        if (
            abs(bounds["minZoom"] - min_zoom) < 0.001
            and abs(bounds["maxZoom"] - max_zoom) < 0.001
        ):
            return bounds
        time.sleep(0.1)
    bounds = get_zoom_bounds(component)
    assert abs(bounds["minZoom"] - min_zoom) < 0.001
    assert abs(bounds["maxZoom"] - max_zoom) < 0.001
    return bounds


def count_shadow_root_components(page: Page) -> int:
    return page.evaluate(
        """() => {
            let count = 0;
            const visit = (element) => {
                if (element.shadowRoot?.querySelector("#container")) {
                    count += 1;
                }
                element.shadowRoot
                    ?.querySelectorAll("*")
                    .forEach((child) => visit(child));
                element.querySelectorAll(":scope > *").forEach((child) => {
                    visit(child);
                });
            };
            visit(document.documentElement);
            return count;
        }"""
    )


def test_v2_validation_page_renders_two_independent_components(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")

    expect(page.locator(COMPONENT_LOCATOR)).to_have_count(2, timeout=10000)
    expect(page.locator(IFRAME_LOCATOR)).to_have_count(0)
    assert count_shadow_root_components(page) == 0

    left = get_component(page, 0)
    right = get_component(page, 1)

    assert get_node_ids(left) == ["left_root"]
    assert get_node_ids(right) == ["right_root"]
    expect(get_badge(left, "left_root")).to_have_text("+2/1.2k")
    expect(get_badge(right, "right_root")).to_have_text("+3")

    left_icon = get_node_background_image(left, "left_root")
    right_icon = get_node_background_image(right, "right_root")
    assert "_stcore/bidi-components" in left_icon
    assert "icons/directions_car.svg" in left_icon
    assert "_stcore/bidi-components" in right_icon
    assert "icons/person.svg" in right_icon


def test_v2_validation_instances_keep_badge_toggle_separate(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")

    left = get_component(page, 0)
    right = get_component(page, 1)
    left_toggle = left.locator("#expansionBadgeToggle")
    right_toggle = right.locator("#expansionBadgeToggle")

    expect(get_badge(left, "left_root")).to_be_visible()
    expect(get_badge(right, "right_root")).to_be_visible()

    left_toggle.click()
    expect(left_toggle).to_have_attribute("aria-pressed", "false")
    expect(right_toggle).to_have_attribute("aria-pressed", "true")
    expect(get_badge(left, "left_root")).to_be_hidden()
    expect(get_badge(right, "right_root")).to_be_visible()


def test_v2_validation_updates_selection_mode_without_remount(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")

    left = get_component(page, 0)
    assert get_node_ids(left) == ["left_root"]
    assert get_selection_runtime(left) == {
        "boxSelectionEnabled": False,
        "selectionType": "single",
    }
    expect(left.locator("#canvasModeControls")).to_be_hidden()

    page.get_by_role("switch", name="Use box selection on left graph").click(force=True)
    expect(left.locator("#selectionStatusMode")).to_have_text("Box", timeout=10000)
    expect(left.locator("#canvasModeControls")).to_be_visible()
    assert get_node_ids(left) == ["left_root"]
    assert get_selection_runtime(left) == {
        "boxSelectionEnabled": True,
        "selectionType": "additive",
    }

    page.get_by_role("switch", name="Use box selection on left graph").click(force=True)
    expect(left.locator("#selectionStatusMode")).to_have_text("Single", timeout=10000)
    expect(left.locator("#canvasModeControls")).to_be_hidden()
    assert get_selection_runtime(left) == {
        "boxSelectionEnabled": False,
        "selectionType": "single",
    }


def test_v2_validation_updates_and_resets_zoom_bounds_without_remount(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")

    left = get_component(page, 0)
    default_bounds = get_zoom_bounds(left)

    page.get_by_role("switch", name="Limit left graph zoom bounds").click(force=True)
    assert wait_for_zoom_bounds(left, min_zoom=0.5, max_zoom=2.0) == {
        "minZoom": 0.5,
        "maxZoom": 2.0,
    }
    assert get_node_ids(left) == ["left_root"]

    page.get_by_role("switch", name="Limit left graph zoom bounds").click(force=True)
    wait_for_zoom_bounds(
        left,
        min_zoom=default_bounds["minZoom"],
        max_zoom=default_bounds["maxZoom"],
    )


def test_v2_validation_resizes_cytoscape_when_container_size_changes(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")

    left = get_component(page, 0)
    get_cy(left).evaluate(
        """(element) => {
            const cy = element._cyreg.cy;
            const originalResize = cy.resize.bind(cy);
            cy.__resizeCalls = 0;
            cy.resize = (...args) => {
                cy.__resizeCalls += 1;
                return originalResize(...args);
            };
            element.closest("#container").style.height = "540px";
        }"""
    )

    deadline = time.time() + 10
    while time.time() < deadline:
        resize_calls = get_cy(left).evaluate(
            """(element) => element._cyreg.cy.__resizeCalls || 0"""
        )
        if resize_calls > 0:
            return
        time.sleep(0.1)
    assert (
        get_cy(left).evaluate("""(element) => element._cyreg.cy.__resizeCalls || 0""")
        > 0
    )


def test_v2_validation_hides_visibility_actions_when_not_enabled(page: Page):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")

    left = get_component(page, 0)
    open_toolbox_menu(left, "selectionControls")

    expect(left.locator("#selectionSelectAll")).to_be_visible()
    expect(left.locator("#selectionClear")).to_be_visible()
    expect(left.locator("#selectionFocus")).to_be_visible()
    expect(left.locator("#selectionHideUnselected")).to_be_hidden()
    expect(left.locator("#selectionRestore")).to_be_hidden()


def test_v2_validation_instances_emit_events_to_their_own_return_values(
    page: Page,
):
    page.get_by_role("link", name=PAGE_NAME).click()
    page.wait_for_load_state("networkidle")

    left = get_component(page, 0)
    right = get_component(page, 1)
    left_return = page.get_by_test_id("stJson").nth(0)
    right_return = page.get_by_test_id("stJson").nth(1)

    left_pos = get_node_pos("left_root", left)
    get_cy(left).click(position=left_pos)
    expect(left_return).to_contain_text("left_node_click", timeout=10000)
    expect(right_return).not_to_contain_text("left_node_click")

    right_pos = get_node_pos("right_root", right)
    get_cy(right).click(position=right_pos)
    expect(right_return).to_contain_text("right_node_click", timeout=10000)
