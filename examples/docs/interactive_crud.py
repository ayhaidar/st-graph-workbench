import streamlit as st

from page_overview import render_page_overview

st.markdown("# Interactive CRUD For Python Developers")
st.markdown(
    """
    Interactive CRUD in `st_graph_workbench` is intentionally Python-owned. The
    browser does not connect to your database. It only tells Streamlit what the
    user requested and which graph elements were selected.
    """
)

render_page_overview(
    [
        (
            "Mental model",
            "How browser intents, Streamlit reruns, dialogs, session state, and commands fit together.",
        ),
        (
            "Why dialogs",
            "Why Python owns validation, persistence, and database work.",
        ),
        (
            "Returned CRUD event shape",
            "The operation, selected IDs, connected IDs, element records, and suggested position returned by the browser.",
        ),
        (
            "Minimal pattern",
            "A compact CRUD event handler and dialog example.",
        ),
        (
            "CRUD helper functions",
            "The helper APIs used to build and apply command payloads.",
        ),
        (
            "Incremental commands",
            "How larger graphs update through command batches instead of full reloads.",
        ),
    ],
    description="This overview summarizes the CRUD documentation before the code pattern.",
)

st.markdown("## Mental Model")
st.markdown(
    """
    1. Cytoscape stores temporary browser state such as selection and viewport.
    2. A CRUD toolbox button emits an event with selected nodes, selected edges,
       connected node and edge IDs, connected element records, the latest
       selected element, and a suggested canvas position.
    3. Streamlit reruns your Python script.
    4. Your Python code stores the event once and opens a Streamlit dialog.
    5. The dialog lets the user confirm, inspect, create, edit, or delete data.
    6. Python updates `st.session_state["elements"]`.
    7. Python also sends a small `graph_commands` payload for the browser.
    8. The component applies unseen command IDs directly to Cytoscape with
       `cy.batch(...)`.
    """
)

st.markdown("## Returned CRUD Event Shape")
st.markdown(
    """
    CRUD events return a dictionary designed for Python-side decisions and
    screenshots. Use the compact ID lists for commands, then inspect the
    element dictionaries when you need labels, timestamps, risk values, or
    other record fields:

    - `operation`
    - `selected_node_ids` and `selected_edge_ids`
    - `connected_node_ids` and `connected_edge_ids`
    - `last_selected`
    - `selected_elements` and `connected_elements`
    - `suggested_position`
    """
)

st.markdown("## Why Dialogs")
st.markdown(
    """
    Dialogs keep graph editing focused without moving business logic into
    JavaScript. The browser still only says what the user requested. Python
    opens the modal, validates form input, calls databases or APIs if needed,
    updates the session graph, queues an incremental graph command, and reruns
    the app.
    """
)

st.markdown("## Minimal Pattern")
st.code(
    """
from st_graph_workbench import (
    apply_graph_command,
    graph_workbench,
    upsert_elements_command,
)

if "elements" not in st.session_state:
    st.session_state.elements = {"nodes": [], "edges": []}
if "graph_commands" not in st.session_state:
    st.session_state.graph_commands = []
if "command_seq" not in st.session_state:
    st.session_state.command_seq = 0


def queue_command(command):
    st.session_state.elements = apply_graph_command(
        st.session_state.elements,
        command,
    )
    st.session_state.graph_commands = [command]


def command_id(prefix):
    st.session_state.command_seq += 1
    return f"{prefix}-{st.session_state.command_seq}"


def on_graph_event():
    event = st.session_state["graph"]
    if event["action"] != "crud":
        return

    data = event["data"]
    if data["operation"] == "request_node_data":
        st.session_state.active_dialog = "load_related"
        st.session_state.dialog_event = event


@st.dialog("Load related data")
def load_related_dialog(event):
    node_id = event["data"]["selected_node_ids"][0]
    if st.button("Load"):
        related = fetch_related_data(node_id)
        command = upsert_elements_command(
            command_id(f"load-{node_id}"),
            nodes=related["nodes"],
            edges=related["edges"],
        )
        queue_command(command)
        st.session_state.active_dialog = None
        st.rerun()


graph_workbench(
    st.session_state.elements,
    crud_actions=["request_node_data", "read_selected"],
    graph_commands=st.session_state.graph_commands,
    elements_sync="initial",
    key="graph",
    on_change=on_graph_event,
)

if st.session_state.get("active_dialog") == "load_related":
    load_related_dialog(st.session_state.dialog_event)
""",
    language="python",
)

st.markdown("## Why The JavaScript Does Not Fetch Directly")
st.markdown(
    """
    Streamlit apps often use private credentials, internal databases, or Python
    data-processing code. Keeping fetches in Python means credentials stay on
    the server side, validation is centralized, and the same app logic can run
    locally or after deployment.
    """
)

st.markdown("## CRUD Helper Functions")
st.markdown(
    """
    - `get_element(elements, element_id)` reads one node or edge.
    - `upsert_elements(elements, nodes=..., edges=...)` adds or replaces nodes
      and edges.
    - `update_element_data(elements, element_id, data)` updates a node or edge
      data dict.
    - `delete_elements(elements, node_ids=..., edge_ids=...)` removes elements
      and, by default, incident edges.

    Each helper returns a new validated graph dictionary instead of mutating the
    input in place. Treat `update_element_data(...)` as a property edit:
    `data.id` must match the target element when it is included, and replacement
    data must include that matching ID. `delete_elements(...)` accepts one ID
    string or an iterable of IDs for `node_ids` and `edge_ids`. Each ID must be
    a non-empty scalar string, finite number, or boolean. Dictionaries, nested
    containers, non-finite numbers, and arbitrary objects fail before they can
    become surprising string IDs.
    """
)

st.markdown("## Incremental Commands For Larger Graphs")
st.markdown(
    """
    For small graphs, sending the full `elements` dict on every rerun is simple
    and reliable. For larger database-backed graphs, use
    `elements_sync="initial"` plus `graph_commands`.

    With that mode, the first render sends the full graph. After that, Python
    can keep the full graph in `st.session_state`, but send only the latest
    command to the browser:

    - `upsert_elements` for newly fetched nodes and edges
    - `update_data` for property edits
    - `delete_elements` for removals
    - `set_elements` for an explicit full reset
    - `fit`, `center`, `pan`, `zoom`, `set_viewport`, and `set_zoom_bounds`
      for viewport changes

    Each command has a stable `command_id`, so the frontend applies it once even
    if Streamlit reruns with the same command still in session state.

    Treat `update_data` as a property edit. Element IDs are graph identity, so
    `data.id` must match `element_id` when it is included. Use delete/add or
    upsert when a node or edge needs a new ID.
    """
)
