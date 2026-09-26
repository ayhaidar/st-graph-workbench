"""Exercise every incremental command against the same authoritative graph."""

from functools import partial
from typing import get_args
import streamlit as st
from demos.demo_helpers import demo_node_styles
from st_graph_workbench import (
    GraphCommandValidationError,
    apply_graph_commands,
    graph_workbench,
    validate_graph_commands,
)
from st_graph_workbench.component.commands import GraphCommandOperation
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
from tutorials.workflows import (
    command_example,
    missing_elements_command,
    next_command_id,
)

state = begin_lesson(12)
show_graph_data(state["elements"])
st.header("Code and working graph")
operation = st.selectbox(
    "Command operation",
    list(get_args(GraphCommandOperation)),
    key="tutorial_12_widget_operation",
)
sync = st.segmented_control(
    "Element synchronization",
    ["initial", "always"],
    default="initial",
    required=True,
    key="tutorial_12_widget_sync",
)
st.markdown(
    "Add creates only missing records; upsert can change existing ones. Update renames ABC123, delete removes the checkpoint, clear empties the graph, and set restores the sample. Layout and viewport commands change the browser view without changing Python relationships."
)
st.subheader("How this example works")
st.markdown("""
A **browser command** is a Python dictionary describing an instruction for the
already-mounted graph. It is not JavaScript code that your application has to
execute itself. A command helper constructs the instruction; `graph_commands`
delivers it to the component.

The example first builds a command, validates it against the current records,
and applies data changes to the Python checkpoint with `apply_graph_commands`.
Only an accepted command is sent. The overlap helper removes known IDs from
add batches because the pure Python add applier is strict about duplicate IDs.
An upsert deliberately permits updating existing records.

Record commands add, upsert, update, delete, replace (`set_elements`), or clear
data. View commands fit, center, pan, zoom, set the camera, set zoom bounds, or
run a layout. Applying a view command in Python does not compute a browser layout
or change the source relationships.

With **initial** synchronization, Python supplies a full checkpoint at mount
and commands carry later changes. With **always**, full element data is also
synchronized on reruns. Neither mode turns a command ID into a delivery receipt.
Keep a complete Python checkpoint for a future remount and assign a new
`command_id` to each new instruction.
""")
with show_example(__file__):
    if st.button("Send command", icon=":material/send:"):
        # Every new instruction gets a new ID, even when its operation is repeated.
        command = command_example(operation, next_command_id(state, "command"))
        command = missing_elements_command(state["elements"], command)
        try:
            # Do not send a command the Python checkpoint cannot accept.
            validate_graph_commands([command], elements=state["elements"])
            state["elements"] = apply_graph_commands(state["elements"], [command])
        except (GraphCommandValidationError, KeyError) as error:
            st.error(str(error))
        else:
            state["commands"] = [command]
            st.rerun()
    result = graph_workbench(
        state["elements"],
        layout={"name": "preset", "padding": 60},
        node_styles=demo_node_styles(text_size=18),
        graph_commands=state["commands"],
        elements_sync=sync,
        key=component_key(12),
        on_change=partial(receive_event, 12),
        height=600,
    )
st.subheader("Try it and check the result")
st.markdown("""
1. Send `add_elements` twice. The checkpoint appears once; repeating the sample
   addition does not create a duplicate node. Send `upsert_elements` to change
   its name, then `delete_elements` to remove it.
2. Send `update_data` and find ABC123's new caption. Compare its unchanged ID
   with the changed name in the source table.
3. Try `run_layout`, `pan`, and `zoom`. Their visible effects do not add or remove
   records. The same distinction applies to the other viewport operations.
4. Send `clear` and expect an intentionally empty graph. Send `set_elements`
   to restore the sample before trying another operation that targets ABC123.

The dictionary below is the outgoing instruction. Compare its `operation` and
target fields with the canvas; it is not an event confirming delivery.
""")
st.subheader("Code in practice")
show_function(
    command_example,
    "**Choose an instruction, not a JavaScript program.** This executing builder "
    "maps the operation control to public command helpers. The first branches "
    "change records; the final parameter dictionary configures view-only commands. "
    "The outgoing dictionary below shows the chosen branch's actual result.",
)
show_result(
    state["commands"],
    "This is the command sent, not a returned acknowledgment. `command_id` deduplicates an instruction within a browser instance; `operation` selects its behavior. The remaining fields contain records, target IDs, layout options, or viewport coordinates. Compare the canvas with the Python source table to confirm the effect.",
    label="Outgoing graph commands",
)
st.markdown(
    "**Command acknowledgment.** The current API does not return a command-acknowledgment event. Command IDs prevent duplicate application in the mounted browser; they are not delivery receipts. Verify the visible result or export the graph. The request/acknowledgment handshake for progressive loading is a separate feature covered in lesson 15."
)
finish_lesson(
    12,
    __file__,
    mistakes="A new operation needs a new command ID. Apply data commands to Python too. After clear, use set_elements before updating ABC123. `initial` requires a stable key and a full checkpoint for a future remount.",
    conclusion="Commands are structured instructions sent to the browser, allowing small graph changes without repeatedly replacing the complete dataset.",
)
