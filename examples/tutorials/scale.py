"""Grow fixed-position records and compare compound and performance options."""

from functools import partial
from typing import get_args
import streamlit as st
from demos.demo_helpers import demo_node_styles
from st_graph_workbench import PerformanceProfile, StyleRule, graph_workbench
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
from tutorials.data import fleet_graph

state = begin_lesson(14)
count = st.select_slider(
    "Vehicle records",
    options=[10, 50, 100, 250, 500, 1000],
    value=state.get("count", 50),
    key="tutorial_14_widget_count",
)
compound = st.toggle(
    "Group vehicles under a parent",
    value=state.get("compound", False),
    key="tutorial_14_widget_compound",
)
profile = st.segmented_control(
    "Performance profile",
    list(get_args(PerformanceProfile)),
    default=state.get("profile", "default"),
    required=True,
    key="tutorial_14_widget_profile",
)
state["elements"] = fleet_graph(count, compound=compound)
state.update(count=count, compound=compound, profile=profile)
show_graph_data(
    state["elements"],
    "Three location hubs connect to generated vehicle records with time fields. Coordinates are deterministic, so increasing the count does not shuffle previously loaded records.",
)
st.header("Code and working graph")
st.markdown(
    "A compound node groups its children through `data.parent`. Compare profiles at the same node count; they tune rendering, not the number of records. Large graphs also need bounded loading and an appropriate layout."
)
st.subheader("How this example works")
st.markdown("""
`fleet_graph(count)` generates one edge per vehicle to one of three location
hubs. With 50 vehicles the ungrouped graph therefore has **53 nodes and 50
edges**, not 50 nodes. Increasing the control to 100 vehicles produces 103 nodes
and 100 edges. IDs and generated positions remain deterministic so you can
compare sizes without introducing a different dataset on every rerun.

Grouping adds a `fleet` parent node and gives each vehicle `data.parent="fleet"`.
This is compound containment, not an extra relationship edge. The three hubs
remain outside the parent; enabling grouping adds one node, but no extra sighting
edges. The `:parent` style rule draws the group's boundary and caption.

The **default**, **large**, and **dense** profiles choose rendering/layout
defaults. They do not sample data, discard edges, or change the meaning of a
selection. Compare them at the same graph size before attributing a difference
to the profile. Preset positions avoid a global force-layout calculation here,
but drawing, hit testing, event payloads, and Python/browser transfer still cost
more as the graph grows.

This generated graph is relatively sparse. A graph with the same number of nodes
and many more edges can behave differently. For larger applications, combine an
appropriate profile with bounded expansion or loading rather than assuming a
profile makes every dataset inexpensive.
""")
with show_example(__file__):
    styles = [
        *demo_node_styles(text_size=18),
        # :parent matches containment nodes, not all nodes connected by edges.
        StyleRule(
            ":parent",
            {"background-opacity": 0.08, "border-width": 1, "label": "data(name)"},
        ),
    ]
    result = graph_workbench(
        state["elements"],
        layout={"name": "preset", "padding": 60},
        node_styles=styles,
        # Profiles tune rendering defaults; they do not reduce the source records.
        performance_profile=profile,
        selection_mode="multiple",
        return_selection=True,
        search=True,
        key=component_key(14),
        on_change=partial(receive_event, 14),
        height=600,
    )
st.subheader("Try it and check the result")
st.markdown("""
1. Start with 50 vehicles and grouping off. Confirm 53 nodes / 50 edges in the
   source count, then enable grouping and confirm 54 nodes / 50 edges.
2. Keep that size fixed while comparing default, large, and dense. Pan, select,
   and search for `vehicle-0`; these functions should remain available.
3. Increase the count in stages up to 1,000 vehicles. Observe readability and
   responsiveness as well as counts; this is a practical comparison, not a
   timed performance benchmark.

Parent membership organizes a view but does not summarize or collapse its
children automatically. Use the branch controller when reversible exploration,
shared-record ownership, and loading limits are needed.
""")
st.subheader("Code in practice")
st.markdown(
    "Count the graph after generation, not just the requested vehicle rows. "
    "The three hubs and optional parent are additional nodes; each vehicle "
    "contributes one sighting edge."
)
with show_example(__file__):
    # Parent containment changes the node count, not the number of relationships.
    graph_counts = {
        "vehicles": count,
        "nodes": len(state["elements"]["nodes"]),
        "edges": len(state["elements"]["edges"]),
        "parents": int(compound),
    }
    st.caption(
        f"Generated graph: {graph_counts['nodes']} nodes / {graph_counts['edges']} edges"
    )
with st.expander("Generator code: stable IDs, positions, and parent membership"):
    show_function(
        fleet_graph,
        "This is the generator used above. Locate data['parent'] to see containment "
        "and the index-based coordinates to see why increasing count keeps existing positions.",
    )
show_result(
    state["event"] or {"profile": profile, "vehicles": count, "compound": compound},
    "Initially these fields describe the chosen scenario, not a component event. Selection events then provide selected records and neighbor context. Parent membership is stored on each child node's `data.parent`, referring to an existing parent ID.",
    label="Latest component event" if state["event"] else "Scenario configuration",
)
finish_lesson(
    14,
    __file__,
    mistakes="Do not create parent cycles or reference a missing parent. Rendering profiles are not performance guarantees; test your own graph density, devices, and layouts.",
    conclusion="Grouping improves structure, profiles tune rendering, and incremental loading keeps the amount of work bounded.",
)
