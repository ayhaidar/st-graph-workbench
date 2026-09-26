"""Use returned selections to filter original source records."""

from functools import partial
from typing import get_args
import streamlit as st
from demos.demo_helpers import SIGHTING_RECORDS, demo_node_styles
from st_graph_workbench import SelectionMode, graph_workbench, records_to_dataframe
from tutorials.common import (
    show_example,
    begin_lesson,
    component_key,
    finish_lesson,
    receive_event,
    show_graph_data,
    show_result,
)

state = begin_lesson(6)
show_graph_data(state["elements"])
st.header("Code and working graph")
mode = st.segmented_control(
    "Selection mode",
    list(get_args(SelectionMode)),
    default="multiple",
    selection_mode="single",
    required=True,
    key="tutorial_06_widget_mode",
)
st.markdown(
    "Select ABC123 to retrieve its two sightings. Box mode supports group selection; its Pan/Box control switches blank-canvas dragging. Clear selection returns the linked table to zero rows."
)
st.subheader("How this example works")
st.markdown("""
`selection_mode` determines how users build a selection. Single mode chooses one
record; multiple mode allows a group; box mode adds a rectangle gesture. The
Pan/Box control separates moving the camera from selecting a region, so a canvas
drag does not have to mean both operations at once.

`return_selection=True` sends the selected IDs and record context back to Python.
The `on_change` callback stores that payload in this lesson's session state.
On the rerun, `selected_ids` becomes a set and `matched` filters the original
sighting rows by their `Entity` value. This is an ID-based join between a visual
selection and a source table, not a reconstruction of data from node captions.

The first result table answers **which source sightings belong to the selected
vehicles?** The second answers **which graph records were selected?** They can
differ: selecting a location or edge produces selected graph records but no
vehicle rows in this particular `Entity` filter. Adapt the join to include
target IDs or edge IDs when that is the question your application needs to answer.

The graph's **Selection > Show selection details** checkbox controls only the
on-canvas panel without deselecting records. The tables below still respond to
selections when details are hidden. The panel's **X** and **Clear selection**
both empty the selection and its returned tables, leaving the checkbox unchanged.
When the checkbox is enabled, selecting another record shows its details again.

`show_selection_details` sets the application's starting preference. The browser
remembers a user's choice for this graph across ordinary reruns. Changing the
Python preference below overrides it; resetting the lesson starts a new graph key.

Dragging is separate from selection. A normal drag moves one node. Dragging a
selected node moves Cytoscape's selected group. **Move connected nodes** adds
unselected, visible neighbors as rigid followers without selecting them. Its hop
depth is measured through visible relationships and its configured limit refuses
an oversized neighborhood atomically instead of moving only part of it.
""")
with show_example(__file__):
    show_details = st.checkbox(
        "Application preference: show selection details",
        value=True,
        key="tutorial_06_widget_details",
    )
    result = graph_workbench(
        state["elements"],
        layout={"name": "preset", "padding": 60},
        node_styles=demo_node_styles(text_size=18),
        selection_mode=mode,
        # Return IDs to Python even when the on-canvas details panel is hidden.
        return_selection=True,
        # Return the final model coordinates and a movement explanation to Python.
        return_positions=True,
        show_selection_details=show_details,
        connected_drag={
            "enabled": False,
            "depth": 1,
            "max_depth": 3,
            "max_nodes": 25,
        },
        height=600,
        key=component_key(6),
        on_change=partial(receive_event, 6),
    )
st.subheader("Try it and check the result")
st.markdown("""
1. In multiple mode, select ABC123. **Matching source records** becomes 2.
   Add ALPHA to the selection and it becomes 3.
2. Clear the selection. The metric returns to 0 and an empty result is displayed;
   there is no requirement for the user to keep a record selected.
3. Switch to box mode and select a group. Then switch its gesture to Pan and
   move the view without adding another selection rectangle.
4. Select a location or an edge and compare the two result tables. This exposes
   the difference between the graph's selection and the application's join rule.
5. Uncheck **Show selection details** in the Selection menu, then select ABC123.
   Its two source sightings still
   appear below. Re-enable **Show selection details** in the Selection menu to
   inspect the current selection without selecting it again.
6. Click the panel's **X**. The returned selection clears and the metric becomes
   0, but the checkbox stays enabled. Select ABC123 again: its details reappear.
7. Compare movement: drag one unselected node; select two nodes and drag one of
   them; box-select a group and drag it; then enable **Move connected nodes** in
   Selection and try one-, two-, and three-hop movement. Connected followers do
   not become selected, and graph record properties do not change.
""")
st.subheader("Code in practice")
st.markdown(
    "Join the latest selection to the original table by ID. An empty selection "
    "naturally produces zero matching rows; no placeholder record is invented."
)
with show_example(__file__):
    # Entity is the vehicle ID in this sample; captions are not unique join keys.
    selected_ids = set(state["selection"].get("selected_node_ids", []))
    matched = [row for row in SIGHTING_RECORDS if row["Entity"] in selected_ids]
    selected_records = records_to_dataframe(
        state["selection"].get("selected_elements", [])
    )
show_result(
    state["selection"],
    "`selected_node_ids` and `selected_edge_ids` are stable identifiers. `selected_elements` contains records with `id`, `group`, and `data`; `connected_elements` describes their neighbors. Use the IDs to join against your original data rather than treating labels as unique keys.",
    label="Selection payload",
)
st.metric("Matching source records", len(matched))
st.dataframe(records_to_dataframe(matched), hide_index=True)
st.markdown(
    "**Selected graph records.** Nodes and edges retain their full data fields, ready for a detail view or downstream processing."
)
st.dataframe(
    selected_records,
    hide_index=True,
)

movement_event = state.get("results", {}).get("positions", {})
movement_data = movement_event.get("data", {})
movement = movement_data.get("movement", {})
show_result(
    movement,
    "`operation` distinguishes an ordinary/native group drag from connected "
    "dragging. `moved_node_ids` includes every moved node; `connected_node_ids` "
    "contains only automatic followers. The status explains applied, disabled, "
    "over-limit, and active-layout outcomes.",
    title="Latest movement result",
    label="Movement metadata",
)
moved_ids = set(movement.get("moved_node_ids", []))
position_rows = [
    {"id": row["id"], **row["position"]}
    for row in movement_data.get("positions", [])
    if row.get("id") in moved_ids
]
st.markdown(
    "**Moved-node positions.** This filtered table is ready to persist in a "
    "database or session checkpoint. Coordinates describe the browser layout; "
    "they are not fields added to the underlying domain records."
)
st.dataframe(position_rows, hide_index=True)
finish_lesson(
    6,
    __file__,
    mistakes="The panel's X clears selection; use the toolbar checkbox to hide details without clearing the results. Use Pan to navigate in box mode. Connected dragging follows visible graph relationships, not semantic ownership, and refuses a scope above max_nodes. A hidden panel is not an access-control boundary; selected records still return to Python.",
    conclusion="Selections can drive detail views, filters, reports, or application actions, while native and connected dragging provide distinct ways to rearrange the same records.",
)
