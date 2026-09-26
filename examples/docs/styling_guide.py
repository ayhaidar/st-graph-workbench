import streamlit as st

from page_overview import render_page_overview

st.markdown("# Styling Guide")
st.markdown(
    """
    The simplest styling path is to use `NodeStyle` and `EdgeStyle`. They build
    Cytoscape stylesheet rules for you. When you need something more advanced,
    use `StyleRule(selector, style)` and pass Cytoscape style properties directly.
    """
)

render_page_overview(
    [
        (
            "Simple Python styling",
            "`NodeStyle` and `EdgeStyle` examples for common visual encodings.",
        ),
        (
            "Advanced selector styling",
            "`StyleRule` examples for raw Cytoscape selectors and style properties.",
        ),
        (
            "Reading styles.py",
            "How Python style objects become selector dictionaries for the browser.",
        ),
    ],
    description="This overview gives the styling page structure before the code blocks.",
)

st.markdown("## Simple Python Styling")
st.code(
    """
from st_graph_workbench import NodeStyle, EdgeStyle

node_styles = [
    NodeStyle(
        "PERSON",
        color="#FF7F3E",
        caption="name",
        icon="person",
        size=34,
        shape="ellipse",
        border_color="#ffffff",
        border_width=2,
    )
]

edge_styles = [
    EdgeStyle(
        "SEEN_AT",
        color="#2A629A",
        caption="label",
        directed=True,
        width=3,
        line_style="dashed",
    )
]
""",
    language="python",
)

st.markdown("## Advanced Cytoscape Selector Styling")
st.code(
    """
from st_graph_workbench import StyleRule

style_rules = [
    StyleRule(
        "node[risk >= 7]",
        {
            "border-width": 4,
            "border-color": "#D72638",
            "shape": "diamond",
        },
    )
]
""",
    language="python",
)

st.markdown("## Reading `styles.py` If You Know Python")
st.markdown(
    """
    `styles.py` does not draw anything itself. Each style class has a `dump()`
    method that returns a dictionary shaped like this:
    """
)
st.code(
    """
{
    "selector": "node[label='PERSON']",
    "style": {
        "background-color": "#FF7F3E",
        "label": "data(name)",
    },
}
""",
    language="python",
)
st.markdown(
    """
    JavaScript receives that dictionary and gives it to Cytoscape. Cytoscape
    applies the rule to every element matching the selector.
    """
)
