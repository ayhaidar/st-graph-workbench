import json

import streamlit as st

from analysis_examples import analysis_example_payloads, analysis_example_rows
from component_capability_map import javascript_capability_rows
from demos.demo_helpers import (
    capability_rows,
    render_capability_summary,
    render_dictionary_preview,
    render_elements_dataframe,
    render_source_expander,
)
from page_overview import render_javascript_capability_map, render_page_overview
from st_graph_workbench import (
    EdgeStyle,
    NodeStyle,
    StyleRule,
    graph_workbench,
    records_to_dataframe,
)

st.markdown("# Investigation Tools")
st.markdown(
    """
    This demo turns on the link-analysis tools that are useful while exploring a
    graph: richer selection returns, search, neighbor filtering, built-in
    analysis actions, exports, and position returns.
    """
)

render_page_overview(
    [
        (
            "Capability coverage",
            "Selection modes, search, node visibility tools, and graph analysis actions.",
        ),
        (
            "Investigation graph",
            "The graph records used for selection, search, and analysis examples.",
        ),
        (
            "Interactive tools",
            "Pan and box-select canvas modes, search recipes, neighbor filters, export, and returned positions.",
        ),
        (
            "JavaScript to Streamlit mapping",
            "How frontend investigation modules map to Python options.",
        ),
        (
            "Analysis examples",
            "Example shortest path, traversal, connected-component, and degree payloads.",
        ),
        (
            "Try these checks",
            "Small reader checks that verify search, selection, analysis, and returned dictionaries.",
        ),
        (
            "Returned records as a dataframe",
            "A pandas-ready view of the records returned by selection or search.",
        ),
    ],
    description="This investigation overview gives readers the tool route before the graph.",
)

render_capability_summary(
    "What this demo covers",
    [
        row
        for row in capability_rows()
        if row["capability"]
        in {
            "Selection modes",
            "Search",
            "Node actions and visibility",
            "Analysis tools",
        }
    ],
    description="The investigation controls and returned payloads demonstrated here.",
)

elements = {
    "nodes": [
        {
            "data": {"id": "case", "label": "CASE", "name": "Case 42", "risk": 8},
            "position": {"x": 120, "y": 160},
        },
        {
            "data": {
                "id": "vehicle",
                "label": "MAIN_VEHICLE",
                "name": "ABC123",
                "risk": 8,
            },
            "position": {"x": 320, "y": 100},
        },
        {
            "data": {
                "id": "escort_vehicle",
                "label": "VEHICLE",
                "name": "12VEC",
                "risk": 7,
            },
            "position": {"x": 320, "y": 260},
        },
        {
            "data": {"id": "maya", "label": "PERSON", "name": "Maya Reed", "risk": 5},
            "position": {"x": 520, "y": 60},
        },
        {
            "data": {"id": "noah", "label": "PERSON", "name": "Noah Pike", "risk": 4},
            "position": {"x": 520, "y": 220},
        },
        {
            "data": {"id": "lina", "label": "PERSON", "name": "Lina Park", "risk": 6},
            "position": {"x": 520, "y": 340},
        },
        {
            "data": {"id": "omar", "label": "PERSON", "name": "Omar Vale", "risk": 3},
            "position": {"x": 520, "y": 460},
        },
        {
            "data": {
                "id": "time_0814",
                "label": "TIME",
                "name": "02 Sep 2024 08:14",
                "risk": 9,
            },
            "position": {"x": 720, "y": 160},
        },
        {
            "data": {
                "id": "time_0910",
                "label": "TIME",
                "name": "02 Sep 2024 09:10",
                "risk": 10,
            },
            "position": {"x": 720, "y": 320},
        },
        {
            "data": {
                "id": "harbor_camera",
                "label": "CAMERA",
                "name": "Harbor Camera 4",
                "risk": 6,
            },
            "position": {"x": 920, "y": 120},
        },
        {
            "data": {
                "id": "depot_camera",
                "label": "CAMERA",
                "name": "Depot Camera 2",
                "risk": 7,
            },
            "position": {"x": 920, "y": 300},
        },
        {
            "data": {
                "id": "phone",
                "label": "DEVICE",
                "name": "Phone 0412",
                "risk": 8,
            },
            "position": {"x": 720, "y": 500},
        },
        {
            "data": {
                "id": "cell_tower",
                "label": "TOWER",
                "name": "Cell tower T-18",
                "risk": 7,
            },
            "position": {"x": 920, "y": 500},
        },
        {
            "data": {
                "id": "service_depot",
                "label": "LOCATION",
                "name": "Service depot 12",
                "risk": 5,
            },
            "position": {"x": 1120, "y": 390},
        },
    ],
    "edges": [
        {
            "data": {
                "id": "e_case_vehicle",
                "label": "INVESTIGATES",
                "source": "case",
                "target": "vehicle",
            }
        },
        {
            "data": {
                "id": "e_case_escort",
                "label": "INVESTIGATES",
                "source": "case",
                "target": "escort_vehicle",
            }
        },
        {
            "data": {
                "id": "e_vehicle_maya",
                "label": "REGISTERED_TO",
                "source": "vehicle",
                "target": "maya",
            }
        },
        {
            "data": {
                "id": "e_vehicle_noah",
                "label": "DRIVEN_BY",
                "source": "vehicle",
                "target": "noah",
            }
        },
        {
            "data": {
                "id": "e_vehicle_omar",
                "label": "ASSOCIATED_WITH",
                "source": "vehicle",
                "target": "omar",
            }
        },
        {
            "data": {
                "id": "e_escort_vehicle",
                "label": "TRAVELS_WITH",
                "source": "escort_vehicle",
                "target": "vehicle",
            }
        },
        {
            "data": {
                "id": "e_escort_lina",
                "label": "REGISTERED_TO",
                "source": "escort_vehicle",
                "target": "lina",
            }
        },
        {
            "data": {
                "id": "e_maya_time_0814",
                "label": "OBSERVED_AT",
                "source": "maya",
                "target": "time_0814",
            }
        },
        {
            "data": {
                "id": "e_noah_time_0814",
                "label": "OBSERVED_AT",
                "source": "noah",
                "target": "time_0814",
            }
        },
        {
            "data": {
                "id": "e_lina_time_0910",
                "label": "OBSERVED_AT",
                "source": "lina",
                "target": "time_0910",
            }
        },
        {
            "data": {
                "id": "e_time_0814_harbor_camera",
                "label": "RECORDED_BY",
                "source": "time_0814",
                "target": "harbor_camera",
            }
        },
        {
            "data": {
                "id": "e_time_0910_harbor_camera",
                "label": "RECORDED_BY",
                "source": "time_0910",
                "target": "harbor_camera",
            }
        },
        {
            "data": {
                "id": "e_time_0814_depot_camera",
                "label": "SEEN_AT",
                "source": "time_0814",
                "target": "depot_camera",
            }
        },
        {
            "data": {
                "id": "e_time_0910_depot_camera",
                "label": "SEEN_AT",
                "source": "time_0910",
                "target": "depot_camera",
            }
        },
        {
            "data": {
                "id": "e_maya_phone",
                "label": "USES",
                "source": "maya",
                "target": "phone",
            }
        },
        {
            "data": {
                "id": "e_omar_phone",
                "label": "USES",
                "source": "omar",
                "target": "phone",
            }
        },
        {
            "data": {
                "id": "e_phone_tower",
                "label": "CONNECTS_TO",
                "source": "phone",
                "target": "cell_tower",
            }
        },
        {
            "data": {
                "id": "e_tower_depot",
                "label": "LOCATED_AT",
                "source": "cell_tower",
                "target": "service_depot",
            }
        },
        {
            "data": {
                "id": "e_escort_depot",
                "label": "SEEN_AT",
                "source": "escort_vehicle",
                "target": "service_depot",
            }
        },
    ],
}

layout = {"name": "preset", "fit": True, "padding": 40}

node_styles = [
    NodeStyle("CASE", "#6A4C93", "name", "description", size=38),
    NodeStyle("MAIN_VEHICLE", "#2A629A", "name", "directions_car", size=34),
    NodeStyle("VEHICLE", "#1F7A8C", "name", "directions_car", size=34),
    NodeStyle("PERSON", "#FF7F3E", "name", "person", size=30),
    NodeStyle("TIME", "#2D936C", "name", "schedule", size=32),
    NodeStyle("CAMERA", "#C44536", "name", "photo_camera", size=34),
    NodeStyle("DEVICE", "#5F5AA2", "name", "smartphone", size=32),
    NodeStyle("TOWER", "#3D405B", "name", "cell_tower", size=30),
    NodeStyle("LOCATION", "#8A5A44", "name", "place", size=34),
    StyleRule(
        "node[risk >= 8]",
        {
            "border-width": 4,
            "border-color": "#D72638",
            "shape": "diamond",
        },
    ),
]

edge_styles = [
    EdgeStyle("INVESTIGATES", "#6A4C93", "label", directed=True, width=3),
    EdgeStyle("REGISTERED_TO", "#2A629A", "label", directed=True),
    EdgeStyle("DRIVEN_BY", "#2A629A", "label", directed=True),
    EdgeStyle("ASSOCIATED_WITH", "#3D405B", "label", directed=True),
    EdgeStyle("TRAVELS_WITH", "#8A5A44", "label", directed=True, line_style="dotted"),
    EdgeStyle("OBSERVED_AT", "#2D936C", "label", directed=True, width=3),
    EdgeStyle("RECORDED_BY", "#C44536", "label", directed=True, width=3),
    EdgeStyle("SEEN_AT", "#D72638", "label", directed=True, line_style="dashed"),
    EdgeStyle("USES", "#5F5AA2", "label", directed=True),
    EdgeStyle("CONNECTS_TO", "#1F7A8C", "label", directed=True),
    EdgeStyle("LOCATED_AT", "#8A5A44", "label", directed=True, line_style="dashed"),
]

analysis_examples = analysis_example_payloads(
    elements,
    shortest_path=("case", "time_0910"),
    traversal_root="vehicle",
    degree_node="time_0814",
)

st.markdown("## Data before rendering")
st.markdown(
    """
    This graph mixes vehicles, people, times, cameras, devices, and locations.
    Search, box selection, neighbor filters, and analysis tools all return IDs
    from these records so Python can build tables, exports, or follow-up views.
    The canvas mode control separates navigation from rectangular selection:
    use `Pan` to move around the network and `Box select` to select an area.
    """
)
render_elements_dataframe(elements, "Investigation graph records")

st.markdown("## JavaScript to Streamlit mapping")
st.markdown(
    """
    The visible controls below are small JavaScript modules. This demo enables
    them through Streamlit arguments so users can see the Python API surface
    beside the browser behavior.
    """
)
render_javascript_capability_map(
    [
        row
        for row in javascript_capability_rows()
        if row["javascript module"]
        in {
            "analysis.js",
            "boxSelection.js",
            "graph.js",
            "search.js",
            "nodeActions.js",
            "toolbar.js",
            "payloads.js",
        }
    ],
    height=360,
)

st.markdown("## Analysis examples")
st.markdown(
    """
    Each row below corresponds to one Analyze button. The expandable payloads
    show the dictionary returned to Streamlit after the browser-side Cytoscape
    algorithm runs.
    """
)
st.dataframe(analysis_example_rows(analysis_examples), hide_index=True)

for example in analysis_examples:
    with st.expander(example["title"], expanded=example["title"] == "Shortest path"):
        description_column, payload_column = st.columns(
            [0.38, 0.62],
            vertical_alignment="top",
        )
        with description_column:
            st.markdown("**Dictionary description**")
            st.markdown(f"Selection: {example['selection']}")
            st.markdown(
                """
                The top-level `action` is always `analysis`. The nested `data`
                dictionary names the algorithm and returns the node or edge IDs
                that Python can use for tables, evidence summaries, exports, or
                follow-up queries.
                """
            )
        with payload_column:
            with st.container(height=320):
                st.code(
                    json.dumps(
                        {
                            "action": "analysis",
                            "data": example["data"],
                            "timestamp": 1780000000000,
                        },
                        indent=2,
                    ),
                    language="json",
                )

st.markdown("## Interactive tools")
st.markdown(
    "The application's preference below sets whether selection details start "
    "visible. Users can change it inside Selection > Show selection details. "
    "The toolbar checkbox hides details while preserving selected records and "
    "the dataframe below. The panel's X and Clear selection deselect records "
    "without changing that checkbox. An unchanged Python preference preserves "
    "the browser choice across reruns, while changing it overrides that choice."
)
show_details = st.checkbox(
    "Application preference: show selection details",
    value=True,
    key="investigation_tools_details",
)
value = graph_workbench(
    elements,
    layout=layout,
    node_styles=node_styles,
    edge_styles=edge_styles,
    node_actions=[
        "show_neighbors",
        "show_incoming",
        "show_outgoing",
        "hide_unselected",
        "restore_hidden",
    ],
    selection_mode="box",
    return_selection=True,
    show_selection_details=show_details,
    search=True,
    analysis_actions=["shortest_path", "bfs", "dfs", "connected_components", "degree"],
    return_positions=True,
    connected_drag={
        "enabled": False,
        "depth": 1,
        "max_depth": 3,
        "max_nodes": 100,
    },
    toolbar={
        "mode": "adaptive",
        "position": "top",
        "collapsible": True,
        "sticky": True,
    },
    key="investigation_tools",
    height=560,
)

st.markdown("## Try These Checks")
st.markdown(
    """
    - Text search: enter `time` to highlight and select both observation time
      nodes while keeping the whole graph visible.
    - Canvas navigation: choose `Pan`, then drag empty canvas space to move
      around the graph without changing the selection.
    - Box selection: choose `Box select`, then drag a rectangle around `ABC123`
      and `12VEC` to select both vehicle nodes without panning the canvas.
    - Deselecting: click a selected node again to toggle it off, click empty
      canvas space, the panel's X, or `Selection` > clear to clear the whole selection.
    - Details without deselecting: uncheck `Show selection details` in `Selection`,
      then select another record. The returned dataframe still updates. Re-enable `Show selection
      details` in `Selection` to display the current record again.
    - Connected movement: open `Selection`, enable `Move connected nodes`, and
      choose a one- to three-hop depth. Drag a node to move its visible,
      grabbable neighborhood rigidly without selecting those followers. Compare
      this with dragging an explicitly selected group while the option is off.
    - Toolbar layout: narrow the browser to see compact icon menus, use the
      search icon to open its dedicated row, and use the arrow to minimize and
      restore all controls without changing the graph.
    - Node label search: choose `Node label`, enter `PERSON`, and apply it to
      focus on Maya, Noah, Lina, and Omar.
    - Property search: choose `Property`, enter `risk:10`, and apply it to
      focus and select the 09:10 time window without hiding graph context.
    - Selector search: choose `Selector`, enter `node[risk >= 8]`, and apply it
      to find the high-risk nodes.
    - Neighbor tools: select `ABC123`, open `Explore`, then click neighbors,
      incoming, or outgoing.
    - Analysis: select `Case 42` and `02 Sep 2024 09:10`, open `Analyze`, then
      click shortest path. Select only `02 Sep 2024 08:14`, then click degree.
    - Visibility and export: open `Selection` to hide unselected nodes, then
      open `Export` to download the selected subgraph or positions JSON.
    """
)

render_dictionary_preview(
    "Returned investigation value",
    value or {},
    """
    This dictionary is returned after selection, search, visibility, or analysis
    interactions. It carries selected IDs, connected evidence records, matched
    search records, or graph algorithm results back to Streamlit.
    """,
    height=380,
    expanded=True,
)

event_data = value.get("data", {}) if isinstance(value, dict) else {}
returned_records = []
returned_record_source = None
if isinstance(event_data, dict):
    for candidate in ("selected_elements", "matched_elements"):
        candidate_records = event_data.get(candidate)
        if isinstance(candidate_records, list) and candidate_records:
            returned_records = candidate_records
            returned_record_source = candidate
            break

st.markdown("## Returned Records As A Dataframe")
st.markdown(
    """
    Selection and search events include complete element records, not only IDs.
    `records_to_dataframe(...)` flattens each record's nested `data` dictionary
    into columns that can be filtered, joined, summarized, or exported with the
    rest of a pandas workflow.
    """
)
if returned_records:
    st.caption(f"Showing `{returned_record_source}` from the latest event.")
    st.dataframe(records_to_dataframe(returned_records), hide_index=True)
else:
    st.info(
        "Select graph elements or apply a search to populate this dataframe "
        "from the returned event."
    )
st.code(
    """event_data = value.get("data", {})
returned_records = (
    event_data.get("selected_elements")
    or event_data.get("matched_elements")
    or []
)
returned_table = records_to_dataframe(returned_records)
st.dataframe(returned_table, hide_index=True)""",
    language="python",
)

st.markdown("## What The JavaScript Is Doing")
st.markdown(
    """
    The search panel asks Cytoscape for matching elements, selects/highlights
    all matches, and fits the viewport around them without hiding the rest of
    the graph. In box selection mode, the canvas mode control switches the
    same blank-canvas drag between Cytoscape panning and the custom selection
    rectangle. Selection changes build a JSON payload with selected and
    connected elements. Analysis buttons call Cytoscape graph algorithms,
    highlight the result, and send the result back to Streamlit as an
    `analysis` action. Connected dragging calculates a visible, undirected BFS
    neighborhood when a gesture starts, then moves those followers by the
    anchor's exact position delta. It does not select them or edit their data.
    """
)


render_source_expander(__file__)
