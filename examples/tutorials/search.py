"""Search within a graph and inspect neighborhood visibility events."""

from functools import partial
import streamlit as st
from demos.demo_helpers import demo_node_styles
from st_graph_workbench import graph_workbench, records_to_dataframe
from tutorials.common import (
    show_example,
    begin_lesson,
    component_key,
    finish_lesson,
    receive_event,
    show_graph_data,
    show_result,
)

state = begin_lesson(7)
show_graph_data(state["elements"])
st.header("Code and working graph")
st.markdown(
    "Search scenarios: text `ABC123`; node label `PLACE`; edge label `Seen At`; property `confidence` with value `0.94`; selector `node[id = 'ABC123']`. Search should focus its matches, not the whole graph."
)
st.subheader("How this example works")
st.markdown("""
Search is a way to choose a starting point in records already available to this
component. Text searches property values; label modes match node or edge
categories; property search narrows the query to one field. Selector mode uses
Cytoscape selector syntax, such as `node[id = 'ABC123']`, for precise targeting.
This lesson does not query an external data source.

Choose the mode, enter the query, then press Enter or Apply Search. Search
inputs and dropdowns keep a readable text size on smaller screens; controls
move onto additional rows when space is limited. Node captions belong to the
graph itself and scale with graph zoom, independently of the search input.

Search reports matches and focuses their extent. Finding several records can
therefore frame a region, while finding one should focus that particular record.
`matched_node_ids` and `matched_edge_ids` identify the results independently of
their captions; `matched_elements` lets Python inspect their properties.

Neighborhood tools answer a different question: **what is connected to my
selection?** Incoming edges point toward the selected node; outgoing edges point
away from it, according to `source` and `target`. A neighborhood view or
**Hide unselected** changes visibility, not the authoritative Python data.
**Restore hidden** reverses that temporary restriction. Provider-backed search
and restoration of collapsed branches are covered in the expansion lesson.
""")
with show_example(__file__):
    # Search operates on records already available to this browser instance.
    result = graph_workbench(
        state["elements"],
        layout={"name": "preset", "padding": 60},
        node_styles=demo_node_styles(text_size=18),
        search=True,
        selection_mode="multiple",
        return_selection=True,
        node_actions=[
            # Direction follows edge source/target; hiding does not delete records.
            "show_neighbors",
            "show_incoming",
            "show_outgoing",
            "hide_unselected",
            "restore_hidden",
        ],
        key=component_key(7),
        on_change=partial(receive_event, 7),
        height=600,
    )
st.subheader("Try it and check the result")
st.markdown("""
1. Search for ABC123 in text mode, then use the exact ID selector. Compare the
   matched IDs, not only the zoom level, to confirm what the search found.
2. Search the edge property `confidence` for `0.94`. The match is a sighting
   edge, not a vehicle node: properties belong to individual records.
3. Select Location 1 and show incoming neighbors. ABC123 and ALPHA both have
   edges pointing to it. Compare this with outgoing neighbors.
4. Restore hidden records and confirm the canvas returns to 7 nodes / 5 edges.
   The Python source table was not reduced by the visibility operations.

Clear a search before starting a different question, and read the latest
event's `action`: a search result and a visibility result have different fields.
""")
st.subheader("Code in practice")
st.markdown(
    "Use matched records to populate a review table. This keeps the latest "
    "search report even if a later neighborhood action emits a visibility event. "
    "It is empty until a search reports matches; it is not a new source query."
)
with show_example(__file__):
    # Match data belongs to the search action, not every possible component event.
    search_event = state.get("results", {}).get("search", {})
    search_data = search_event.get("data", {})
    matches = records_to_dataframe(search_data.get("matched_elements", []))
    st.dataframe(matches, hide_index=True, height=220)
show_result(
    state["event"],
    "A search result identifies its `mode`, `query`, `match_count`, and `matched_node_ids`/`matched_edge_ids`. `matched_elements` contains matching records. Visibility events describe the operation and visible/hidden counts. They change browser visibility, not your Python-owned source records.",
    label="Latest component event",
)
st.markdown(
    "**Practical result.** ABC123 connects to two locations. Incoming neighbors of Location 1 include ABC123 and ALPHA. Restoring hidden records makes the full source graph visible again."
)
finish_lesson(
    7,
    __file__,
    mistakes="Choose the correct search mode; a label is a category, while a property is a field on a record. Hidden records still exist and may be included in a full-data export.",
    conclusion="Search finds starting points; neighborhood tools let users inspect the relevant context without deleting information.",
)
