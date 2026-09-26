"""Build a valid two-node graph and inspect its Python data contract."""

import streamlit as st
from st_graph_workbench import EdgeStyle, NodeStyle, graph_workbench, validate_elements
from tutorials.common import (
    show_example,
    begin_lesson,
    component_key,
    finish_lesson,
    show_graph_data,
    show_result,
    show_function,
)
from tutorials.data import first_graph

state = begin_lesson(1, first_graph)
show_graph_data(
    state["elements"],
    "One vehicle and one location are joined by a timestamped sighting. These are sample records, not a restriction on what your graph can represent.",
)
st.header("Code and working graph")
st.markdown(
    "Each node has a unique `data.id`. The edge's `source` and `target` refer to those IDs. Validation succeeds before rendering two nodes and one edge."
)
st.subheader("How this example works")
st.markdown("""
1. **Describe the records.** `first_graph()` creates the two lists the component
   expects: `nodes` for entities and `edges` for their relationships. An edge is
   a record in its own right, so the sighting has its own ID and time property.
2. **Check the connections.** `validate_elements(elements)` checks the graph
   contract before the browser receives it. On success it returns normally;
   an invalid graph raises an error. It does not draw or repair the graph.
3. **Render the graph.** `graph_workbench()` sends the validated records and
   display options to the browser. Grid supplies the initial coordinates;
   `NodeStyle` supplies category colors, captions, and icons. The directed edge
   makes the recorded source-to-target relationship visible.
4. **Keep the instance identifiable.** `component_key(1)` is this app's helper
   for a stable Streamlit key. In your own page, a fixed string such as
   `key="my_graph"` serves the same purpose. Ordinary reruns should not invent
   a new key, which would create a new browser instance.

The vehicle and location are only sample entities. Exactly the same contract
can represent tasks and dependencies, documents and references, or devices and
connections. No particular database or application domain is required.
""")
show_function(
    first_graph,
    "**Construct the input.** This is the function used to initialize the source "
    "table. Follow the node IDs into the edge endpoints; the Time value is read "
    "from the shared sample records, not calculated by the component.",
)
with show_example(__file__):
    # Validate the Python input before mounting a browser graph.
    elements = state["elements"]
    validate_elements(elements)
    result = graph_workbench(
        elements,
        layout={"name": "grid", "padding": 60},
        node_styles=[
            NodeStyle("VEHICLE", "#287D8E", "name", "directions_car", text_size=12),
            NodeStyle("PLACE", "#29946B", "name", "place", text_size=12),
        ],
        edge_styles=[EdgeStyle("Seen At", directed=True)],
        height=600,
        # The same key identifies this graph on subsequent Streamlit reruns.
        key=component_key(1),
    )
st.subheader("Try it and check the result")
st.markdown("""
1. Find `ABC123`, `location_1`, and `sighting-1` in the source records, then match
   them to the two nodes and connecting edge below the code.
2. Drag a node and zoom the view. The relationship still connects the same IDs;
   moving an element is not changing what it represents.
3. Inspect the dictionary below. This is the **input graph**, not a selection
   event. Selection callbacks and saving dragged positions are added in later
   lessons; this minimal example does not persist those interactions to Python.
""")
st.subheader("Code in practice")
st.markdown(
    "Count the records supplied to the component. These counts describe the Python "
    "input, not a selection or a live readback of dragged node positions."
)
with show_example(__file__):
    # Nodes represent entities; edges are separate relationship records.
    node_count = len(elements["nodes"])
    edge_count = len(elements["edges"])
    st.caption(f"Input graph: {node_count} nodes / {edge_count} edges")
show_result(
    elements,
    "This is the input passed to `graph_workbench`, not its return value.\n\n"
    "- `nodes`: two entity records, each with its properties inside `data`.\n"
    "- `edges`: one sighting; `source` and `target` reference the two node IDs.\n"
    "- `Time`: an application-owned property, not a layout instruction.\n"
    "- `position`: optional here because grid supplies coordinates.\n\n"
    "`label` selects a styling category; `name` supplies the caption. Neither replaces the unique `id`.",
    label="Input graph dictionary",
)
finish_lesson(
    1,
    __file__,
    mistakes="Do not reuse IDs or reference a missing endpoint. Keep the component key stable across reruns. A graph does not need a database to render.",
    conclusion="You have a working graph built from ordinary Python dictionaries. Next, change those dictionaries with the element helpers.",
)
