"""Five named graph-analysis scenarios with deterministic expected results."""

from functools import partial
import streamlit as st
from analysis_examples import analysis_example_payloads
from demos.demo_helpers import demo_node_styles, render_dictionary_preview
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

state = begin_lesson(8)
show_graph_data(state["elements"])
st.header("Code and working graph")
st.subheader("How this example works")
st.markdown("""
Each scenario enables one browser analysis action so you can connect a specific
question to its result. The browser uses Cytoscape algorithms on the **displayed
graph**. These shortest-path and traversal examples are unweighted and ignore
edge direction: a four-edge route is not a distance in kilometres, a travel-time
estimate, or proof that events occurred in chronological order.

- **Shortest path** finds a route with the fewest edges between two selected
  nodes. ALPHA and BETA are connected through Location 1, ABC123, and Location 2.
- **Breadth-first search (BFS)** explores outward from one selected node in
  layers. It is useful for finding reachable records near a starting point.
- **Depth-first search (DFS)** follows a branch before backtracking. It explores
  reachability too, but its visiting order differs from BFS.
- **Connected components** partitions the graph into groups connected by paths.
  No selection is needed. The separate 12VEC / Location 3 pair forms its own group.
- **Degree** counts incident edges on one selected node. For ABC123 the total
  is 2, with 0 incoming and 2 outgoing edges. Degree measures connectivity, not
  importance, confidence, or causality.

The callback retains the last analysis result separately from later selection
events. Choosing another scenario does not compute it automatically: run its
action, then check `data.analysis` before comparing it with the reference output.
""")
scenarios = analysis_example_payloads(
    state["elements"],
    shortest_path=("ALPHA", "BETA"),
    traversal_root="ABC123",
    degree_node="ABC123",
)
title = st.selectbox(
    "Analysis scenario",
    [item["title"] for item in scenarios],
    key="tutorial_08_widget_scenario",
)
scenario = next(item for item in scenarios if item["title"] == title)
action = scenario["data"]["analysis"]
st.markdown(
    scenario["selection"] + " Run the named action in the graph's analysis menu."
)
with show_example(__file__):
    result = graph_workbench(
        state["elements"],
        layout={"name": "preset", "padding": 60},
        node_styles=demo_node_styles(text_size=18),
        selection_mode="multiple",
        return_selection=True,
        # Enable just this scenario; choosing it does not run the algorithm yet.
        analysis_actions=[action],
        key=component_key(8),
        on_change=partial(receive_event, 8),
        height=600,
    )
if state["event"] and state["event"].get("action") == "analysis":
    state["analysis"] = state["event"]
st.subheader("Try it and check the result")
st.markdown("""
1. Run shortest path with ALPHA and BETA selected. Expect `distance=4`; the
   returned node and edge IDs identify the route's members. Shortest-path ID
   lists are sorted, so do not treat their list order as a route itinerary.
2. Run BFS and DFS separately from ABC123. Both reach the five nodes in its
   connected group, but can visit them in different orders.
3. Run connected components and degree. Expect two components and degree 2 for
   ABC123. The example dictionary is a calculated reference, not a second event.
4. Inspect `scope`, `node_count`, `edge_count`, and `completeness` in the actual
   event. A complete result for the displayed graph does not establish coverage
   of a larger dataset that has not been loaded.

The table below an actual path or traversal joins returned node IDs to source
records. Components instead use `components[].node_ids`; degree uses `node_id`.
Use the result shape appropriate to the algorithm when building a report.
""")
st.subheader("Code in practice")
st.markdown(
    "Turn the actual algorithm result into a source-record table. Paths and "
    "traversals return node_ids; components group their IDs; degree returns one "
    "node_id. The empty table before an analysis is intentional."
)
with show_example(__file__):
    # Read the event that actually ran, not the selected scenario's reference output.
    analysis_data = (state.get("analysis") or {}).get("data", {})
    ids = set(analysis_data.get("node_ids", []))
    if analysis_data.get("analysis") == "connected_components":
        ids = {
            node_id
            for group in analysis_data.get("components", [])
            for node_id in group["node_ids"]
        }
    elif analysis_data.get("analysis") == "degree":
        ids = {analysis_data["node_id"]}
    # Joining by ID preserves application properties the algorithm does not return.
    st.dataframe(
        records_to_dataframe(
            [node for node in state["elements"]["nodes"] if node["data"]["id"] in ids]
        ),
        hide_index=True,
        height=220,
    )
show_result(
    state.get("analysis"),
    "The event envelope has `action='analysis'`, `data`, and `timestamp`.\n\n"
    "- `data.analysis`: which algorithm actually ran.\n"
    "- Paths: `source_id`, `target_id`, `distance`, and result IDs.\n"
    "- Traversals: `root_id` and visited node/edge IDs.\n"
    "- Components: a list of groups, each with node/edge IDs.\n"
    "- Degree: `node_id`, `degree`, `indegree`, `outdegree`, and incident edge IDs.\n\n"
    "Scope/count fields describe the records analyzed. Without managed expansion, source identity/version fields can be null.",
    label="Analysis event",
)
st.markdown(
    "**Expected result for this scenario.** This is a calculated reference for comparison, not a returned browser event. Path ALPHA to BETA has four edges; ABC123 has degree two; the graph has two connected components."
)
render_dictionary_preview(
    "Expected analysis dictionary",
    scenario["data"],
    "Compare these fields with the actual result above. BFS and DFS can visit equal-depth neighbors in different valid orders.",
    height=220,
)
finish_lesson(
    8,
    __file__,
    mistakes="Shortest path needs two selected nodes; BFS, DFS, and degree need one. Components need none. An unreachable destination is different from an empty selection.",
    conclusion="Returned IDs connect algorithm results back to your application records, making graph analysis useful beyond highlighting a route.",
)
