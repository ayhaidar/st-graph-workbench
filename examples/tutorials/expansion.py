"""Explore independent branches without losing source records or shared connections."""

from expansion_data import expansion_source, expansion_start
from expansion_workflow import render_expansion_workflow
from tutorials.common import begin_lesson, component_key, finish_lesson, show_graph_data

state = begin_lesson(9, expansion_start)
show_graph_data(
    expansion_source(),
    "The complete example contains vehicles, locations, cameras, times, and reports. These are sample entities: the same branch rules apply to any connected dataset. Only ABC123 is initially displayed.",
)
render_expansion_workflow(state, component_key(9))
finish_lesson(
    9,
    __file__,
    mistakes="Do not delete source records to collapse a view or treat every graph as a tree. Shared nodes and edges may belong to several active branches. Source totals and displayed-graph metrics answer different questions. Legacy node_actions=['expand'] remains supported; enable_node_actions is deprecated.",
    conclusion="The ExpansionController separates source data, cached records, and the displayed graph. Reopening restores nested exploration and saved positions; bounded loading and explicit analysis scope keep exploration reproducible.",
)
