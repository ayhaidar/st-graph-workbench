"""Apply pure element helpers to a Python-owned graph."""

import streamlit as st
from demos.demo_helpers import demo_node_styles
from st_graph_workbench import (
    delete_elements,
    get_element,
    graph_workbench,
    records_to_dataframe,
    update_element_data,
    upsert_elements,
)
from tutorials.common import (
    show_example,
    begin_lesson,
    component_key,
    finish_lesson,
    show_graph_data,
    show_result,
)

state = begin_lesson(2)
show_graph_data(state["elements"])
st.header("Code and working graph")
st.markdown(
    "**Scope of this example.** All four operations target one node with the fixed "
    "ID `checkpoint`. Add creates this location and the `checkpoint-visit` edge "
    "from `ABC123`; Get reads the checkpoint; Update changes its name; Delete "
    "removes it and its incident edge. Selecting another node on the canvas does "
    "not change this target. ABC123 and the other original sample records remain intact."
)
st.subheader("How this example works")
st.markdown("""
The element helpers operate on Python dictionaries without needing a browser.
This makes them useful in data preparation, validation pipelines, and application
callbacks as well as in an interactive page.

- **Get** uses `get_element` to look up a node or edge by ID. A missing record
  returns `None`; it is not a failed graph render.
- **Add** uses `upsert_elements` to include a checkpoint node and its edge in
  one new graph dictionary. Upsert also updates a matching ID, so repeating the
  operation does not create a second checkpoint.
- **Update** changes the checkpoint's `name` with `update_element_data`. The ID
  and the edge endpoints remain unchanged.
- **Delete** removes the checkpoint and its incident relationship. Removing the
  edge alone would leave both endpoint nodes present.

The helper result is assigned to `state["elements"]`, then `st.rerun()` refreshes
the table and graph from that same checkpoint. Session state retains this
lesson's records during in-session navigation; it is not durable database storage.

This is deliberately a single-node example, not a restriction of the library.
The helpers accept other record IDs, and `upsert_elements` and `delete_elements`
can also process multiple records. The selection and CRUD lessons show how to
choose operation targets from a user's graph selection.
""")
with show_example(__file__):
    operation = st.selectbox(
        "Record operation",
        ["Get", "Add", "Update", "Delete"],
        key="tutorial_02_widget_operation",
    )
    if st.button("Apply operation", icon=":material/play_arrow:"):
        elements = state["elements"]
        if operation == "Add":
            # Accept the new node and its relationship together as one valid graph.
            elements = upsert_elements(
                elements,
                nodes={
                    "data": {"id": "checkpoint", "label": "PLACE", "name": "Checkpoint"}
                },
                edges={
                    "data": {
                        "id": "checkpoint-visit",
                        "source": "ABC123",
                        "target": "checkpoint",
                        "label": "Seen At",
                    }
                },
            )
        elif operation == "Update" and get_element(elements, "checkpoint"):
            # Keep the ID stable: only the display name changes.
            elements = update_element_data(
                elements, "checkpoint", {"name": "Updated checkpoint"}
            )
        elif operation == "Delete":
            # Incident edges are removed too, avoiding dangling endpoints.
            elements = delete_elements(elements, node_ids=["checkpoint"])
        state["elements"] = elements
        state["result"] = get_element(elements, "checkpoint")
        st.rerun()
    result = graph_workbench(
        state["elements"],
        layout={"name": "grid", "padding": 60},
        node_styles=demo_node_styles(text_size=18),
        height=600,
        key=component_key(2),
    )
st.subheader("Try it and check the result")
st.markdown("""
1. Choose **Get** and apply it before adding anything. The result is `null`
   because `checkpoint` does not yet exist.
2. Apply **Add**: the counts change from 7 nodes / 5 edges to 8 nodes / 6 edges.
   Apply Add again and confirm that the counts stay the same.
3. Apply **Update** and find `Updated checkpoint` in the table and on the graph.
4. Apply **Delete**. Counts return to 7 / 5 and the lookup becomes `null` again.

The important connection is between the lookup result, source table, and live
graph: all three should describe the same Python-owned state after each action.
""")
st.subheader("Code in practice")
st.markdown(
    "Inspect the fixed target and its relationships directly in Python. The "
    "table contains one edge after Add and no edges after Delete, regardless of "
    "which record is selected on the canvas."
)
with show_example(__file__):
    # A missing record returns None; reading does not create it.
    checkpoint_record = get_element(state["elements"], "checkpoint")
    st.caption("Checkpoint exists" if checkpoint_record else "Checkpoint is absent")
    incident_edges = [
        edge
        for edge in state["elements"]["edges"]
        if "checkpoint" in (edge["data"]["source"], edge["data"]["target"])
    ]
    st.dataframe(records_to_dataframe(incident_edges), hide_index=True, height=180)
show_result(
    {"element": state.get("result")},
    "`element` is the complete record returned by `get_element`, or `null` (Python `None`) if the checkpoint does not exist. The helpers return new graph dictionaries; assigning that result to session state makes it survive reruns.",
    label="Python lookup result",
)
finish_lesson(
    2,
    __file__,
    mistakes="Add the checkpoint before updating it. A caption update must not change its ID. Deleting a node normally removes its incident edges too.",
    conclusion="Python owns these changes. A database-backed application can authorize and persist the same operations before sending the updated graph.",
)
