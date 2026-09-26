"""Immediate editing and its explicitly browser-local lifecycle."""

from functools import partial
from typing import get_args
import streamlit as st
from demos.demo_helpers import demo_edge_styles, demo_node_styles
from st_graph_workbench import (
    EditAction,
    EdgeStyle,
    NodeStyle,
    graph_workbench,
    records_to_dataframe,
)
from tutorials.common import (
    show_example,
    begin_lesson,
    component_key,
    finish_lesson,
    receive_event,
    show_graph_data,
    show_result,
    show_workflow_comparison,
    show_function,
)
from tutorials.workflows import edit_report_frame

state = begin_lesson(
    11,
    contents=(
        "Source data",
        "CRUD or browser editing?",
        "Code and working graph",
        "Draft records",
        "How this example works",
        "Try it and check the result",
        "Code in practice",
        "Python records and browser edit report",
        "Data and practical result",
        "Common mistakes and next step",
    ),
)
show_graph_data(
    state["elements"],
    "This Python checkpoint is intentionally not changed by browser-local editing. Compare its counts with the graph's edit results.",
)
show_workflow_comparison(11)
st.header("Code and working graph")
st.markdown(
    "Editing scenarios: add a node; select two nodes and connect; delete selected records; lock/unlock or disable/enable dragging; snap to grid; then undo and redo. These operations take effect immediately, without a Python dialog."
)
st.subheader("Draft records")
st.markdown("""
**Gold document nodes are generic drafts**, not confirmed locations or vehicles.
Add Browser Node creates a record with `label="NODE"` and a generated ID such as
`node-1`. This lesson gives that category a document icon, dashed border, and
"Draft node" caption. The selection details and returned records retain the
unique ID and original `name`. A gold dashed **RELATED** edge is a draft link.

The browser tool does not offer a domain-type dialog. In the CRUD lesson you
choose the type before confirming; here you create an unclassified record first
to explore an idea. The draft appearance comes from the executing Python styles
below, not a required library color or an automatic approval status.
""")
st.subheader("How this example works")
st.markdown("""
Browser editing is deliberately different from the previous lesson's CRUD
requests. `edit_actions` enables changes that take effect immediately in the
mounted graph. Python receives an `edit` event afterward; no approval dialog runs
before the change in this example.

`elements_sync="initial"` sends the checkpoint when the graph mounts and allows
local edits to survive subsequent reruns. The callback retains events for
inspection but does **not** apply their changed records to `state["elements"]`.
That is why the source table can stay at 7 nodes / 5 edges while the browser's
`graph_counts` changes. This difference is intentional, not missing data.

The comparison below uses the latest **edit** report, so a later selection event
does not replace it. Added or updated elements are partial change records, not
the whole graph. Delete returns IDs; undo/redo returns a graph snapshot. This is
inspection of a browser report, not a second authoritative dataset or a live
readback. Its counts describe the moment that edit occurred.

Adding, connecting, and deleting change the local graph records. Locking prevents
position changes, while disabling dragging prevents the user's drag gesture;
neither is a record-level permission system. Grid snapping aligns positions.
Undo and redo operate on this browser instance's edit history. They do not roll
back a database transaction and do not survive unmounting the component.

To make edits durable, process the returned changes in an application handler
or export the graph. Validate those records before storing them, and use the
Python-owned CRUD workflow when a change must be approved before it is visible.
""")
with show_example(__file__):
    result = graph_workbench(
        state["elements"],
        layout={"name": "preset", "padding": 60},
        node_styles=[
            *demo_node_styles(text_size=18),
            # Classify browser-created NODE records visually, without changing their data.
            NodeStyle(
                "NODE",
                "#DCA72C",
                "name",
                "description",
                size=36,
                shape="round-rectangle",
                border_color="#805C12",
                border_width=2,
                raw_style={"border-style": "dashed", "label": "Draft node"},
            ),
        ],
        edge_styles=[
            *demo_edge_styles(),
            EdgeStyle(
                "RELATED", "#B78922", "label", directed=True, line_style="dashed"
            ),
        ],
        edit_actions=list(get_args(EditAction)),
        selection_mode="multiple",
        return_selection=True,
        # This lesson inspects edit events but does not mirror them into Python data.
        elements_sync="initial",
        key=component_key(11),
        on_change=partial(receive_event, 11),
        height=600,
    )
st.subheader("Try it and check the result")
st.markdown("""
1. Add a node and compare the browser counts with the unchanged Python table.
   Expect **8 browser nodes versus 7 Python nodes**, with a gold Draft node on the
   canvas. New drafts appear near the view center; drag one into open space if
   that area is occupied. Select it and ABC123, connect them, and inspect `added_elements`.
2. Undo the connection, then redo it. Compare each event's operation and snapshot
   with the visible result; selection events may appear between edit events.
3. Select a node and test lock/unlock, dragging controls, and grid snapping.
   The graph's identity and relationships do not change when its position changes.
4. Export any work you need, then leave and reopen this lesson. The graph starts
   again from its Python checkpoint, demonstrating the boundary of local history.
5. Compare with CRUD: adding Camera 8 there requires a type and confirmation and
   updates the Python records. A browser draft here is not that accepted camera
   record, even if you later give it a similar visual style.
""")
st.subheader("Code in practice")
st.markdown(
    "Keep the latest edit separate from selection events, then convert only its "
    "returned records for inspection. The helper's branches are shown below the tables."
)
st.subheader("Python records and browser edit report")
st.markdown(
    "The Python checkpoint table contains the input supplied to graph_workbench. "
    "The browser edit table contains only records or IDs returned by the latest edit, not "
    "an inferred full graph. Both are scrollable; the graph itself remains the "
    "current browser view. Reporting an edit is not approving or saving it."
)
with show_example(__file__):
    # Keep the edit report available even after a node-selection event arrives.
    report = state.get("results", {}).get("edit", {}).get("data", {})
    python_records = records_to_dataframe(state["elements"])
    browser_records = edit_report_frame(report)
python_column, browser_column = st.columns(2)
with python_column:
    st.markdown("**Python checkpoint**")
    st.caption(
        f"Python records: {len(state['elements']['nodes'])} nodes / {len(state['elements']['edges'])} edges"
    )
    st.dataframe(python_records, hide_index=True, height=240)
with browser_column:
    st.markdown("**Latest browser edit**")
    counts = report.get("graph_counts", {})
    st.caption(
        f"Browser report: {counts['total_nodes']} nodes / {counts['total_edges']} edges"
        if counts
        else "No browser edit reported yet."
    )
    st.dataframe(browser_records, hide_index=True, height=240)
st.caption(
    "Partial records are normal: add/connect returns added elements, lock/drag "
    "controls return updated elements, delete returns removed IDs, and snap "
    "returns positions. Only undo/redo reports include a full graph snapshot. "
    "Equal node counts do not imply equal relationships or properties."
)
with st.expander("Code for partial records, deleted IDs, and snapshots"):
    show_function(
        edit_report_frame,
        "The same helper builds the browser table above. A full snapshot takes "
        "precedence; added/updated elements stay partial; delete creates rows from "
        "the returned IDs only. No branch silently modifies the Python checkpoint.",
    )
show_result(
    state.get("results", {}).get("edit"),
    "`data.operation` names the edit and `graph_counts` describes the browser graph. `added_elements`/`updated_elements` carry changed records; delete returns deleted IDs. Undo/redo returns an `elements` snapshot. These are suitable inputs to an application persistence handler.",
    label="Latest browser edit event",
)
st.caption(
    f"Python checkpoint: {len(state['elements']['nodes'])} nodes, {len(state['elements']['edges'])} edges. Browser-only edits and undo history end when the page's component is unmounted."
)
finish_lesson(
    11,
    __file__,
    mistakes="With `elements_sync='initial'`, the initial checkpoint is not resent on each interaction. Returning to this page recreates that checkpoint, not unpersisted browser edits. Mirror edit events or export the full graph before leaving if changes must survive.",
    conclusion="Use immediate editing for a local workspace, and the previous lesson's Python-owned approach when your application must approve every change.",
)
