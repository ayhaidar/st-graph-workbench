from pathlib import Path
import re
import runpy

import streamlit as st

from page_overview import render_library_badges
from st_graph_workbench import records_to_dataframe
from demos.demo_helpers import render_dictionary_preview

ROOT_DIR = Path(__file__).resolve().parents[2]
LOGO_PATH = ROOT_DIR / "images" / "logo.png"
README_PATH = ROOT_DIR / "README.md"
SNIPPET_DIR = ROOT_DIR / "docs" / "snippets"
LIVE_OUTPUT_MARKER = re.compile(r"<!-- live-output: ([a-z_]+\.py) -->")
EXAMPLE_MARKER = re.compile(r"<!-- example: [a-z_]+\.py -->\n?")
SCREENSHOT_MARKER = re.compile(
    r"!\[([^\]]+)\]\(docs/assets/screenshots/([a-z0-9-]+\.png)\)"
)
EXAMPLE_TITLES = {
    "readme_graph.py": "Quick start code output",
    "readme_style.py": "Styled graph output",
    "readme_records.py": "Record helper code output",
    "readme_selection.py": "Selection as evidence output",
}

BANNER = """<p align="center">
  <img src="images/logo.png" alt="st-graph-workbench logo" width="400">
</p>"""


def render_live_example(filename: str, scope: dict) -> None:
    st.markdown(f"### {EXAMPLE_TITLES[filename]}")
    if filename == "readme_style.py":
        st.markdown("The same source records, now with type-specific styling.")
        st.dataframe(records_to_dataframe(scope["elements"]), hide_index=True)

    # Only execute the four local, maintained snippets, never code from Markdown.
    scope.update(runpy.run_path(str(SNIPPET_DIR / filename), init_globals=scope))

    if filename in {"readme_graph.py", "readme_style.py"}:
        render_dictionary_preview(
            "Returned graph event",
            scope["event"],
            (
                "`action` distinguishes selection from search. "
                "`data.selected_node_ids` supplies IDs for evidence filtering; "
                "`data.selected_elements` contains the complete selected records. "
                "Search instead returns `matched_elements` and matching IDs. "
                "`timestamp` marks the interaction. Before an interaction, the "
                "component returns `None`; the waiting message is a display placeholder."
            ),
            height=240,
        )
    elif filename == "readme_records.py":
        st.markdown("#### `records_to_dataframe(...)` output")
        st.markdown(
            "Three source sightings; `record_group` retains the dictionary group."
        )
        st.dataframe(scope["sightings_df"], hide_index=True)
        render_dictionary_preview(
            "`dataframe_to_records(...)` output",
            scope["records"],
            "Each dictionary retains vehicle_id, location, and time from a source row.",
            height=220,
        )
        render_dictionary_preview(
            "Vehicle nodes prepared from the dataframe",
            scope["vehicle_nodes"],
            (
                "Duplicate vehicle IDs are removed before wrapping rows in `data`. "
                "`id` is the graph identity; `label` matches the vehicle style; "
                "`name` is the display text. Relationships are defined separately."
            ),
            height=220,
        )
    elif filename == "readme_selection.py":
        st.markdown("#### Selected element records")
        st.markdown(
            "These are the styled graph's selected records, flattened for a detail "
            "view. The matching sightings above are filtered from the source table."
        )
        if scope["selected_rows"].empty:
            st.info("No element records selected.")
        else:
            st.dataframe(scope["selected_rows"], hide_index=True)


def render_readme_markdown(markdown_text: str) -> None:
    # Use local reviewed assets before publication, and without a GitHub connection.
    parts = SCREENSHOT_MARKER.split(markdown_text)
    st.markdown(parts[0])
    for caption, filename, following in zip(parts[1::3], parts[2::3], parts[3::3]):
        st.image(str(ROOT_DIR / "docs/assets/screenshots" / filename), caption=caption)
        st.markdown(following)


def render_readme_with_code_outputs(markdown_text: str) -> None:
    parts = LIVE_OUTPUT_MARKER.split(EXAMPLE_MARKER.sub("", markdown_text))
    scope: dict = {}
    render_readme_markdown(parts[0])
    for filename, following in zip(parts[1::2], parts[2::2]):
        if filename not in EXAMPLE_TITLES:
            raise ValueError(f"Unknown README example: {filename}")
        render_live_example(filename, scope)
        render_readme_markdown(following)


if LOGO_PATH.exists():
    with st.container(horizontal_alignment="center"):
        st.image(str(LOGO_PATH), width=400)

st.markdown("# Streamlit Graph Workbench")
readme = README_PATH.read_text(encoding="utf-8")
readme = readme.removeprefix("# st-graph-workbench").replace(BANNER, "", 1)
render_readme_with_code_outputs(readme)

st.markdown("## Continue exploring")
st.page_link(
    "demos/graph_workbench_showcase.py",
    label="Graph workbench showcase",
    icon=":material/hub:",
)
st.page_link(
    "demos/data_helpers_commands.py",
    label="Data helpers and commands",
    icon=":material/table_chart:",
)
render_library_badges(description="The libraries behind the graph workbench.")
