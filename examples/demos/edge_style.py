import streamlit as st

from demos.demo_helpers import (
    demo_edge_styles,
    demo_graph,
    demo_node_styles,
    render_demo_intro,
    render_dictionary_preview,
    render_elements_dataframe,
    render_source_expander,
)
from st_graph_workbench import EdgeStyle, graph_workbench


CURVE_STYLES = [
    "bezier",
    "haystack",
    "straight",
    "unbundled-bezier",
    "round-segments",
    "segments",
    "round-taxi",
    "taxi",
]
LINE_STYLES = ["solid", "dashed", "dotted"]
ARROW_SHAPES = [None, "triangle", "vee", "circle", "diamond", "tee"]


elements = demo_graph()
edge_labels = sorted(
    {str(edge["data"].get("label", "RELATED")) for edge in elements["edges"]}
)
edge_attributes = sorted(
    {str(key) for edge in elements["edges"] for key in edge.get("data", {})}
)

render_demo_intro(
    "Edge styles",
    """
    This demo focuses on `EdgeStyle(...)`, the Python wrapper for relationship
    styling. Use it to encode edge meaning with captions, arrows, width, curve
    style, opacity, and line patterns.
    """,
    [
        (
            "Relationship selector",
            "`EdgeStyle(label=...)` maps to `edge[label='...']`.",
        ),
        (
            "Direction",
            "`directed=True` adds a target arrow; arrow shapes can be overridden.",
        ),
        ("Density control", "Curve and line styles help multigraphs stay readable."),
        (
            "Raw Cytoscape style",
            "`raw_style` fills in properties not named by the wrapper.",
        ),
    ],
    sections=[
        (
            "Capability coverage",
            "How `EdgeStyle` turns relationship labels into Cytoscape edge rules.",
        ),
        (
            "Style controls",
            "Controls for captions, direction, arrows, curve style, line style, width, and opacity.",
        ),
        (
            "Data before rendering",
            "The node and edge records whose relationship labels drive the edge selectors.",
        ),
        (
            "Executed output",
            "The styled graph, edge-style dictionary, returned component value, and source code.",
        ),
    ],
)

st.markdown("## Data before rendering")
st.markdown(
    """
    Edge styles are matched against the `label` field on edge records. Showing
    the records first makes it clear which relationships will be affected by
    the style controls below.
    """
)
render_elements_dataframe(elements, "Input graph records")

st.markdown("## Style controls")
first, second, third, fourth = st.columns(4)
with first:
    label = st.selectbox("Edge label", edge_labels, index=edge_labels.index("Seen At"))
    caption = st.selectbox("Caption field", [None, *edge_attributes], index=4)
with second:
    color = st.color_picker("Line color", value="#2A629A")
    width = st.slider("Line width", min_value=1, max_value=8, value=3)
with third:
    curve_style = st.selectbox("Curve style", CURVE_STYLES)
    line_style = st.selectbox("Line style", LINE_STYLES)
with fourth:
    directed = st.checkbox("Directed", value=True)
    source_arrow = st.selectbox("Source arrow", ARROW_SHAPES)
    target_arrow = st.selectbox("Target arrow", ARROW_SHAPES, index=1)

opacity = st.slider("Edge opacity", min_value=0.2, max_value=1.0, value=0.92)
show_background = st.checkbox("Add label background with `raw_style`", value=True)

default_styles = [style for style in demo_edge_styles() if style.label != label]
raw_style = (
    {
        "text-background-color": "#FFFFFF",
        "text-background-opacity": 0.9,
        "text-background-padding": "2px",
        "font-size": 8,
    }
    if show_background
    else None
)
custom_style = EdgeStyle(
    label,
    color=color,
    caption=caption,
    directed=directed,
    curve_style=curve_style,
    width=width,
    line_style=line_style,
    opacity=opacity,
    source_arrow=source_arrow,
    target_arrow=target_arrow,
    raw_style=raw_style,
)
edge_styles = [*default_styles, custom_style]

value = graph_workbench(
    elements,
    node_styles=demo_node_styles(),
    edge_styles=edge_styles,
    layout={"name": "preset", "fit": True, "padding": 60},
    selection_mode="multiple",
    return_selection=True,
    search=True,
    key="edge_style_demo",
    height=560,
)

st.markdown("## Executed output")
render_dictionary_preview(
    "Returned component value",
    value or {},
    """
    This dictionary is returned after interaction with the styled graph. Select
    an edge to inspect the edge ID, label, source, target, and connected graph
    context.
    """,
    height=260,
    expanded=False,
)
render_dictionary_preview(
    "Generated edge style rule dictionaries",
    [style.dump() for style in edge_styles],
    """
    These dictionaries are generated from `EdgeStyle` objects. They show the
    Cytoscape selector, line color, arrows, curve style, width, opacity, and
    optional raw style values sent to the browser.
    """,
    height=340,
    expanded=True,
)

render_source_expander(__file__)
