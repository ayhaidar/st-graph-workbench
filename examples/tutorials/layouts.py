"""Compare layouts and viewport controls using fixed source records."""

from functools import partial
from typing import get_args
import streamlit as st
from demos.demo_helpers import demo_node_styles
from st_graph_workbench import ViewportAction, graph_workbench, records_to_dataframe
from st_graph_workbench.component.layouts import LAYOUTS
from tutorials.common import (
    show_example,
    begin_lesson,
    component_key,
    finish_lesson,
    receive_event,
    show_graph_data,
    show_result,
)

state = begin_lesson(4)
show_graph_data(
    state["elements"],
    "The same seven nodes and five edges are used for every layout. Each node already has coordinates for preset layout.",
)
st.header("Code and working graph")
name = st.selectbox(
    "Layout",
    sorted(LAYOUTS),
    index=sorted(LAYOUTS).index("preset"),
    key="tutorial_04_widget_layout",
)
toolbar_mode = st.segmented_control(
    "Toolbar presentation",
    ["adaptive", "expanded", "compact", "minimized"],
    default="adaptive",
    key="tutorial_04_widget_toolbar",
)
st.markdown(
    "Grid and circle emphasize arrangement; breadthfirst and dagre emphasize hierarchy; force layouts emphasize connections. Preset uses saved coordinates. Random is useful as a layout starting point."
)
st.subheader("How this example works")
st.markdown("""
A **layout** computes node positions; the **viewport** is the camera looking at
those positions. Panning or zooming moves the camera without changing node
coordinates. Dragging a node changes its coordinates without changing its edges.

- **preset** uses the supplied `position` values; **grid**, **circle**, and
  **concentric** create structured arrangements; **random** scatters the nodes.
- **breadthfirst** arranges levels and **dagre** emphasizes layered structure.
- **cose**, **fcose**, and **cola** use force-based approaches to arrange connected
  records. Their geometric distances are not measurements from the source data.

`fit=True` frames the result after a layout, and `padding` leaves space around it.
`min_zoom` and `max_zoom` constrain magnification; `wheel_sensitivity` adjusts
wheel response. The viewport controls can fit, center, save, or restore the view.
`return_positions=True` enables position payloads, which this lesson's callback
copies into the Python checkpoint. Returning to preset therefore uses the latest
positions captured by the callback, not necessarily the original arrangement.

The toolbar occupies a measured top region rather than covering the graph.
Adaptive mode uses labelled menus when space permits and compact icon menus at
narrower widths. Its arrow button minimizes or restores the controls without
changing graph state, positions, or the viewport.
""")
with show_example(__file__):
    # Fit reframes the camera after layout; padding leaves room around the nodes.
    layout = {"name": name, "fit": True, "padding": 60, "animate": False}
    result = graph_workbench(
        state["elements"],
        layout=layout,
        node_styles=demo_node_styles(text_size=18),
        viewport_actions=list(get_args(ViewportAction)),
        min_zoom=0.1,
        max_zoom=4,
        wheel_sensitivity=0.2,
        # The callback stores returned model coordinates for later preset renders.
        return_positions=True,
        toolbar={
            "mode": toolbar_mode,
            "position": "top",
            "collapsible": True,
            "sticky": True,
        },
        key=component_key(4),
        on_change=partial(receive_event, 4),
        height=600,
    )
st.subheader("Try it and check the result")
st.markdown("""
1. Compare grid, circle, and dagre. The source still contains 7 nodes and 5 edges
   even though the arrangement changes.
2. Pan and zoom, save the viewport, move the camera again, then restore it.
   Camera restoration does not undo a node drag.
3. Drag ABC123 and inspect a `positions` result. Its `x` and `y` are graph/model
   coordinates, not the node's current pixel position on your screen.
4. Compare expanded and compact toolbar modes, then use the arrow to minimize
   and restore the controls. The node coordinates and camera stay unchanged.

Choose a layout to support the question being explored. Use saved positions when
spatial continuity matters, and fit the view when readers need the whole network.
""")
st.subheader("Code in practice")
st.markdown(
    "Read the most recent positions event independently of viewport events. "
    "After dragging, compare its ID and x/y fields with the source table. "
    "The table stays empty until positions have been reported."
)
with show_example(__file__):
    # A pan/zoom event must not overwrite the last reported node coordinates.
    position_event = state.get("results", {}).get("positions", {})
    position_rows = position_event.get("data", {}).get("positions", [])
    st.dataframe(records_to_dataframe(position_rows), hide_index=True, height=180)
show_result(
    state["event"] or layout,
    "Before interaction this is the layout configuration. A `viewport` event describes the operation and resulting pan/zoom. A `positions` event contains `data.positions`, a list of `{id, position: {x, y}}` records in graph coordinates.",
    label="Latest component event" if state["event"] else "Layout configuration",
)
finish_lesson(
    4,
    __file__,
    mistakes="Preset requires usable coordinates. Do not change component keys to switch layouts. Save viewport stores camera pan/zoom, not graph records or node positions.",
    conclusion="Layouts and viewport controls change how relationships are viewed, not the relationships themselves.",
)
