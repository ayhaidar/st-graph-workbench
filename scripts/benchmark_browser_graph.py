"""Measure graph readiness and basic browser capacity for the scale activity."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass

from playwright.sync_api import Error as PlaywrightError, sync_playwright


@dataclass
class Measurement:
    requested_records: int
    nodes: int | None = None
    edges: int | None = None
    render_ms: float | None = None
    heap_mb: float | None = None
    status: str = "ok"
    error: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure the Progressive Loading Scale Test in Chromium."
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8502",
        help="Running examples app URL.",
    )
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=[100, 600, 1_000, 5_000, 10_000],
        help="Vehicle-record checkpoints to render.",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=120_000,
        help="Maximum wait for each graph checkpoint.",
    )
    return parser.parse_args()


def measure(page, size: int, timeout_ms: int) -> Measurement:
    result = Measurement(requested_records=size)
    try:
        control = page.get_by_role("combobox", name="Graph size", exact=True)
        control.scroll_into_view_if_needed()
        control.click()
        page.wait_for_timeout(500)
        option = page.get_by_role(
            "option", name=f"{size:,} vehicle records", exact=True
        )
        option.click(force=True)
        page.wait_for_function(
            """() => document.querySelector('[data-testid="stApp"]')
            ?.getAttribute('data-test-script-state') === 'notRunning'""",
            timeout=timeout_ms,
        )
        started = time.perf_counter()
        page.get_by_role("button", name="Render selected graph").click()
        page.wait_for_function(
            """expected => {
                const element = document.querySelector('#cy');
                const cy = element?._cyreg?.cy;
                return cy?.nodes().length === expected + 3 &&
                    cy?.edges().length === expected;
            }""",
            arg=size,
            timeout=timeout_ms,
        )
        result.render_ms = round((time.perf_counter() - started) * 1000, 1)
        result.nodes, result.edges, result.heap_mb = page.locator("#cy").evaluate(
            """element => {
                const cy = element._cyreg.cy;
                const memory = performance.memory;
                return [
                    cy.nodes().length,
                    cy.edges().length,
                    memory ? memory.usedJSHeapSize / 1024 / 1024 : null,
                ];
            }"""
        )
    except PlaywrightError as error:
        result.status = "failed"
        result.error = str(error).splitlines()[0]
    return result


def main() -> None:
    args = parse_args()
    results: list[Measurement] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(f"{args.base_url.rstrip('/')}/progressive_loading_scale")
            page.locator("#cy").wait_for(state="visible", timeout=args.timeout_ms)
            for size in args.sizes:
                results.append(measure(page, size, args.timeout_ms))
        finally:
            browser.close()

    print("requested_records | nodes | edges | render_ms | heap_mb | status")
    print("--- | --- | --- | --- | --- | ---")
    for result in results:
        print(
            f"{result.requested_records:,} | "
            f"{result.nodes or '-'} | {result.edges or '-'} | "
            f"{result.render_ms or '-'} | "
            f"{result.heap_mb and round(result.heap_mb, 1) or '-'} | "
            f"{result.status}"
        )
    print(json.dumps([asdict(result) for result in results], indent=2))


if __name__ == "__main__":
    main()
