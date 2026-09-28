"""CRUD requests become validated Python mutations through a dialog."""

from typing import get_args
import streamlit as st
from demos.demo_helpers import (
    demo_edge_styles,
    demo_node_styles,
    render_dictionary_preview,
)
from st_graph_workbench import (
    CrudAction,
    delete_elements_command,
    get_element,
    graph_workbench,
    records_to_dataframe,
    update_data_command,
    upsert_elements_command,
)
from tutorials.common import (
    show_example,
    begin_lesson,
    component_key,
    finish_lesson,
    lesson_state,
    receive_event,
    show_graph_data,
    show_result,
    show_workflow_comparison,
    show_function,
)
from tutorials.data import CRUD_NODE_TYPES, related_records
from tutorials.workflows import next_command_id, queue_command


def handle_crud():
    # Store the intent first; no graph records change until the dialog confirms.
    event = receive_event(10)
    if event and event["action"] == "crud":
        lesson_state(10)["pending"] = event["data"]


def dismiss():
    lesson_state(10)["pending"] = None


@st.dialog("Graph record", on_dismiss=dismiss)
def record_dialog(request):
    state = lesson_state(10)
    operation = request["operation"]
    st.markdown(f"**{operation.replace('_', ' ').capitalize()}**")
    node_ids = [node["data"]["id"] for node in state["elements"]["nodes"]]
    selected_nodes = [
        node_id
        for node_id in request.get("selected_node_ids", [])
        if node_id in node_ids
    ]
    selected = request.get("selected_node_ids", []) + request.get(
        "selected_edge_ids", []
    )
    with st.form("tutorial_10_widget_form"):
        # A form submits these fields together, rather than writing on each edit.
        if operation in {"create_node", "create_edge"}:
            if operation == "create_node":
                label = st.selectbox(
                    "Node type",
                    list(CRUD_NODE_TYPES),
                    format_func=lambda value: f"{CRUD_NODE_TYPES[value]} ({value})",
                    help="Stored as data.label; the matching NodeStyle supplies its color and icon.",
                )
            else:
                label = st.selectbox(
                    "Relationship type",
                    [style.label for style in demo_edge_styles()],
                    help="Stored as the edge's data.label. Choose endpoints separately.",
                )
            new_id = st.text_input(
                "Record ID",
                "new-node" if operation == "create_node" else "new-edge",
            )
            name = st.text_input(
                "Name",
                "New record" if operation == "create_node" else "New relationship",
                help="Display text, independent of the type and the unique record ID.",
            )
            if operation == "create_edge":
                source = st.selectbox(
                    "Source",
                    node_ids,
                    index=node_ids.index(selected_nodes[0]) if selected_nodes else 0,
                )
                target = st.selectbox(
                    "Target",
                    node_ids,
                    index=node_ids.index(selected_nodes[1])
                    if len(selected_nodes) > 1
                    else max(0, len(node_ids) - 1),
                )
        elif operation == "update_selected":
            target_id = st.selectbox("Record to update", selected)
            name = st.text_input("New name", "Updated record")
        else:
            st.markdown(
                "The selected records remain unchanged until you confirm. Loading related data is available for ABC123."
            )
            render_dictionary_preview(
                "Request context",
                request,
                "`operation` is the requested action. Selected IDs identify the targets; `selected_elements` includes their fields and `connected_elements` supplies relationship context.",
                height=200,
            )
        submitted = st.form_submit_button("Confirm", icon=":material/check:")
        cancelled = st.form_submit_button("Cancel")
    if cancelled:
        dismiss()
        st.rerun()
    if not submitted:
        return
    try:
        command_id = next_command_id(state, "crud")
        command = None
        if operation in {"create_node", "create_edge"}:
            new_id = new_id.strip()
            if not new_id or get_element(state["elements"], new_id):
                raise ValueError("Use a non-empty, unique record ID.")
            # Category controls styling; the independent ID is the relationship key.
            data = {"id": new_id, "name": name, "label": label}
            if operation == "create_node":
                command = upsert_elements_command(
                    command_id,
                    nodes={
                        "data": data,
                        "position": request.get(
                            "suggested_position", {"x": 500, "y": 300}
                        ),
                    },
                )
            else:
                if not source or not target:
                    raise ValueError("Create endpoint nodes before an edge.")
                data.update(source=source, target=target)
                command = upsert_elements_command(command_id, edges={"data": data})
        elif operation == "update_selected":
            if not target_id:
                raise ValueError("Select a record first.")
            command = update_data_command(command_id, target_id, {"name": name})
        elif operation == "delete_selected":
            command = delete_elements_command(
                command_id,
                node_ids=request.get("selected_node_ids"),
                edge_ids=request.get("selected_edge_ids"),
            )
        elif operation == "request_node_data":
            if "ABC123" not in request.get("selected_node_ids", []):
                raise ValueError(
                    "This sample source has related records only for ABC123."
                )
            command = upsert_elements_command(command_id, **related_records())
        if command:
            # Apply the same validated change to Python and queue it for the browser.
            queue_command(state, command)
        state["notice"] = f"Completed {operation}."
    except (ValueError, TypeError) as error:
        st.error(str(error))
        return
    dismiss()
    st.rerun()


state = begin_lesson(
    10,
    contents=(
        "Source data",
        "CRUD or browser editing?",
        "Code and working graph",
        "Creation types",
        "How this example works",
        "Try it and check the result",
        "Code in practice",
        "Accepted Python records",
        "Data and practical result",
        "Common mistakes and next step",
    ),
)
show_graph_data(state["elements"])
show_workflow_comparison(10)
st.header("Code and working graph")
st.markdown(
    "Add a node, then create an edge whose endpoint is that node. Read, update, delete, and load-related requests include selection context. Each request opens a dialog; Cancel must leave the graph unchanged."
)
st.subheader("Creation types")
st.markdown("""
Choose **Node type** in the Create node dialog: location, vehicle, person, phone,
camera, time, or checkpoint. **Relationship type** offers Seen At, Registered To,
Uses, Seen Near, and Related. These are this application's sample vocabulary,
not a closed list imposed by the library; applications can use other labels.

`id` is unique across nodes and edges. `label` is the category used by
`NodeStyle` or `EdgeStyle`; `name` is separate display text. A location uses
`PLACE` because that is the category in the source data and its style rule.
Changing the Name to "Camera 8" alone does not change a node's type: choose
**Camera (CAMERA)** too. The starter ID is editable for every type.

This lesson checks IDs and endpoint references. It does not enforce rules such
as which types may be connected; add those business rules before accepting a
write in a production app. Update selected currently changes a record's name.
""")
st.subheader("How this example works")
st.markdown("""
CRUD means create, read, update, and delete. In this lesson the graph requests an
operation, but Python decides whether and how it happens. This is the useful
boundary when permissions, validation, or a database transaction must come first.

1. A graph CRUD action emits a `crud` event. `handle_crud()` stores the request
   and opens `record_dialog`; the source records have not changed yet.
2. The dialog gathers a type, unique ID, name, or existing endpoints. Read
   shows the selected record context. Update and delete require selected records.
3. **Confirm** validates the input and builds an incremental command.
   `queue_command` validates that command, applies it to the Python checkpoint,
   and queues it for the browser. **Cancel** or dismissing the dialog leaves
   the records unchanged.
4. `elements_sync="initial"` keeps ordinary reruns from resending the full graph;
   commands deliver accepted changes while the full checkpoint remains available
   if the component is mounted again.

The persistence demonstrated here is session state. In a production application,
authorize and commit the accepted edit to your data store before treating it as
saved. A browser event and its selected IDs are context, not authorization.
""")
with show_example(__file__):
    result = graph_workbench(
        state["elements"],
        layout={"name": "preset", "padding": 60},
        node_styles=demo_node_styles(text_size=18),
        edge_styles=demo_edge_styles(),
        crud_actions=list(get_args(CrudAction)),
        selection_mode="multiple",
        return_selection=True,
        elements_sync="initial",
        # The dialog sends accepted changes; a raw CRUD intent is not a write.
        graph_commands=state["commands"],
        key=component_key(10),
        on_change=handle_crud,
        height=600,
    )
# Render the modal beside the component that emitted the request. Streamlit can
# then show it before rebuilding the lesson's longer documentation sections.
if state.get("pending"):
    record_dialog(state["pending"])
# Conditional feedback must not shift the live component's element-tree position.
if state.get("notice"):
    st.success(state["notice"])
st.subheader("Try it and check the result")
st.markdown("""
1. Open Create node, then cancel. Counts stay at 7 nodes / 5 edges. Open it again
   and enter `new-location` as its unique ID: expect 8 nodes / 5 edges after Confirm.
2. Select ABC123 and the new node, then open Create edge. At least one node must
   be selected to enable that action; two selections prefill both endpoints.
   Create an edge from ABC123 to the new node. Confirm its Source and Target
   fields explicitly; expect 8 nodes / 6 edges and a visible connection.
3. Select the new record, inspect it with Read, then update its name. Its ID
   should remain unchanged. Try an already-used ID when creating another node
   and read the validation message without losing the current graph.
4. Delete the new node and confirm. Its incident edge is removed too, restoring
   the original counts. Related-data requests are a separate application action;
   this sample provides additional data for ABC123 only.
5. Create `camera-8` with type Camera and name "Camera 8". Create a **Related**
   edge between ABC123 and camera-8. The camera icon and relationship label should
   match the chosen types, and the accepted-records table below updates too.
6. Cancel a new record or submit an existing ID. No record is added. In browser
   editing, Add Browser Node instead creates an unclassified draft immediately.
""")
st.subheader("Code in practice")
show_function(
    handle_crud,
    "**Receive the request.** The callback reads this lesson's component event "
    "and retains only CRUD requests for the dialog to handle.",
)
show_function(
    queue_command,
    "**Accept one change.** Confirm uses this helper to validate the command, "
    "update Python records, and queue the same instruction. This is session-state "
    "persistence only; authorization and database writes belong in your application.",
)
with st.expander("Dialog code: types, validation, and confirmation"):
    show_function(
        record_dialog,
        "The executing dialog branches on operation. Follow create_node/create_edge "
        "to see type fields, then submitted and the try/except boundary. Cancel "
        "returns without queueing a command.",
    )
st.subheader("Accepted Python records")
st.markdown(
    "These are the session-state records after confirmed requests. The command "
    "below instructs the browser to apply the same change; it is not a browser "
    "readback or proof of a database save. Compare these counts with the canvas."
)
st.caption(
    f"Accepted records: {len(state['elements']['nodes'])} nodes / {len(state['elements']['edges'])} edges"
)
st.dataframe(records_to_dataframe(state["elements"]), hide_index=True, height=240)
render_dictionary_preview(
    "Latest accepted graph command",
    state["commands"],
    "The command list is sent only after validation. command_id identifies delivery; operation names the change; nodes/edges or data contain the chosen types and fields. Cancelling a new dialog does not alter the previous command.",
    height=220,
)
show_result(
    state.get("results", {}).get("crud"),
    "A `crud` event is an intent, not a completed write. `operation` names the request, selected IDs identify targets, and `suggested_position` places a new node in the current view. Confirm validates and applies a command to Python state, then sends it to the browser.",
    label="CRUD request event",
)
finish_lesson(
    10,
    __file__,
    mistakes="Never treat a browser request as authorization. Validate IDs and endpoints before saving. Use unique command IDs; do not change the component key after each edit.",
    conclusion="Your application can attach validation, authorization, and persistence to every CRUD request without losing the interactive graph.",
)
