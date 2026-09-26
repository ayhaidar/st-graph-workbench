import base64
from pathlib import Path

import streamlit as st

from page_overview import render_page_overview

ROOT_DIR = Path(__file__).resolve().parents[2]
ICONS_DIR = ROOT_DIR / "st_graph_workbench" / "frontend" / "src" / "assets" / "icons"


def prepare_icon(icon):
    icon = icon.read_text().replace("#f0f0f0", "grey").encode("utf-8")
    icon = base64.b64encode(icon).decode("utf-8")
    return f"data:image/svg+xml;base64,{icon}"


icons = ICONS_DIR.glob("*svg")
icons = sorted(list(icons), key=lambda x: x.stem)
icons = [{"name": icon.stem, "preview": prepare_icon(icon)} for icon in icons]
n_icons = len(icons)

st.markdown("## Supported Icons")
render_page_overview(
    [
        (
            "Icon source",
            "The SVG assets bundled with the component frontend.",
        ),
        (
            "Icon preview table",
            "A name and image preview for every supported node icon.",
        ),
        (
            "Styling use",
            "Icon names that can be passed into `NodeStyle(..., icon=...)`.",
        ),
    ],
    description="This overview explains what the icon reference table contains.",
)
st.markdown("#### Icon preview table")
st.markdown(
    """
    The table below lists every bundled SVG icon by the name accepted by
    `NodeStyle(..., icon=...)`. The preview column shows the exact asset that
    the browser component can load for styled nodes.
    """
)
st.dataframe(
    icons,
    width=300,
    height=(n_icons + 1) * 35 + 2,
    hide_index=True,
    column_config={
        "name": st.column_config.TextColumn("Icon name"),
        "preview": st.column_config.ImageColumn("Preview"),
    },
)
