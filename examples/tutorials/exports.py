"""Download graph artifacts and restore saved model coordinates."""

from copy import deepcopy
from functools import partial
import json
import streamlit as st
from demos.demo_helpers import demo_node_styles
from st_graph_workbench import graph_workbench, set_elements_command, viewport_command
from tutorials.common import (
    show_example,
    begin_lesson,
    component_key,
    finish_lesson,
    receive_event,
    show_graph_data,
    show_result,
    show_function,
)
from tutorials.workflows import next_command_id, restore_positions

state = begin_lesson(13)
show_graph_data(state["elements"])
st.header("Code and working graph")
st.markdown(
    "The export menu provides full, visible, and selected graph JSON; PNG and JPG images; and positions JSON. These are browser downloads, not Python export events. Select an edge to compare a selected subgraph with the full dataset."
)
st.subheader("How this example works")
st.markdown("""
Choose an export according to what another person or application needs:

- **Full graph JSON** contains records held by the browser, including hidden
  ones. It is not an export of records an external source has never loaded.
- **Visible graph JSON** reflects the current visibility. **Selected graph
  JSON** describes the chosen subgraph and includes the endpoints needed by
  selected edges, so the exported relationships are not left dangling.
- **PNG/JPG** captures a visual result. An image cannot restore editable node
  properties or the underlying relationship data.
- **Positions JSON** records node IDs with model-coordinate `x`/`y` values.
  Positions are neither screen pixels nor geographic coordinates unless your
  application deliberately maps them that way.

`return_positions=True` enables the callback to copy dragged positions into the
Python graph. **Save positions** takes a separate copy of those values; it is not
merely a reference that changes on the next drag. **Restore positions** validates
the snapshot, matches records by ID, and applies preset coordinates without a
global rearrangement. The snapshot does not include camera pan/zoom or source
records, so keep graph data as well when a workspace must be recreated elsewhere.
""")
with show_example(__file__):
    with st.container(horizontal=True):
        if st.button("Save positions", icon=":material/save:"):
            # Copy coordinates so subsequent drags cannot mutate the saved snapshot.
            state["saved"] = {
                "positions": [
                    {"id": n["data"]["id"], "position": deepcopy(n["position"])}
                    for n in state["elements"]["nodes"]
                    if n.get("position")
                ]
            }
        if st.button(
            "Restore positions",
            icon=":material/restore:",
            disabled="saved" not in state,
        ):
            state["elements"] = restore_positions(state["elements"], state["saved"])
            # Preset applies those model coordinates; fit=False keeps the camera.
            state["commands"] = [
                set_elements_command(
                    next_command_id(state, "restore"), state["elements"]
                ),
                viewport_command(
                    next_command_id(state, "positions"),
                    "run_layout",
                    layout={"name": "preset", "fit": False, "animate": False},
                ),
            ]
            st.rerun()
with st.expander("Import positions JSON"):
    uploaded = st.file_uploader(
        "Position file", type=["json"], key="tutorial_13_widget_upload"
    )
    if uploaded and st.button("Use imported positions", icon=":material/upload:"):
        try:
            candidate = json.loads(uploaded.getvalue())
            restore_positions(state["elements"], candidate)
            state["saved"] = candidate
            st.success("Validated. Restore positions will apply this snapshot.")
        except (ValueError, KeyError, TypeError) as error:
            st.error(str(error))
with show_example(__file__):
    result = graph_workbench(
        state["elements"],
        layout={"name": "preset", "padding": 60},
        node_styles=demo_node_styles(text_size=18),
        return_positions=True,
        return_selection=True,
        selection_mode="multiple",
        node_actions=["hide_unselected", "restore_hidden"],
        graph_commands=state["commands"],
        key=component_key(13),
        on_change=partial(receive_event, 13),
        height=600,
    )
st.subheader("Try it and check the result")
st.markdown("""
1. Save positions, drag ABC123, then restore. ABC123 returns to its saved model
   coordinates; unrelated records and relationships remain present.
2. Select a node and hide unselected records. Download visible and full graph
   JSON and compare their record counts. Restore hidden records afterward.
3. Select an edge and export the selection. Its endpoint nodes are included even
   when you did not select both endpoints separately.
4. Download the saved positions, import that file, and apply Restore positions.
   The importer validates finite coordinates and ignores IDs outside this graph.

The graph's export controls download files directly in the browser. They do not
produce a Python export event; the dictionary below shows a saved position
snapshot when one exists, otherwise the latest component event.
""")
st.subheader("Code in practice")
show_function(
    restore_positions,
    "**Validate before restoring.** This executing helper rejects non-finite "
    "coordinates before copying any changes. It updates known node IDs only, "
    "leaving edges and unrelated properties intact. The saved dictionary below "
    "is the payload this helper receives.",
)
show_result(
    state.get("saved") or state["event"],
    "`positions` is a list of node IDs and model-coordinate `{x, y}` pairs. A saved position snapshot does not contain edges or camera pan/zoom. The callback stores drag positions in the Python graph; Save captures a copy and Restore applies it by ID.",
    label="Saved positions snapshot"
    if state.get("saved")
    else "Latest component event",
)
if state.get("saved"):
    st.download_button(
        "Download saved positions",
        json.dumps(state["saved"], indent=2),
        "positions.json",
        "application/json",
        icon=":material/download:",
    )
finish_lesson(
    13,
    __file__,
    mistakes="Positions alone cannot rebuild a graph without its node records. Selected exports include relationship endpoints to form a valid subgraph. Image exports are visual artifacts, not editable graph data.",
    conclusion="Persist graph data and positions separately when users need to resume their workspace or share a visual result.",
)
