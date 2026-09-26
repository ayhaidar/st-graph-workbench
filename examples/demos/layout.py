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
from st_graph_workbench import graph_workbench
from st_graph_workbench.component.layouts import LAYOUTS


LAYOUT_NAMES = list(LAYOUTS)


render_demo_intro(
    "Layout algorithms",
    """
    This demo shows the two accepted layout forms: pass a layout name such as
    `"fcose"`, or pass a Cytoscape layout dictionary with extra options. Use
    `preset` when your nodes already include saved positions.
    """,
    [
        ("Named layouts", "Any key in `st_graph_workbench.component.layouts.LAYOUTS`."),
        ("Layout dictionaries", 'Use `{"name": ..., "fit": True, ...}` for options.'),
        ("Preset positions", "Node dictionaries can include `position` values."),
        ("Viewport fit", "`fit` and `padding` control the initial framing."),
    ],
    sections=[
        (
            "Capability coverage",
            "The two layout inputs accepted by `graph_workbench`: names and dictionaries.",
        ),
        (
            "Layout controls",
            "Controls for algorithm choice, dictionary mode, fit, padding, animation, and label dimensions.",
        ),
        (
            "Data before rendering",
            "The graph records and preset positions that the layout algorithm receives.",
        ),
        (
            "Executed output",
            "The graph rendered with the selected layout and the returned dictionary preview.",
        ),
        (
            "Available layout examples",
            "A compact reference table for each supported layout option.",
        ),
    ],
)

elements = demo_graph()

st.markdown("## Data before rendering")
st.markdown(
    """
    Preset layouts use each node's `position` values directly. Other layout
    algorithms receive the same node and edge records, then compute new browser
    positions from the graph structure.
    """
)
render_elements_dataframe(elements, "Input graph records")

st.markdown("## Layout controls")
left, middle, right = st.columns(3)
with left:
    layout_name = st.selectbox("Layout name", LAYOUT_NAMES, index=0)
    as_dictionary = st.toggle(
        "Pass as layout dictionary",
        value=True,
        help="Both names and dictionaries work for every supported layout.",
    )
with middle:
    fit = st.toggle("Fit graph after layout", value=True)
    padding = st.slider("Padding", min_value=0, max_value=140, value=60, step=10)
with right:
    animate = st.segmented_control(
        "Animation",
        ["none", "during", "end"],
        default="none",
    )
    include_labels = st.toggle("Include labels in layout dimensions", value=True)

layout = (
    {
        "name": layout_name,
        "fit": fit,
        "padding": padding,
        "animate": False if animate == "none" else animate,
        "nodeDimensionsIncludeLabels": include_labels,
    }
    if as_dictionary
    else layout_name
)

value = graph_workbench(
    elements,
    layout=layout,
    node_styles=demo_node_styles(),
    edge_styles=demo_edge_styles(),
    selection_mode="multiple",
    return_selection=True,
    key="layout_algorithms_demo",
    height=560,
)

st.markdown("## Executed output")
render_dictionary_preview(
    "Returned component value",
    value or {},
    """
    This dictionary is returned by graph interaction. It can be used with
    layouts to confirm selected records or to capture returned position events
    when position reporting is enabled.
    """,
    height=260,
    expanded=False,
)
render_dictionary_preview(
    "Layout payload sent to `graph_workbench(...)`",
    layout,
    """
    This dictionary is the exact layout object passed to Cytoscape. The `name`
    chooses the algorithm, while options such as `fit`, `padding`, `animate`,
    and `nodeDimensionsIncludeLabels` control the initial viewport and spacing.
    """,
    height=280,
    expanded=True,
)

st.markdown("#### Available layout examples")
st.dataframe(
    [
        {
            "layout": name,
            "source": "st_graph_workbench.component.layouts.LAYOUTS",
            "default options": LAYOUTS[name],
        }
        for name in LAYOUTS
    ],
    hide_index=True,
)

render_source_expander(__file__)
