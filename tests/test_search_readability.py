"""Search typography stays readable instead of scaling down with the viewport."""

from io import BytesIO

import pytest
from PIL import Image, ImageStat
from playwright.sync_api import expect

from graph_test_helpers import get_component, get_cy, select_nodes, wait_for_app_idle


@pytest.mark.parametrize("route", ["learn_search", "learn_expansion"])
@pytest.mark.parametrize("width", [1440, 768, 390])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_search_controls_are_readable_and_fit(
    page, run_streamlit, tmp_path, route, width, theme
):
    page.set_viewport_size({"width": width, "height": 1000})
    page.goto(f"http://localhost:{run_streamlit}/{route}")
    graph = get_component(page)
    wait_for_app_idle(page)
    # Exercise the component's own theme tokens without depending on OS settings.
    graph.evaluate("(el, theme) => el.dataset.theme = theme", theme)
    search = graph.locator("#searchPanel")
    if not search.is_visible():
        graph.get_by_role("button", name="Open search controls").click()
    expect(search).to_be_visible()
    if route == "learn_expansion":
        graph.locator("#graphSearchScope").select_option("loaded")
    graph.locator("#graphSearchInput").fill("ABC123")
    graph.locator("#graphSearchInput").press("Enter")
    expect(graph.locator("#graphSearchStatus")).to_contain_text("match")
    if route == "learn_expansion":
        expect(graph.locator("#graphSearchResults")).to_be_visible()
    for control in search.locator("input:visible, select:visible").all():
        assert control.evaluate("el => getComputedStyle(el).fontSize") == "16px"
        assert control.bounding_box()["height"] >= 40
    for button in search.locator("button:visible").all():
        assert button.bounding_box()["height"] >= 40
    status = graph.locator("#graphSearchStatus")
    assert status.evaluate("el => getComputedStyle(el).fontSize") == "14px"
    graph.screenshot(path=tmp_path / f"search-normal-{route}-{width}-{theme}.png")
    status.evaluate(
        "el => el.textContent = 'Search feedback: ' + 'many matching records '.repeat(12)"
    )
    page.wait_for_function(
        "el => el.closest('#container').style.getPropertyValue('--infopanel-top') !== ''",
        arg=search.element_handle(),
    )
    assert search.evaluate("""el => {
        const bounds = el.getBoundingClientRect();
        const graph = el.closest('#container').getBoundingClientRect();
        const controls = [...el.children].filter(e => e.getClientRects().length);
        const rects = controls.map(e => e.getBoundingClientRect());
        return bounds.left >= graph.left && bounds.right <= graph.right
            && el.scrollWidth <= el.clientWidth + 1
            && controls.every(e => e.scrollWidth <= e.clientWidth + 1)
            && rects.every(r => r.left >= bounds.left && r.right <= bounds.right)
            && rects.every((a, i) => rects.slice(i + 1).every(b =>
                a.right <= b.left || a.left >= b.right || a.bottom <= b.top || a.top >= b.bottom));
    }""")
    graph.screenshot(path=tmp_path / f"search-{route}-{width}-{theme}.png")
    # Restore ordinary feedback before checking the selection panel's available space.
    graph.locator("#graphSearchClear").click()
    select_nodes(graph, ["ABC123"])
    expect(graph.locator("#infopanel")).to_be_visible()
    page.wait_for_function(
        """el => {
        const panel = el.querySelector('#infopanel').getBoundingClientRect();
        const bar = el.querySelector('.graph-topbar').getBoundingClientRect();
        return panel.top >= bar.bottom;
    }""",
        arg=graph.element_handle(),
    )
    pixels = Image.open(BytesIO(get_cy(graph).screenshot())).convert("RGB")
    assert max(ImageStat.Stat(pixels).stddev) > 5
    expect(page.get_by_test_id("stException")).to_have_count(0)
