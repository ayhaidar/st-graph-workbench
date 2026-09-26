"""Custom listeners and dynamic options across independent component instances."""

from functools import partial
import streamlit as st
from demos.demo_helpers import demo_node_styles, render_dictionary_preview
from st_graph_workbench import Event, get_element, graph_workbench, records_to_dataframe
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

state = begin_lesson(16)
show_graph_data(state["elements"])
st.header("Code and working graph")
st.markdown(
    "Both graphs start from identical records but have separate component keys. Click a node or edge in either graph. Change search or selection on the first graph and confirm that the second graph remains independent."
)
st.subheader("How this example works")
st.markdown("""
`Event("record_tapped", "tap", "node, edge")` has three parts: an
application-specific action name, the Cytoscape interaction to listen for, and
a selector defining eligible targets. The second listener maps a node double-tap
to `record_double_tapped`. These are observations of user interaction, not
instructions to edit a record.

Each graph has a distinct stable key. Its `on_change` callback reads that key's
payload and stores results under `results_first` or `results_second`. The two
graphs can start from the same Python records without sharing browser selection,
camera position, or interaction history. Different keys create that separation;
different layouts alone do not.

One click can trigger both a custom event and a built-in selection event. The
lesson retains the latest result **per action** so the selection does not hide
the earlier custom payload. This is not an append-only audit log: a later event
with the same action replaces the earlier one. Store a separate history with
your own retention rules when every interaction must be recorded.

The toggles change options on the first component while retaining its key.
The second graph should remain independent. Replacing a key intentionally
creates a new instance, which is different from updating a supported live option.
""")
search = st.toggle("Search on the first graph", key="tutorial_16_widget_search")
multiple = st.toggle(
    "Multiple selection on the first graph",
    value=True,
    key="tutorial_16_widget_multiple",
)
with show_example(__file__):
    listeners = [
        # Arguments are application action name, Cytoscape event, and target selector.
        Event("record_tapped", "tap", "node, edge"),
        Event("record_double_tapped", "dbltap", "node"),
    ]
    first = graph_workbench(
        state["elements"],
        layout={"name": "preset", "padding": 60},
        node_styles=demo_node_styles(text_size=18),
        events=listeners,
        search=search,
        selection_mode="multiple" if multiple else "single",
        return_selection=True,
        height=600,
        # Separate keys and callback namespaces keep the two graphs independent.
        key=component_key(16, "first"),
        on_change=partial(receive_event, 16, "first"),
    )
    second = graph_workbench(
        state["elements"],
        layout="circle",
        node_styles=demo_node_styles(text_size=18),
        events=listeners,
        return_selection=True,
        height=600,
        key=component_key(16, "second"),
        on_change=partial(receive_event, 16, "second"),
    )
st.subheader("Try it and check the result")
st.markdown("""
1. Click ABC123 in the first graph. Find `record_tapped` and `selection` in its
   result dictionary; the second graph has not selected the same node for you.
2. Click ALPHA in the second graph. Its callback produces separate results.
   Double-click a node to inspect `record_double_tapped` as a different action.
3. Enable search on the first graph or switch its selection mode. Check that
   the second graph's selection and layout stay as they were.
4. Inspect the target ID and group in a node event and an edge event. Use that
   ID to retrieve the authoritative record before performing an application action.

These callbacks can drive a details pane, a table filter, or a follow-up query.
Custom action names describe your application's intent without replacing the
component's reserved built-in event names.
""")
st.subheader("Code in practice")
st.markdown(
    "Resolve the first graph's latest tapped ID against the Python source. "
    "This can drive a detail view or a follow-up query. A later selection event "
    "does not replace record_tapped; the table is empty before the first tap."
)
with show_example(__file__):
    # Event targets supply identifiers, not authority to change the corresponding record.
    tapped = state.get("results_first", {}).get("record_tapped", {})
    target_id = tapped.get("data", {}).get("target_id")
    record = get_element(state["elements"], target_id) if target_id else None
    st.dataframe(
        records_to_dataframe([record] if record else []), hide_index=True, height=180
    )
with st.expander("Callback code: separate component keys and retained events"):
    show_function(
        receive_event,
        "Both graphs use this helper with different instance arguments. It "
        "deduplicates the last payload and stores results per action and instance, "
        "so one graph's tap cannot replace the other graph's event history.",
    )
show_result(
    state.get("results_first"),
    "The first graph's callback reads its own component key. This dictionary retains the latest payload for each action, so a later selection does not hide a custom event. Custom events contain `type`, `target_id`, `target_group`, and a timestamp; selection uses the built-in selection payload.",
    label="First graph events by action",
)
render_dictionary_preview(
    "Second graph events by action",
    state.get("results_second"),
    "These latest-by-action payloads belong only to the second component. Comparing the two dictionaries demonstrates that selection, view, and listeners are not shared between instances.",
    height=240,
)
finish_lesson(
    16,
    __file__,
    mistakes="Use unique stable keys for separate graphs and application-specific event names. Reserved action names cannot be used for custom listeners. Changing a key intentionally creates a new instance.",
    conclusion="You can combine graph exploration with the rest of a Streamlit application through structured events, independent instances, and Python-owned state. Feature Lab remains available for deeper experimentation.",
)
