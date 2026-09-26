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
from st_graph_workbench import NodeStyle, StyleRule, graph_workbench
from st_graph_workbench.component.icons import SUPPORTED_ICONS


elements = demo_graph()
node_labels = sorted(
    {str(node["data"].get("label", "NODE")) for node in elements["nodes"]}
)
node_attributes = sorted(
    {str(key) for node in elements["nodes"] for key in node.get("data", {})}
)

render_demo_intro(
    "Node styles",
    """
    This demo focuses on `NodeStyle(...)`, the high-level Python wrapper for
    Cytoscape node styling. Pick a node label, change the style controls, and
    inspect the generated Cytoscape selector rule.
    """,
    [
        ("Node label selector", "`NodeStyle(label=...)` maps to `node[label='...']`."),
        (
            "Captions and icons",
            "Caption fields and Material Symbols icons come from node data.",
        ),
        (
            "Visual encoding",
            "Size, shape, border, opacity, text size, and label position.",
        ),
        (
            "Advanced rule",
            "`StyleRule(...)` adds raw Cytoscape style for selected nodes.",
        ),
    ],
    sections=[
        (
            "Capability coverage",
            "How `NodeStyle` and `StyleRule` map Python choices to Cytoscape node selectors.",
        ),
        (
            "Style controls",
            "Interactive controls for label, caption, icon, shape, color, size, border, and opacity.",
        ),
        (
            "Data before rendering",
            "The node and edge records used to populate the styled graph.",
        ),
        (
            "Executed output",
            "The live graph, generated style dictionary, returned component value, and source code.",
        ),
    ],
)

st.markdown("## Data before rendering")
st.markdown(
    """
    The style controls below operate on this graph dictionary. The `label`
    fields are the selectors used by `NodeStyle(...)`, while fields such as
    `name`, `type`, and `confidence` can be used as captions.
    """
)
render_elements_dataframe(elements, "Input graph records")

st.markdown("## Style controls")
first, second, third = st.columns(3)
with first:
    label = st.selectbox("Node label", node_labels, index=node_labels.index("VEHICLE"))
    icon = st.selectbox(
        "Icon", SUPPORTED_ICONS, index=SUPPORTED_ICONS.index("directions_car")
    )
    caption = st.selectbox("Caption field", [None, *node_attributes], index=1)
with second:
    color = st.color_picker("Fill color", value="#FF7F3E")
    shape = st.selectbox(
        "Shape",
        ["ellipse", "diamond", "round-rectangle", "hexagon", "vee", "tag"],
    )
    label_position = st.segmented_control(
        "Label position",
        ["top", "center", "bottom"],
        default="bottom",
    )
with third:
    size = st.slider("Size", min_value=20, max_value=70, value=38)
    text_size = st.slider("Text size", min_value=6, max_value=18, value=9)
    opacity = st.slider("Opacity", min_value=0.2, max_value=1.0, value=1.0)

border_row = st.container(horizontal=True)
border_color = border_row.color_picker("Border color", value="#D72638")
border_width = border_row.slider("Border width", min_value=0, max_value=8, value=3)
highlight_selected = st.checkbox(
    "Apply an extra `StyleRule(...)` to the chosen label",
    value=True,
)

default_styles = [
    style
    for style in demo_node_styles()
    if not isinstance(style, NodeStyle) or style.label != label
]
custom_style = NodeStyle(
    label,
    color=color,
    caption=caption,
    icon=icon,
    size=size,
    shape=shape,
    border_color=border_color,
    border_width=border_width,
    opacity=opacity,
    label_position=label_position,
    text_size=text_size,
)
node_styles = [*default_styles, custom_style]
if highlight_selected:
    node_styles.append(
        StyleRule(
            f"node[label = '{label}']",
            {
                "text-background-color": "#FFFFFF",
                "text-background-opacity": 0.92,
                "text-background-padding": "2px",
            },
        )
    )

value = graph_workbench(
    elements,
    node_styles=node_styles,
    edge_styles=demo_edge_styles(),
    layout={"name": "preset", "fit": True, "padding": 60},
    selection_mode="multiple",
    return_selection=True,
    search=True,
    key="node_style_demo",
    height=560,
)

st.markdown("## Executed output")
render_dictionary_preview(
    "Returned component value",
    value or {},
    """
    This dictionary is returned after graph interaction. For this style demo,
    it is most useful after selecting a node because it shows the selected
    element IDs and connected context.
    """,
    height=260,
    expanded=False,
)
render_dictionary_preview(
    "Generated node style rule dictionaries",
    [style.dump() for style in node_styles],
    """
    These dictionaries are generated from `NodeStyle` and `StyleRule` objects.
    They show the selector, visual properties, icon settings, and caption fields
    that the component sends to Cytoscape.
    """,
    height=340,
    expanded=True,
)

render_source_expander(__file__)
