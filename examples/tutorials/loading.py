"""Request, acknowledge, and retry bounded graph batches."""

import streamlit as st
from demos.demo_helpers import demo_node_styles, render_dictionary_preview
from st_graph_workbench import graph_workbench, set_elements_command
from tutorials.common import (
    show_example,
    begin_lesson,
    component_key,
    finish_lesson,
    lesson_state,
    receive_event,
    show_graph_data,
    show_result,
    show_function,
)
from tutorials.workflows import (
    load_next_batch,
    loading_checkpoint,
    next_command_id,
    queue_command,
)


def handle_loading():
    # Ignore selection/search events; only load_more requests query this source.
    event = receive_event(15)
    if event and event["action"] == "load_more":
        state = lesson_state(15)
        # Consume the simulated outcome once so a subsequent request can retry.
        outcome = state.pop("next_outcome", "Success")
        load_next_batch(state, event["data"], outcome=outcome)


def restart_loading():
    state = lesson_state(15)
    queue_command(
        state,
        set_elements_command(next_command_id(state, "restart"), loading_checkpoint()),
    )
    state.update(
        loaded=30, complete=False, acknowledged=None, error="", next_outcome="Success"
    )


state = begin_lesson(15, loading_checkpoint)
show_graph_data(
    state["elements"],
    "Thirty vehicle records and three hubs are loaded initially. Each request can add thirty more vehicles; the sample source has 180 in total.",
)
st.header("Code and working graph")
st.markdown(
    "Pan or select a node, then use Load more. Existing positions and selection should remain stable. Responses intentionally include earlier records to demonstrate duplicate-safe additions."
)
st.subheader("How this example works")
st.markdown("""
Progressive loading pages through a dataset rather than opening a branch around
a particular node. The component asks for more records; Python owns the query,
the continuation cursor, validation, and merging. This sample uses a generated
source so the success and failure cases are reproducible without a service.

1. `progressive_loading` describes the current cursor, page size, displayed
   loading count, and whether another request is allowed.
2. **Load more** emits a `load_more` event. Its `request_id` identifies this
   request; its `cursor` identifies the page; its `page_size` bounds the batch.
3. `handle_loading` passes the request to `load_next_batch`. The handler rejects
   stale cursors and filters overlapping IDs before queuing an add command.
   Existing records are not added a second time.
4. A successful page advances the cursor. Failure leaves both graph and cursor
   unchanged. `acknowledged_request_id` records receipt even on failure so a
   new request can retry that page; acknowledgment is not the same as success.

`loaded_count` and `total_count` refer to **vehicle source records** here. The
three shared location hubs and all edges are counted separately by the graph.
`has_more=False` ends the workflow even when an empty final batch is received.
In a database-backed provider a cursor may be an opaque token rather than this
sample's integer offset.
""")
outcome = st.selectbox(
    "Next response",
    ["Success", "Fail once", "Empty final batch"],
    key="tutorial_15_widget_outcome",
)
with st.container(horizontal=True):
    if st.button("Arm next response", icon=":material/check:"):
        state["next_outcome"] = outcome
    st.button(
        "Restart loading", icon=":material/restart_alt:", on_click=restart_loading
    )
st.caption(
    f"Selected response: {outcome}. "
    f"Armed response: {state.get('next_outcome', 'Success')}."
)
if state.get("error"):
    st.error(state["error"])
with show_example(__file__):
    config = {
        "page_size": 30,
        # Counts track vehicle rows; graph counts also include shared location hubs.
        "loaded_count": state.get("loaded", 30),
        "total_count": 180,
        "cursor": state.get("loaded", 30),
        "has_more": not state.get("complete", False),
        # Receipt is acknowledged on failure too; it does not mean the batch succeeded.
        "acknowledged_request_id": state.get("acknowledged"),
    }
    result = graph_workbench(
        state["elements"],
        layout={"name": "preset", "padding": 60},
        node_styles=demo_node_styles(text_size=18),
        progressive_loading=config,
        graph_commands=state["commands"],
        elements_sync="initial",
        performance_profile="large",
        return_selection=True,
        selection_mode="multiple",
        search=True,
        key=component_key(15),
        on_change=handle_loading,
        height=600,
    )
st.subheader("Try it and check the result")
st.markdown("""
1. Load one successful page. The loading label changes from 30 / 180 to 60 / 180;
   the graph contains 63 nodes and 60 edges because the hubs are shared.
2. Choose **Fail once**, then **Arm next response**, then Load more. Read the
   error: neither the cursor nor the accepted graph advances. Load more again
   to retry successfully; arming affects one request only.
3. Continue to completion. Expect 180 vehicle records, 183 graph nodes, and
   180 edges, with Load more disabled.
4. Restart, arm **Empty final batch**, and request again. Loading finishes at
   the current count, demonstrating that completion need not equal the advertised
   total. Restart again to explore another scenario.

Pan or select between requests to check continuity. Restart loading resets the
data through a command; Reset lesson recreates this lesson's complete checkpoint
and component instance.
""")
st.subheader("Code in practice")
show_function(
    handle_loading,
    "**Route the request.** This callback obtains the load_more payload and passes "
    "it to the application loader. The graph component does not query a database itself.",
)
show_function(
    load_next_batch,
    "**Merge, advance, and acknowledge.** This is the loader executed by that "
    "callback. Follow the duplicate-request guard, cursor check, successful "
    "queue_command, and finally block. Compare loaded/cursor before and after "
    "the failure-and-retry exercise; acknowledgment is separate from completion.",
)
show_result(
    state.get("results", {}).get("load_more"),
    "`load_more` contains `request_id`, `cursor`, and `page_size`. Python checks the cursor before loading. It returns the request ID as `acknowledged_request_id` even on failure so the browser can offer another request. A failed page does not advance the cursor.",
    label="Load-more request event",
)
render_dictionary_preview(
    "Loading state",
    config,
    "`loaded_count` counts vehicle records, not hubs or edges. `has_more=False` ends loading, including an empty final response. Restart sends a set command without replacing the browser instance.",
    height=220,
)
finish_lesson(
    15,
    __file__,
    mistakes="Acknowledge failed and stale requests as well as successful ones. Advance a cursor only after a successful response. Distinguish data-source record counts from node and edge counts.",
    conclusion="The component requests batches; your application decides how to query, merge, retry, and finish the loading workflow.",
)
