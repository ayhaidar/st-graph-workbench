import streamlit as st

from demos.demo_helpers import (
    capability_rows,
    render_capability_summary,
    render_dictionary_preview,
    render_elements_dataframe,
    render_source_expander,
)
from page_overview import render_page_overview
from st_graph_workbench import EdgeStyle, NodeStyle, StyleRule, graph_workbench
from st_graph_workbench import upsert_elements

st.markdown("# Graph Workbench Showcase")
st.markdown(
    """
    This page combines the main `st-graph-workbench` capabilities in one graph:
    selection, search, neighbor exploration, analysis, expansion badges,
    CRUD/data-loading events, export, positions, compound nodes, and performance
    profile options.
    """
)

render_page_overview(
    [
        (
            "Capability coverage",
            "The major graph workbench features demonstrated together on one page.",
        ),
        (
            "Showcase graph setup",
            "The staged knowledge-graph records, expansion metadata, styles, and performance profile.",
        ),
        (
            "Data before rendering",
            "The currently visible graph records, including any Python-loaded related records.",
        ),
        (
            "Interactive graph",
            "Selection, search, right-click expansion, node actions, CRUD intents, analysis, exports, and positions.",
        ),
        (
            "Try these checks",
            "Concrete interactions to verify expansion counts, terminal records, search, analysis, and export.",
        ),
        (
            "Returned dictionaries",
            "The latest selection, expansion, CRUD, analysis, visibility, export, or position payload.",
        ),
        (
            "What JavaScript is doing",
            "How the browser modules connect Cytoscape interactions back to Streamlit.",
        ),
    ],
    description="This showcase overview gives readers the whole feature route before the graph.",
)

render_capability_summary(
    "What this showcase enables",
    [
        row
        for row in capability_rows()
        if row["capability"]
        in {
            "Render Cytoscape graphs",
            "Search",
            "Selection modes",
            "Node actions and visibility",
            "Analysis tools",
            "CRUD intents",
            "Performance profiles",
        }
    ],
    description="The main APIs and interactions demonstrated by the showcase graph.",
)

STATE_KEY = "showcase_extra_elements"
EXPANDED_KEY = "showcase_expanded_nodes"
NOTICE_KEY = "showcase_notice"
COMPONENT_KEY = "graph_workbench_showcase"

ROOT_NODE_IDS = {"case", "vehicle", "maya"}
CHILDREN_BY_NODE = {
    "vehicle": {"checkpoint", "time_window"},
}

BASE_NODES = [
    {
        "data": {
            "id": "case",
            "label": "CASE",
            "name": "Case 118",
            "risk": 7,
        },
        "position": {"x": 80, "y": 230},
    },
    {
        "data": {
            "id": "vehicle",
            "label": "MAIN_VEHICLE",
            "name": "ABC123",
            "risk": 8,
        },
        "position": {"x": 300, "y": 210},
    },
    {
        "data": {
            "id": "maya",
            "label": "PERSON",
            "name": "Maya Reed",
            "risk": 5,
        },
        "position": {"x": 300, "y": 360},
    },
    {
        "data": {
            "id": "checkpoint",
            "label": "LOCATION",
            "name": "Harbor Camera 4",
            "risk": 6,
        },
        "position": {"x": 520, "y": 120},
    },
    {
        "data": {
            "id": "time_window",
            "label": "TIME",
            "name": "02 Sep 2024 08:14",
            "risk": 9,
        },
        "position": {"x": 520, "y": 290},
    },
    {
        "data": {
            "id": "tower",
            "label": "LOCATION",
            "name": "Cell tower T-18",
            "risk": 6,
        },
        "position": {"x": 740, "y": 210},
    },
    {
        "data": {
            "id": "device",
            "label": "DEVICE",
            "name": "Phone 0412",
            "risk": 8,
        },
        "position": {"x": 740, "y": 370},
    },
    {
        "data": {
            "id": "depot",
            "label": "LOCATION",
            "name": "Service depot 12",
            "risk": 7,
        },
        "position": {"x": 740, "y": 50},
    },
    {
        "data": {
            "id": "trip",
            "label": "MOVEMENT",
            "name": "Trip segment TS-449",
            "risk": 6,
        },
        "position": {"x": 960, "y": 90},
    },
]

BASE_EDGES = [
    {
        "data": {
            "id": "case-vehicle",
            "label": "INVESTIGATES",
            "source": "case",
            "target": "vehicle",
        }
    },
    {
        "data": {
            "id": "vehicle-maya",
            "label": "REGISTERED_TO",
            "source": "vehicle",
            "target": "maya",
        }
    },
    {
        "data": {
            "id": "vehicle-checkpoint",
            "label": "SEEN_AT",
            "source": "vehicle",
            "target": "checkpoint",
        }
    },
    {
        "data": {
            "id": "vehicle-time",
            "label": "OBSERVED_DURING",
            "source": "vehicle",
            "target": "time_window",
        }
    },
    {
        "data": {
            "id": "maya-device",
            "label": "USES",
            "source": "maya",
            "target": "device",
        }
    },
    {
        "data": {
            "id": "device-tower",
            "label": "SEEN_NEAR",
            "source": "device",
            "target": "tower",
        }
    },
    {
        "data": {
            "id": "checkpoint-depot",
            "label": "NEAR",
            "source": "checkpoint",
            "target": "depot",
        }
    },
    {
        "data": {
            "id": "depot-trip",
            "label": "PART_OF",
            "source": "depot",
            "target": "trip",
        }
    },
]

RELATED_DATA = {
    "vehicle": {
        "nodes": [
            {
                "data": {
                    "id": "document",
                    "label": "DOCUMENT",
                    "name": "Sighting report SR-118",
                    "observed_at": "2024-09-02 08:14",
                    "risk": 8,
                },
                "position": {"x": 300, "y": 520},
            }
        ],
        "edges": [
            {
                "data": {
                    "id": "vehicle-document",
                    "label": "RECORDED_IN",
                    "source": "vehicle",
                    "target": "document",
                }
            }
        ],
    },
    "maya": {
        "nodes": [
            {
                "data": {
                    "id": "person_device",
                    "label": "DEVICE",
                    "name": "Phone 0412",
                    "risk": 8,
                },
                "position": {"x": 520, "y": 510},
            }
        ],
        "edges": [
            {
                "data": {
                    "id": "maya-device-related",
                    "label": "USES",
                    "source": "maya",
                    "target": "person_device",
                }
            }
        ],
    },
}


def ensure_state():
    if STATE_KEY not in st.session_state:
        st.session_state[STATE_KEY] = {"nodes": [], "edges": []}
    if EXPANDED_KEY not in st.session_state:
        st.session_state[EXPANDED_KEY] = set()
    if NOTICE_KEY not in st.session_state:
        st.session_state[NOTICE_KEY] = ""


def descendants(node_id):
    found = set()
    pending = list(CHILDREN_BY_NODE.get(node_id, set()))
    while pending:
        child = pending.pop()
        if child in found:
            continue
        found.add(child)
        pending.extend(CHILDREN_BY_NODE.get(child, set()))
    return found


def visible_node_ids():
    visible = set(ROOT_NODE_IDS)
    changed = True
    while changed:
        changed = False
        for node_id in list(visible):
            if node_id not in st.session_state[EXPANDED_KEY]:
                continue
            new_ids = CHILDREN_BY_NODE.get(node_id, set()) - visible
            if new_ids:
                visible |= new_ids
                changed = True
    return visible


def expansion_for(node_id, visible):
    children = CHILDREN_BY_NODE.get(node_id, set())
    if not children:
        return None

    is_expanded = node_id in st.session_state[EXPANDED_KEY]
    hidden_direct = children - visible
    hidden_total = descendants(node_id) - visible

    if is_expanded:
        visible_descendants = descendants(node_id) & visible
        return {
            "state": "expanded",
            "collapse_count": len(visible_descendants),
            "total_count": len(hidden_total),
            "depth": 1 if hidden_total else 0,
        }

    return {
        "state": "collapsed",
        "next_count": len(hidden_direct),
        "total_count": len(hidden_total),
        "depth": 1,
    }


def visible_base_elements():
    visible = visible_node_ids()
    nodes = []
    for node in BASE_NODES:
        node_id = node["data"]["id"]
        if node_id not in visible:
            continue
        data = dict(node["data"])
        expansion = expansion_for(node_id, visible)
        if expansion:
            data["expansion"] = expansion
        nodes.append({**node, "data": data})

    edges = [
        edge
        for edge in BASE_EDGES
        if edge["data"]["source"] in visible and edge["data"]["target"] in visible
    ]
    return {"nodes": nodes, "edges": edges}


def current_elements():
    return upsert_elements(
        visible_base_elements(),
        nodes=st.session_state[STATE_KEY]["nodes"],
        edges=st.session_state[STATE_KEY]["edges"],
    )


def load_related(node_id):
    related = RELATED_DATA.get(node_id)
    if not related:
        st.session_state[NOTICE_KEY] = f"No extra showcase data for `{node_id}`."
        return

    extra = st.session_state[STATE_KEY]
    nodes_by_id = {node["data"]["id"]: node for node in extra["nodes"]}
    edges_by_id = {edge["data"]["id"]: edge for edge in extra["edges"]}
    nodes_by_id.update({node["data"]["id"]: node for node in related["nodes"]})
    edges_by_id.update({edge["data"]["id"]: edge for edge in related["edges"]})
    st.session_state[STATE_KEY] = {
        "nodes": list(nodes_by_id.values()),
        "edges": list(edges_by_id.values()),
    }
    st.session_state[NOTICE_KEY] = (
        f"Loaded {len(related['nodes'])} related node(s) for `{node_id}`."
    )


def handle_graph_event():
    event = st.session_state.get(COMPONENT_KEY)
    if not event:
        return

    action = event.get("action")
    data = event.get("data", {})

    if action == "expand":
        for node_id in data.get("node_ids", []):
            if node_id in st.session_state[EXPANDED_KEY]:
                st.session_state[EXPANDED_KEY].remove(node_id)
            elif node_id in CHILDREN_BY_NODE:
                st.session_state[EXPANDED_KEY].add(node_id)
        st.session_state[NOTICE_KEY] = "Expansion state updated in Python."
        return

    if action == "crud" and data.get("operation") == "request_node_data":
        node_ids = data.get("selected_node_ids", [])
        if node_ids:
            load_related(node_ids[0])


ensure_state()

left, right = st.columns([1, 2])
with left:
    performance_profile = st.selectbox(
        "Performance profile",
        ["default", "large", "dense"],
        help="Large and dense profiles reduce browser rendering work.",
    )
    if st.button("Reset showcase graph"):
        st.session_state[STATE_KEY] = {"nodes": [], "edges": []}
        st.session_state[EXPANDED_KEY] = set()
        st.session_state[NOTICE_KEY] = ""
        st.rerun()

with right:
    if st.session_state[NOTICE_KEY]:
        st.info(st.session_state[NOTICE_KEY])

node_styles = [
    NodeStyle("CASE", "#3D405B", "name", "folder", size=42),
    NodeStyle("MAIN_VEHICLE", "#2A629A", "name", "directions_car", size=36),
    NodeStyle("PERSON", "#FF7F3E", "name", "person", size=32),
    NodeStyle("LOCATION", "#2D936C", "name", "place", size=34),
    NodeStyle("TIME", "#8A5A44", "name", "schedule", size=34),
    NodeStyle("MOVEMENT", "#5F5AA2", "name", "local_shipping", size=34),
    NodeStyle("DOCUMENT", "#876445", "name", "description", size=34),
    NodeStyle("DEVICE", "#4F6F52", "name", "smartphone", size=34),
    StyleRule(
        "node[risk >= 8]",
        {"border-width": 4, "border-color": "#D72638"},
    ),
]

edge_styles = [
    EdgeStyle("INVESTIGATES", "#3D405B", "label", directed=True, width=3),
    EdgeStyle("REGISTERED_TO", "#2A629A", "label", directed=True),
    EdgeStyle("SEEN_AT", "#2D936C", "label", directed=True, width=3),
    EdgeStyle(
        "OBSERVED_DURING", "#D72638", "label", directed=True, line_style="dashed"
    ),
    EdgeStyle("SEEN_NEAR", "#C44536", "label", directed=True, width=3),
    EdgeStyle("NEAR", "#8A5A44", "label", directed=True),
    EdgeStyle("PART_OF", "#5F5AA2", "label", directed=True),
    EdgeStyle("RECORDED_IN", "#876445", "label", directed=True),
    EdgeStyle("USES", "#4F6F52", "label", directed=True),
]

elements = current_elements()

st.markdown("## Data before rendering")
st.markdown(
    """
    The showcase graph is Python-owned. Expansion and data-loading actions
    update these visible records, then Streamlit sends the resulting node and
    edge dictionaries back into the same browser component.
    """
)
render_elements_dataframe(elements, "Current showcase graph records")

value = graph_workbench(
    elements,
    layout={"name": "preset", "fit": True, "padding": 50},
    node_styles=node_styles,
    edge_styles=edge_styles,
    node_actions=[
        "expand",
        "show_neighbors",
        "show_incoming",
        "show_outgoing",
        "hide_unselected",
        "restore_hidden",
    ],
    crud_actions=["read_selected", "request_node_data"],
    selection_mode="multiple",
    return_selection=True,
    search=True,
    analysis_actions=["shortest_path", "bfs", "dfs", "connected_components", "degree"],
    return_positions=True,
    performance_profile=performance_profile,
    key=COMPONENT_KEY,
    on_change=handle_graph_event,
    height=620,
)

st.markdown("## Try These Checks")
st.markdown(
    """
    - Select `ABC123`; the info panel shows expansion totals, and
      the node badge shows the next expansion count.
    - Right-click `ABC123` and choose expand/collapse, or use the
      toolbox button after selecting the node.
    - `Harbor Camera 4` and `02 Sep 2024 08:14` are terminal records in this
      showcase, so they should not show expansion badges after ABC123 is
      expanded.
    - Search for `time`, use property search with `risk:8`, or selector
      search with `node[risk >= 8]`.
    - Select two visible nodes, open `Analyze`, and run shortest path.
    - Select one node, open `Data`, and click `Load Related Data` to merge fake
      Python data into the graph.
    - Open `Export` to download visible JSON, selected JSON, images, or
      positions.
    """
)

render_dictionary_preview(
    "Returned showcase value",
    value or {},
    """
    This dictionary is the latest event from the all-features showcase graph.
    Depending on the interaction it may describe selection, expansion, CRUD,
    analysis, visibility, export context, or returned node positions.
    """,
    height=380,
    expanded=True,
)

st.markdown("## What JavaScript Is Doing")
st.markdown(
    """
    Cytoscape renders and interacts with the graph in the browser. The
    component modules wire DOM controls to Cytoscape methods for search,
    selection, analysis, exports, view controls, expansion badges, and CRUD
    event payloads. Streamlit receives those payloads, reruns Python, and sends
    updated `elements` back into the same browser component instance.
    """
)


render_source_expander(__file__)
