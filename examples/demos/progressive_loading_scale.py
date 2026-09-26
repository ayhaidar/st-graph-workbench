"""Render progressively larger browser graphs and explain the measured limits."""

from copy import deepcopy

import streamlit as st

from demos.demo_helpers import (
    render_capability_summary,
    render_dictionary_preview,
    render_source_expander,
)
from page_overview import render_page_overview
from progressive_loading_data import graph_through
from st_graph_workbench import (
    EdgeStyle,
    NodeStyle,
    graph_workbench,
    records_to_dataframe,
)


SIZES = (100, 600, 1_000, 5_000, 10_000)
ACTIVE_SIZE_KEY = "progressive_scale_active_size"
POSITIONS_KEY = "progressive_scale_positions"
COMPONENT_KEY = "progressive-scale-graph"


@st.cache_data(max_entries=5, show_spinner=False)
def scale_elements(record_count: int) -> dict:
    """Generate one deterministic graph size for repeatable browser comparisons."""
    return graph_through(record_count)


def graph_counts(elements: dict) -> dict[str, int]:
    return {
        "source_records": len(
            [
                node
                for node in elements["nodes"]
                if node["data"].get("label") == "VEHICLE"
            ]
        ),
        "nodes": len(elements["nodes"]),
        "edges": len(elements["edges"]),
    }


def remember_positions() -> None:
    """Retain the latest browser arrangement for the active size checkpoint."""
    event = st.session_state.get(COMPONENT_KEY)
    if not isinstance(event, dict) or event.get("action") != "positions":
        return
    st.session_state[POSITIONS_KEY] = {
        "size": st.session_state[ACTIVE_SIZE_KEY],
        "positions": {
            row["id"]: row["position"] for row in event["data"].get("positions", [])
        },
    }


st.markdown("# Progressive Loading Scale Test")
st.markdown(
    """
    This activity extends the Progressive Loading lesson by testing the same
    graph shape at several sizes. It is deliberately a browser activity: the
    Python process creates and validates the dictionaries, while Cytoscape
    stores, draws, searches, and selects the records in the browser.

    **Learning target:** distinguish source-record count from rendered node and
    edge count, compare the `large` rendering profile, and identify a useful
    interaction limit for your own data instead of assuming one universal number.
    """
)

render_page_overview(
    [
        (
            "Scale activity and source data",
            "Choose a deterministic graph size and inspect representative records before rendering.",
        ),
        (
            "Browser graph",
            "Render the selected graph with stable preset positions and the large performance profile.",
        ),
        (
            "Read the counts",
            "Understand why source records, nodes, edges, and browser workload are different.",
        ),
        (
            "Load more in practice",
            "Use bounded batches when the full graph is larger than the useful working view.",
        ),
        (
            "Measure your boundary",
            "Run the repeatable browser benchmark and record the point where interactions slow down.",
        ),
    ],
    description="Use this activity after Progressive Loading to turn a fixed example into a browser-capacity experiment.",
)

render_capability_summary(
    "What this activity covers",
    [
        {
            "capability": "Deterministic scale comparison",
            "API surface": "graph_workbench, preset layout",
            "what to try": "Render each size and compare counts, pan, zoom, search, and selection.",
        },
        {
            "capability": "Browser-oriented performance profile",
            "API surface": "performance_profile='large'",
            "what to try": "Reduce label and viewport drawing work while retaining graph data.",
        },
        {
            "capability": "Bounded data delivery",
            "API surface": "progressive_loading, add_elements_command",
            "what to try": "Use Load more instead of sending every source record at startup.",
        },
    ],
    description="The graph is useful only while its records remain understandable and its interactions remain responsive.",
)

st.session_state.setdefault(ACTIVE_SIZE_KEY, 600)
st.session_state.setdefault(POSITIONS_KEY, {})
selected_size = st.selectbox(
    "Graph size",
    SIZES,
    format_func=lambda value: f"{value:,} vehicle records",
    help="This is the number of vehicle source records. Each record creates one node and one assignment edge.",
)
if st.button("Render selected graph", icon=":material/play_arrow:"):
    st.session_state[ACTIVE_SIZE_KEY] = selected_size

active_size = st.session_state[ACTIVE_SIZE_KEY]
elements = deepcopy(scale_elements(active_size))
saved_positions = st.session_state[POSITIONS_KEY]
if saved_positions.get("size") == active_size:
    for node in elements["nodes"]:
        position = saved_positions.get("positions", {}).get(node["data"]["id"])
        if position is not None:
            node["position"] = deepcopy(position)
counts = graph_counts(elements)

st.markdown("## Source records before rendering")
st.markdown(
    "Python creates the complete selected checkpoint first. The table below is "
    "only a readable sample; the graph receives all records for the selected size. "
    "Locations are shared by vehicles, so the number of nodes is records plus three "
    "location nodes, while the number of edges is one assignment per vehicle."
)
st.dataframe(
    records_to_dataframe(
        {
            "nodes": elements["nodes"][:8],
            "edges": elements["edges"][:8],
        }
    ),
    hide_index=True,
    height=260,
)

metrics = st.columns(4)
metrics[0].metric("Vehicle records", f"{counts['source_records']:,}")
metrics[1].metric("Graph nodes", f"{counts['nodes']:,}")
metrics[2].metric("Graph edges", f"{counts['edges']:,}")
metrics[3].metric("Checkpoint", f"{active_size:,}")

st.markdown("## Browser graph")
st.markdown(
    "The component keeps the source positions supplied by Python and uses the "
    "`large` profile to reduce label and viewport rendering work. Try search, "
    "selection, pan, zoom, and Fit at each checkpoint. In Selection, enable "
    "Move connected nodes: dragging a vehicle moves its small local scope, while "
    "dragging a location intentionally refuses a neighborhood above 100 followers. "
    "This demonstrates a bounded interaction rather than a partial move. The browser benchmark "
    "linked below measures readiness and graph counts; it does not claim a "
    "machine-independent maximum."
)

node_styles = [
    NodeStyle("LOCATION", "#1F6F78", "name", "place", size=40),
    NodeStyle("VEHICLE", "#2A629A", "name", "directions_car", size=22),
]
edge_styles = [
    EdgeStyle("SERVES", "#708090", "label", directed=True, opacity=0.5),
]

with st.echo():
    value = graph_workbench(
        elements,
        layout={"name": "preset", "fit": True, "padding": 55},
        node_styles=node_styles,
        edge_styles=edge_styles,
        selection_mode="multiple",
        return_selection=True,
        return_positions=True,
        search=True,
        analysis_actions=["degree", "connected_components"],
        performance_profile="large",
        connected_drag={
            "enabled": False,
            "depth": 1,
            "max_depth": 3,
            "max_nodes": 100,
        },
        key=COMPONENT_KEY,
        on_change=remember_positions,
        height=680,
    )

render_dictionary_preview(
    "Returned value from the scale graph",
    value or {},
    "This is the component event value, not the input graph dictionary. A selection "
    "contains IDs and records that Python can use for a filtered query. An analysis "
    "payload describes the displayed checkpoint. The input records and counts are "
    "shown above so the reader can compare source data with browser output.",
    height=300,
    expanded=True,
)

st.markdown("## What the counts mean")
st.dataframe(
    [
        {
            "measurement": "Vehicle records",
            "meaning": "The domain records supplied by Python for this checkpoint.",
            "example": f"{active_size:,}",
        },
        {
            "measurement": "Graph nodes",
            "meaning": "Vehicle nodes plus the three shared location nodes.",
            "example": f"{counts['nodes']:,}",
        },
        {
            "measurement": "Graph edges",
            "meaning": "One SERVES relationship per vehicle in this scenario.",
            "example": f"{counts['edges']:,}",
        },
        {
            "measurement": "Browser workload",
            "meaning": "Parsing, Cytoscape collections, styles, hit testing, search, and drawing.",
            "example": "Depends on browser, device, styles, and topology",
        },
    ],
    hide_index=True,
)

st.markdown("## Why Load more is useful")
st.markdown(
    """
    **Load more** is an in-graph component control for adding the next bounded
    page of records. It is useful when a source has more records than a person
    can reasonably inspect at once, or when each extra page costs network,
    serialization, layout, or browser memory.

    The control does not connect to a database by itself. You include it by
    passing a `progressive_loading` dictionary to `graph_workbench`, then handle
    the returned `load_more` event in Python. Your callback applies access rules,
    filters and pagination, validates the returned records, and sends an
    incremental `add_elements_command`. Existing nodes, positions, zoom, and
    pan remain in the same browser instance.
    """
)
st.code(
    """progress = {
    "page_size": 100,
    "loaded_count": len(loaded_records),
    "total_count": total_records,
    "has_more": next_cursor is not None,
    "cursor": next_cursor,
}

value = graph_workbench(
    elements,
    progressive_loading=progress,
    graph_commands=[next_page_command],
    elements_sync="initial",
    key="records-graph",
    on_change=handle_graph_event,
)""",
    language="python",
)
st.markdown(
    "In this pattern, the browser asks for a page and Python decides what that "
    "page means. Use a stable command ID, advance the cursor only after a valid "
    "batch is applied, and acknowledge failures so the user can retry. For a "
    "large source, progressive pages are usually more useful than trying to show "
    "the entire dataset in one canvas."
)

st.markdown("## Measure your useful boundary")
st.markdown(
    "Run the browser benchmark from the repository root. It opens this activity, "
    "renders each requested size, checks node and edge counts, and reports the "
    "time until the graph is ready. Chromium may also report JavaScript heap use. "
    "Treat the first noticeable delay in search, selection, pan, or zoom as your "
    "application's practical boundary, then switch to Load more, server-side "
    "filters, or node expansion."
)
st.code(
    "uv run python scripts/benchmark_browser_graph.py --base-url http://localhost:8502",
    language="powershell",
)
st.markdown(
    "The benchmark is intentionally manual and machine-specific. It is a capacity "
    "probe, not a promise that every browser can render the largest option."
)

st.markdown("## Conclusion")
st.markdown(
    "A graph library can support thousands of records in the browser, but the "
    "right limit is determined by topology, styling, device, and interaction "
    "needs. Start with a useful subset, measure the real workflow, and let Load "
    "more or expansion reveal the next records when they are needed."
)

render_source_expander(__file__)
