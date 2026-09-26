import streamlit as st
from st_graph_workbench import EdgeStyle, NodeStyle, StyleRule, graph_workbench
from demos.demo_helpers import (
    render_demo_intro,
    render_dictionary_preview,
    render_elements_dataframe,
    render_source_expander,
)

render_demo_intro(
    "Compound nodes and performance",
    """
    Cytoscape supports compound nodes through `node.data.parent`. This lets a
    graph show entities grouped inside cases, locations, time windows, devices,
    or other containers. The Python validator checks that every parent ID
    exists.
    """,
    [
        (
            "Compound parent nodes",
            "`node.data.parent` groups child nodes inside a parent.",
        ),
        (
            "Parent styling",
            "`StyleRule('node:parent', ...)` styles compound containers.",
        ),
        (
            "Performance profiles",
            "`default`, `large`, and `dense` change frontend rendering defaults.",
        ),
        (
            "Analysis with groups",
            "Connected components and degree still run on grouped graphs.",
        ),
    ],
    sections=[
        (
            "Capability coverage",
            "Compound parent nodes, parent styling, performance profiles, and analysis on grouped graphs.",
        ),
        (
            "Performance profile",
            "A profile selector that changes frontend rendering defaults for heavier graphs.",
        ),
        (
            "Data before rendering",
            "Compound node records with `parent` fields and the edges between child nodes.",
        ),
        (
            "Interactive graph",
            "A compound graph with case containers, styled children, selection, and analysis tools.",
        ),
        (
            "Returned dictionary",
            "The selection or analysis payload returned from the grouped graph.",
        ),
        (
            "What the JavaScript is doing",
            "How Cytoscape interprets `parent` fields and performance profile settings.",
        ),
    ],
)

performance_profile = st.selectbox(
    "Performance profile",
    ["default", "large", "dense"],
    help="Large and dense profiles reduce rendering work for heavier graphs.",
)

elements = {
    "nodes": [
        {"data": {"id": "case_a", "label": "CASE", "name": "Case 118"}},
        {"data": {"id": "case_b", "label": "CASE", "name": "Case 203"}},
        {
            "data": {
                "id": "vehicle_a",
                "label": "VEHICLE",
                "name": "ABC123",
                "parent": "case_a",
            }
        },
        {
            "data": {
                "id": "vehicle_b",
                "label": "VEHICLE",
                "name": "QRT982",
                "parent": "case_b",
            }
        },
        {
            "data": {
                "id": "person_a",
                "label": "PERSON",
                "name": "Maya Reed",
                "parent": "case_a",
            }
        },
        {
            "data": {
                "id": "person_b",
                "label": "PERSON",
                "name": "Omar Khan",
                "parent": "case_b",
            }
        },
        {
            "data": {
                "id": "checkpoint",
                "label": "CHECKPOINT",
                "name": "Harbor Camera 4",
            }
        },
        {
            "data": {
                "id": "time_window",
                "label": "TIME",
                "name": "02 Sep 2024 08:14",
            }
        },
    ],
    "edges": [
        {
            "data": {
                "id": "e1",
                "label": "REGISTERED_TO",
                "source": "vehicle_a",
                "target": "person_a",
            }
        },
        {
            "data": {
                "id": "e2",
                "label": "REGISTERED_TO",
                "source": "vehicle_b",
                "target": "person_b",
            }
        },
        {
            "data": {
                "id": "e3",
                "label": "SEEN_AT",
                "source": "vehicle_a",
                "target": "checkpoint",
            }
        },
        {
            "data": {
                "id": "e4",
                "label": "SEEN_AT",
                "source": "vehicle_b",
                "target": "checkpoint",
            }
        },
        {
            "data": {
                "id": "e5",
                "label": "OBSERVED_DURING",
                "source": "checkpoint",
                "target": "time_window",
            }
        },
    ],
}

node_styles = [
    NodeStyle("CASE", "#E8EEF7", "name", size=80, raw_style={"text-valign": "top"}),
    NodeStyle("VEHICLE", "#2A629A", "name", "directions_car", size=34),
    NodeStyle("PERSON", "#FF7F3E", "name", "person", size=30),
    NodeStyle("CHECKPOINT", "#2D936C", "name", "photo_camera", size=34),
    NodeStyle("TIME", "#8A5A44", "name", "schedule", size=32),
    StyleRule(
        "node:parent",
        {
            "padding": 24,
            "background-opacity": 0.18,
            "border-width": 2,
            "border-color": "#8A9DB6",
        },
    ),
]

edge_styles = [
    EdgeStyle("REGISTERED_TO", "#2A629A", "label", directed=True),
    EdgeStyle("SEEN_AT", "#D72638", "label", directed=True, width=3),
    EdgeStyle("OBSERVED_DURING", "#8A5A44", "label", directed=True),
]

st.markdown("## Data before rendering")
st.markdown(
    """
    The `parent` values in the node records below are what make Cytoscape draw
    `case_a` and `case_b` as compound containers around their child entities.
    """
)
render_elements_dataframe(elements, "Compound graph records")

value = graph_workbench(
    elements,
    layout="fcose",
    node_styles=node_styles,
    edge_styles=edge_styles,
    node_actions=["show_neighbors", "hide_unselected", "restore_hidden"],
    selection_mode="multiple",
    return_selection=True,
    analysis_actions=["connected_components", "degree"],
    performance_profile=performance_profile,
    key="compound_performance",
    height=560,
)

render_dictionary_preview(
    "Returned compound-graph value",
    value or {},
    """
    This dictionary is returned after selecting or analyzing the grouped graph.
    It is useful for confirming that compound parent nodes still return normal
    selected IDs, connected context, and analysis payloads.
    """,
    height=340,
    expanded=True,
)

st.markdown("## What The JavaScript Is Doing")
st.markdown(
    """
    The `parent` field is not interpreted by Python; it is validated and then
    passed to Cytoscape. Cytoscape draws compound parent nodes around their
    children. The performance profile is a small frontend style/layout preset
    that reduces label and edge rendering cost for larger graphs.
    """
)


render_source_expander(__file__)
