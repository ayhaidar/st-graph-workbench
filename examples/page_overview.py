from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import streamlit as st


PageSection = str | tuple[str, str] | Mapping[str, Any]


LIBRARY_BADGES: tuple[tuple[str, str, str, str], ...] = (
    (
        ":material/account_tree:",
        "Cytoscape.js",
        "blue",
        "Browser graph rendering and interaction.",
    ),
    (
        ":material/web_asset:",
        "Streamlit",
        "red",
        "Python app shell, navigation, and reruns.",
    ),
    (
        ":material/code:",
        "Python",
        "green",
        "Typed validation, commands, and state ownership.",
    ),
    (
        ":material/table_chart:",
        "Pandas",
        "orange",
        "Dataframe and record conversions for evidence tables.",
    ),
    (
        ":material/developer_board:",
        "Components v2",
        "violet",
        "Bidirectional bridge without a legacy iframe.",
    ),
    (
        ":material/category:",
        "Material Symbols",
        "gray",
        "Consistent icons for controls and node styling.",
    ),
)


def _section_row(section: PageSection, position: int) -> dict[str, str]:
    if isinstance(section, str):
        return {
            "step": str(position),
            "section": section,
            "summary": "A focused section of this page.",
        }

    if isinstance(section, Mapping):
        section_name = (
            section.get("section")
            or section.get("title")
            or section.get("name")
            or f"Section {position}"
        )
        section_description = (
            section.get("description")
            or section.get("summary")
            or section.get("what")
            or section.get("details")
            or "A focused section of this page."
        )
        return {
            "step": str(position),
            "section": str(section_name),
            "summary": str(section_description),
        }

    return {
        "step": str(position),
        "section": str(section[0]) if section else f"Section {position}",
        "summary": (
            str(section[1]) if len(section) > 1 else "A focused section of this page."
        ),
    }


def _contents_markdown(rows: Sequence[dict[str, str]]) -> str:
    lines: list[str] = []
    for row in rows:
        lines.append(f"{row['step']}. **{row['section']}**  \n   {row['summary']}")
    return "\n".join(lines)


def render_page_overview(
    sections: Sequence[PageSection],
    *,
    title: str = "What is in this page",
    description: str = "A quick contents guide for the sections below.",
) -> None:
    rows = [_section_row(section, index) for index, section in enumerate(sections, 1)]
    if not rows:
        return

    with st.container(border=True):
        st.markdown(f"#### :material/list_alt: {title}")
        if description:
            st.caption(description)
        st.markdown(_contents_markdown(rows))


def render_library_badges(
    *,
    title: str = "Library stack",
    description: str = "Built from a small set of focused libraries and runtime APIs.",
    columns_per_row: int = 3,
) -> None:
    """Render a compact, screenshot-friendly technology strip."""
    st.markdown(f"#### :material/extension: {title}")
    if description:
        st.caption(description)

    row_size = max(1, columns_per_row)
    for start in range(0, len(LIBRARY_BADGES), row_size):
        row = LIBRARY_BADGES[start : start + row_size]
        columns = st.columns(len(row), gap="small")
        for column, (icon, label, color, summary) in zip(columns, row):
            with column.container(border=True, height=126):
                st.badge(label, icon=icon, color=color)
                st.caption(summary)


def render_page_directory(page_guides: Sequence[Any]) -> None:
    """Render the complete navigation catalog as a reader-facing guide."""
    grouped_guides: dict[str, list[Any]] = {}
    for guide in page_guides:
        grouped_guides.setdefault(str(guide.section), []).append(guide)

    for section, guides in grouped_guides.items():
        section_heading = "Demo pages" if section == "Demos" else f"{section} pages"
        st.markdown(f"### {section_heading}")
        for guide in guides:
            with st.container(border=True):
                st.markdown(f"#### {guide.icon} {guide.title}")
                st.markdown(guide.summary)
                st.markdown(f"**What appears on the page:** {guide.contents}")
                st.markdown(f"**What to try or inspect:** {guide.reader_action}")
                st.caption(f"Main API: {guide.api}")
                st.caption(f"Returned or visible output: {guide.output}")


def render_javascript_capability_map(
    rows: Sequence[Mapping[str, Any]],
    *,
    height: int = 520,
) -> None:
    """Render frontend-to-Python mappings as a readable scrollable guide."""
    with st.container(border=True, height=height):
        for row in rows:
            module = str(row.get("javascript module", "frontend module"))
            responsibility = str(row.get("browser responsibility", ""))
            streamlit_surface = str(row.get("Streamlit surface", ""))
            example = str(row.get("example", ""))

            st.markdown(f"**`{module}`**")
            if responsibility:
                st.markdown(responsibility)
            if streamlit_surface:
                st.caption(f"Streamlit surface: `{streamlit_surface}`")
            if example:
                st.caption(f"Best demo page: {example}")
