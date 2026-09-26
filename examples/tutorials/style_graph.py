"""Style categories and individual records without changing their identity."""

import streamlit as st
from st_graph_workbench import EdgeStyle, NodeStyle, StyleRule, graph_workbench
from tutorials.common import (
    show_example,
    begin_lesson,
    component_key,
    finish_lesson,
    show_graph_data,
    show_result,
)

state = begin_lesson(3)
show_graph_data(state["elements"])
st.header("Code and working graph")
st.markdown(
    "A category style gives vehicles an icon; a selector rule highlights one record. The graph data stays the same when its appearance changes."
)
st.subheader("How this example works")
st.markdown("""
`NodeStyle` matches `data.label`, not the text shown under a node. In this
checkpoint ABC123 has the category `MAIN_VEHICLE`, so the color, size, and shape
controls below affect it. The other vehicles have their own category styles.
`caption="name"` reads a property from each matching record; `icon` names a
packaged symbol. Changing these options does not rename or replace any record.

`EdgeStyle("Seen At", ...)` styles the sighting relationships: width controls
the line, `line_style="dashed"` changes its pattern, and `directed=True` shows
an arrow toward the target. An arrow changes presentation; it does not turn the
analysis algorithms into directed algorithms.

`StyleRule` accepts a Cytoscape selector and a property dictionary. Here an ID
selector adds a red border to ABC123, while the general `node` rule sets readable
captions. Property selectors can similarly emphasize records that satisfy a
condition. When several rules set the same style property, later matching rules
can override earlier values, so keep broad defaults before targeted overrides.
""")
color = st.color_picker(
    "Vehicle color", state.get("color", "#287D8E"), key="tutorial_03_widget_color"
)
size = st.slider(
    "Node size", 20, 70, state.get("size", 38), key="tutorial_03_widget_size"
)
shape = st.selectbox(
    "Node shape",
    ["ellipse", "diamond", "rectangle"],
    index=["ellipse", "diamond", "rectangle"].index(state.get("shape", "ellipse")),
    key="tutorial_03_widget_shape",
)
state.update(color=color, size=size, shape=shape)
with show_example(__file__):
    # Category styles match data.label, not the unique record ID.
    node_styles = [
        NodeStyle(
            "MAIN_VEHICLE",
            color=color,
            caption="name",
            icon="directions_car",
            size=size,
            shape=shape,
        ),
        NodeStyle("VEHICLE", color="#2A629A", caption="name", icon="directions_car"),
        NodeStyle(
            "HIGH-INTEREST OVERLAP",
            color="#D72638",
            caption="name",
            icon="directions_car",
        ),
        NodeStyle("PLACE", color="#29946B", caption="name", icon="place"),
        StyleRule(
            "node[id = 'ABC123']", {"border-width": 4, "border-color": "#D72638"}
        ),
        # This broad rule sets captions; it does not replace the red border above.
        StyleRule(
            "node", {"font-size": 18, "min-zoomed-font-size": 0, "label": "data(name)"}
        ),
    ]
    edge_styles = [
        # Arrows communicate direction visually; analysis chooses its own scope/rules.
        EdgeStyle(
            "Seen At",
            color="#687B8C",
            caption="label",
            directed=True,
            width=2,
            line_style="dashed",
        )
    ]
    result = graph_workbench(
        state["elements"],
        layout={"name": "preset", "padding": 60},
        node_styles=node_styles,
        edge_styles=edge_styles,
        height=600,
        key=component_key(3),
    )
st.subheader("Try it and check the result")
st.markdown("""
1. Change the vehicle color and node size, then choose the diamond shape.
   ABC123 changes appearance but keeps its ID, location, and relationships.
2. Notice that its red border remains: the selector rule sets the border while
   the category style sets its fill, size, and shape.
3. Compare the dumped styles below with the source records above. A `selector`
   describes which records match; a `style` dictionary describes their appearance.

Use category styling for consistent visual vocabulary and targeted rules for
exceptions. A caption or shape should reinforce color so meaning does not depend
on color alone.
""")
st.subheader("Code in practice")
st.markdown(
    "Inspect the style helpers as selector/property dictionaries. These are "
    "rendering instructions, not modified node or edge records. Change a control "
    "above and compare the corresponding property below."
)
with show_example(__file__):
    # dump() exposes the Cytoscape selector and appearance properties.
    style_payloads = [style.dump() for style in [*node_styles, *edge_styles]]
show_result(
    style_payloads,
    "Each `selector` identifies matching elements. Its `style` dictionary contains Cytoscape appearance properties. `data(name)` reads the caption from the record; the vehicle icon is a packaged asset.",
    label="Style configuration",
)
finish_lesson(
    3,
    __file__,
    mistakes="A NodeStyle label must match `data.label`, not the node ID. Use a StyleRule for individual IDs or property conditions. The Feature Lab exposes all style fields and the icon catalog.",
    conclusion="Styles communicate categories and emphasis without changing your source records. Next, arrange the same graph with different layouts.",
)
