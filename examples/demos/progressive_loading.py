from collections import Counter
from copy import deepcopy
import inspect
from uuid import uuid4

import streamlit as st

from demos.demo_helpers import (
    render_capability_summary,
    render_dictionary_preview,
    render_elements_dataframe,
    render_source_expander,
)
from page_overview import render_page_overview
from progressive_loading_data import (
    INITIAL_RECORDS,
    PAGE_SIZE,
    TOTAL_RECORDS,
    bfs_result_rows,
    graph_through,
    record_batch,
)
from st_graph_workbench import (
    EdgeStyle,
    NodeStyle,
    ProgressiveLoadConfig,
    add_elements_command,
    apply_graph_command,
    graph_workbench,
    records_to_dataframe,
    set_elements_command,
    viewport_command,
)

st.markdown("# Progressive Loading")
st.markdown(
    """
    Progressive loading means showing a useful first portion of a dataset, then
    adding more when requested. This example starts with 60 vehicles and three
    locations, not all 600 vehicles at once. The same pattern works for any
    connected dataset: the graph requests a page, and Python supplies the records.

    **Learning targets:** follow a Load more request from browser to Python;
    explore one node with breadth-first search (BFS); find a shortest path
    between two nodes; and see how newly loaded connections change the results.
    """
)

render_page_overview(
    [
        (
            "Source data and scenario",
            "Inspect the loaded records and optionally introduce cross-location sightings.",
        ),
        (
            "How Load more works",
            "The component button, Python callback, cursor, and incremental command.",
        ),
        (
            "Cursor and batch state",
            "The progress configuration sent to the browser and returned on request.",
        ),
        (
            "Interactive graph",
            "Update the layout, then use search, selection, analysis, and Load more.",
        ),
        (
            "BFS experiments and results",
            "Compare roots and batches, then read the visit order and hop counts.",
        ),
        (
            "Shortest path and clearing highlights",
            "Connect two endpoints, inspect the returned relationships, and reset the canvas selection.",
        ),
        (
            "Returned dictionaries and next steps",
            "Interpret scope correctly and identify useful application extensions.",
        ),
    ],
    description="Use this contents list to follow the large-graph workflow from source records to browser updates.",
)

render_capability_summary(
    "What this demo covers",
    [
        {
            "capability": "Cursor-aware progressive loading",
            "API surface": "progressive_loading: ProgressiveLoadConfig",
            "what to try": "Request the next bounded batch from the graph canvas.",
        },
        {
            "capability": "Incremental browser updates",
            "API surface": "add_elements_command, elements_sync='initial'",
            "what to try": "Add unseen records while retaining the live Cytoscape instance.",
        },
        {
            "capability": "Large graph rendering",
            "API surface": "performance_profile='large'",
            "what to try": "Grow the graph to hundreds of nodes, then test selection and analysis.",
        },
    ],
    description="These APIs work together to keep large graph exploration responsive.",
)

STATE_KEY = "progressive_demo_elements"
LOADED_KEY = "progressive_demo_loaded"
COMMANDS_KEY = "progressive_demo_commands"
COMMAND_SEQUENCE_KEY = "progressive_demo_command_sequence"
COMMAND_NAMESPACE_KEY = "progressive_demo_command_namespace"
ACKNOWLEDGED_KEY = "progressive_demo_acknowledged_request"
ERROR_KEY = "progressive_demo_error"
LAST_EVENT_KEY = "progressive_demo_last_event"
NOTICE_KEY = "progressive_demo_notice"
VERSION_KEY = "progressive_demo_version"
STATE_VERSION = 3
COMPONENT_KEY = "progressive-loading-graph"
CROSS_LOCATIONS_KEY = "progressive_demo_cross_locations"
CROSS_LOCATIONS_WIDGET_KEY = "progressive_demo_cross_locations_widget"
BFS_KEY = "progressive_demo_bfs"
PATH_KEY = "progressive_demo_shortest_path"
LAYOUT_WIDGET_KEY = "progressive_demo_layout"

LAYOUT_OPTIONS = {
    "Source positions": "preset",
    "fCoSE physics": "fcose",
    "Cola physics": "cola",
    "CoSE physics": "cose",
    "Breadth-first": "breadthfirst",
    "Dagre hierarchy": "dagre",
    "Circle": "circle",
    "Concentric": "concentric",
    "Grid": "grid",
    "Random": "random",
}


def next_command_id(prefix: str) -> str:
    st.session_state[COMMAND_SEQUENCE_KEY] += 1
    return (
        f"{st.session_state[COMMAND_NAMESPACE_KEY]}-{prefix}-"
        f"{st.session_state[COMMAND_SEQUENCE_KEY]}"
    )


def selected_layout() -> dict:
    """Return a bounded layout configuration for the current graph."""
    name = LAYOUT_OPTIONS[st.session_state[LAYOUT_WIDGET_KEY]]
    layout: dict = {"name": name, "fit": True, "padding": 55, "animate": False}
    if name == "preset":
        # Restore the deterministic coordinates owned by the Python checkpoint.
        layout["positions"] = {
            str(node["data"]["id"]): deepcopy(node["position"])
            for node in st.session_state[STATE_KEY]["nodes"]
            if "position" in node
        }
    elif name in {"cose", "fcose", "cola"}:
        # Start from the visible arrangement instead of scattering nodes first.
        layout["randomize"] = False
    if name == "cola":
        # Keep a large loaded graph from running an unbounded simulation.
        layout["maxSimulationTime"] = 2500
    elif name == "dagre":
        layout["rankDir"] = "LR"
    elif name == "breadthfirst":
        layout["directed"] = True
    return layout


def apply_selected_layout() -> None:
    """Queue a browser-only layout command without replacing graph records."""
    layout = selected_layout()
    st.session_state[COMMANDS_KEY] = [
        viewport_command(
            next_command_id(f"layout-{layout['name']}"),
            "run_layout",
            layout=layout,
        )
    ]
    st.session_state[NOTICE_KEY] = (
        f"Applied {st.session_state[LAYOUT_WIDGET_KEY]}. The records did not change."
    )


def reset_state() -> None:
    initial = graph_through(
        INITIAL_RECORDS,
        cross_locations=st.session_state.get(CROSS_LOCATIONS_KEY, False),
    )
    st.session_state[STATE_KEY] = initial
    st.session_state[LOADED_KEY] = INITIAL_RECORDS
    st.session_state[COMMANDS_KEY] = []
    # These identifiers live as long as the component, not just the current data.
    st.session_state.setdefault(COMMAND_SEQUENCE_KEY, 0)
    st.session_state.setdefault(COMMAND_NAMESPACE_KEY, uuid4().hex)
    st.session_state[ACKNOWLEDGED_KEY] = None
    st.session_state[ERROR_KEY] = ""
    st.session_state[LAST_EVENT_KEY] = None
    st.session_state[NOTICE_KEY] = ""
    st.session_state[VERSION_KEY] = STATE_VERSION
    st.session_state[BFS_KEY] = None
    st.session_state[PATH_KEY] = None


def ensure_state() -> None:
    if st.session_state.get(VERSION_KEY) != STATE_VERSION:
        reset_state()
    st.session_state.setdefault(CROSS_LOCATIONS_KEY, False)
    st.session_state.setdefault(BFS_KEY, None)
    st.session_state.setdefault(PATH_KEY, None)


def handle_graph_event() -> None:
    event = st.session_state.get(COMPONENT_KEY)
    if event and event.get("action") == "positions":
        # Save browser coordinates before a later incremental batch is applied.
        returned_positions = {
            row["id"]: row["position"] for row in event["data"].get("positions", [])
        }
        for node in st.session_state[STATE_KEY]["nodes"]:
            node_id = str(node["data"]["id"])
            if node_id in returned_positions:
                node["position"] = deepcopy(returned_positions[node_id])
    elif (
        event
        and event.get("action") == "analysis"
        and event["data"].get("analysis") == "bfs"
    ):
        # Keep the result after selection/load events, with its original data scope.
        st.session_state[BFS_KEY] = {
            "event": deepcopy(event),
            "loaded_count": st.session_state[LOADED_KEY],
            "rows": bfs_result_rows(st.session_state[STATE_KEY], event["data"]),
        }
    elif (
        event
        and event.get("action") == "analysis"
        and event["data"].get("analysis") == "shortest_path"
    ):
        # Join the returned edge IDs to source records, not a second path calculation.
        path_ids = set(event["data"]["edge_ids"])
        st.session_state[PATH_KEY] = {
            "event": deepcopy(event),
            "loaded_count": st.session_state[LOADED_KEY],
            "rows": [
                deepcopy(edge["data"])
                for edge in st.session_state[STATE_KEY]["edges"]
                if edge["data"]["id"] in path_ids
            ],
        }
    if not event or event.get("action") != "load_more":
        return
    request = event.get("data", {})
    event_id = request.get("request_id", event.get("timestamp"))
    if event_id == st.session_state.get(LAST_EVENT_KEY):
        return
    st.session_state[LAST_EVENT_KEY] = event_id
    st.session_state[COMMANDS_KEY] = []
    st.session_state[ERROR_KEY] = ""
    try:
        load_batch(request)
    except (OSError, ValueError, KeyError) as error:
        st.session_state[ERROR_KEY] = (
            f"Batch was not loaded: {error}. Try Load more again."
        )
    finally:
        st.session_state[ACKNOWLEDGED_KEY] = request.get("request_id")


def load_batch(request: dict) -> None:
    start = st.session_state[LOADED_KEY]
    if request.get("cursor") != start:
        st.session_state[NOTICE_KEY] = "Ignored an outdated page request."
        return
    requested_size = int(request.get("page_size", PAGE_SIZE))
    stop = min(start + requested_size, TOTAL_RECORDS)
    if stop <= start:
        st.session_state[NOTICE_KEY] = "All mobility records are already loaded."
        return

    # This deterministic generator stands in for a database/API page fetch.
    batch = record_batch(
        start, stop, cross_locations=st.session_state.get(CROSS_LOCATIONS_KEY, False)
    )
    command = add_elements_command(
        next_command_id("load-page"),
        nodes=batch["nodes"],
        edges=batch["edges"],
    )
    st.session_state[STATE_KEY] = apply_graph_command(
        st.session_state[STATE_KEY], command
    )
    st.session_state[COMMANDS_KEY] = [command]
    st.session_state[LOADED_KEY] = stop
    st.session_state[NOTICE_KEY] = (
        f"Loaded records {start + 1:,}-{stop:,}. The graph now contains "
        f"{len(st.session_state[STATE_KEY]['nodes']):,} nodes and "
        f"{len(st.session_state[STATE_KEY]['edges']):,} edges."
    )


def reset_graph() -> None:
    command = set_elements_command(
        next_command_id("reset"),
        graph_through(
            INITIAL_RECORDS,
            cross_locations=st.session_state.get(CROSS_LOCATIONS_KEY, False),
        ),
    )
    reset_state()
    st.session_state[COMMANDS_KEY] = [command]


def change_scenario() -> None:
    st.session_state[CROSS_LOCATIONS_KEY] = st.session_state[CROSS_LOCATIONS_WIDGET_KEY]
    reset_graph()


ensure_state()
st.session_state[CROSS_LOCATIONS_WIDGET_KEY] = st.session_state[CROSS_LOCATIONS_KEY]
st.checkbox(
    "Include cross-location sightings",
    key=CROSS_LOCATIONS_WIDGET_KEY,
    on_change=change_scenario,
    help="Changing the scenario restarts at 60 vehicles and clears saved analysis results.",
)
st.button("Reset progressive graph", on_click=reset_graph)

loaded_count = st.session_state[LOADED_KEY]
remaining_count = TOTAL_RECORDS - loaded_count
progressive_config: ProgressiveLoadConfig = {
    "page_size": PAGE_SIZE,
    "loaded_count": loaded_count,
    "total_count": TOTAL_RECORDS,
    "has_more": remaining_count > 0,
    "cursor": loaded_count,
    "acknowledged_request_id": st.session_state[ACKNOWLEDGED_KEY],
}

st.markdown("## Data before rendering")
st.markdown(
    """
    These are the Python records currently available to the
    component. The three location hubs are loaded once; each request adds a new
    page of vehicle records and relationship records.
    """
)
render_elements_dataframe(st.session_state[STATE_KEY], "Loaded mobility records")
st.caption(
    "SERVES is a vehicle's assigned location. Optional orange SEEN_AT edges are "
    "additional sightings at another location. Times are descriptive attributes; "
    "BFS does not apply a time filter or infer travel order."
)
with st.expander("Upcoming connections in the optional scenario"):
    st.markdown(
        "These source records are disclosed for the exercise; they are not in the "
        "graph until their vehicle's batch is loaded. Without the checkbox, the "
        "three location groups stay separate."
    )
    st.dataframe(
        [
            {
                "loaded_vehicles": 120,
                "vehicle": "vehicle-0061",
                "assigned_to": "North interchange",
                "also_seen_at": "Central depot",
                "time": "08:15",
            },
            {
                "loaded_vehicles": 180,
                "vehicle": "vehicle-0122",
                "assigned_to": "Central depot",
                "also_seen_at": "South terminal",
                "time": "09:30",
            },
        ],
        hide_index=True,
    )

metrics = st.columns(4)
metrics[0].metric("Loaded records", f"{loaded_count:,}")
metrics[1].metric("Remaining records", f"{remaining_count:,}")
metrics[2].metric("Graph nodes", f"{len(st.session_state[STATE_KEY]['nodes']):,}")
metrics[3].metric("Graph edges", f"{len(st.session_state[STATE_KEY]['edges']):,}")

st.markdown("## How Load more works")
st.markdown("""
**Yes, Load more is a built-in component control.** Passing a
`progressive_loading` configuration to `graph_workbench()` makes it appear
inside the graph. It is not a separate Streamlit button placed over the canvas.
It requests data; it does not know your database, download records by itself,
or automatically run BFS.

1. **Start small.** Python supplies 60 vehicles, 3 location nodes, and 60
   assignment edges. `60 / 600` counts vehicles, not all graph elements.
2. **Request a page.** Clicking Load more sends a `load_more` event to Python.
   Its `cursor` is a bookmark for where to continue; here `60` means start at
   the next vehicle, number 61. Real APIs may use an opaque token instead.
3. **Fetch and validate.** `handle_graph_event()` calls `load_batch()`. This demo
   generates synthetic data locally; a production callback would query a file,
   API, or database. `page_size=60` limits one request to 60 vehicles.
4. **Append, do not rebuild.** `add_elements_command()` describes the new nodes
   and edges. `apply_graph_command()` updates Python's checkpoint; the same
   command is passed to the existing browser graph. Existing positions, pan,
   and zoom stay unchanged. `elements_sync="initial"` avoids repeatedly sending
   the entire checkpoint on ordinary reruns.
5. **Acknowledge and continue.** Python returns the request ID in
   `acknowledged_request_id`, updates the cursor/counts, and enables the next
   request. At 600 vehicles, `has_more=False` disables Load more. A handled
   failure keeps the last valid graph and permits an explicit retry.

Each click adds vehicles **and their relationships**. With cross-location
sightings enabled, some pages add an extra edge as well. More loaded data can
therefore change connectivity, not just increase the number of dots.
""")
with st.expander("Python callback and batch code (used by this page)"):
    st.markdown(
        "The callback consumes the browser event. The loader checks the cursor, "
        "prepares a validated command, and advances the checkpoint only after success."
    )
    st.code(inspect.getsource(handle_graph_event), language="python")
    st.code(inspect.getsource(load_batch), language="python")
    st.markdown(
        "This local generator is the part to replace with your own data provider."
    )
    st.code(inspect.getsource(record_batch), language="python")

render_dictionary_preview(
    "Cursor and batch configuration",
    progressive_config,
    """
    `cursor` identifies the next data position, `page_size` bounds the request,
    and the count fields drive the progress shown inside the graph. The browser
    returns these values unchanged in a `load_more` event so the application can
    query a database, API, file, or graph service.
    """,
    height=250,
    expanded=True,
)

with st.container():
    if st.session_state[ERROR_KEY]:
        st.error(st.session_state[ERROR_KEY])
    elif st.session_state[NOTICE_KEY]:
        st.info(st.session_state[NOTICE_KEY])

node_styles = [
    NodeStyle("LOCATION", "#1F6F78", "name", "place", size=40),
    NodeStyle("VEHICLE", "#2A629A", "name", "directions_car", size=22),
]
edge_styles = [
    EdgeStyle("SERVES", "#708090", "label", directed=True, opacity=0.5),
    EdgeStyle("SEEN_AT", "#D97706", "label", directed=True, width=3),
]

st.markdown("## Interactive graph")
st.markdown(
    "Choose a placement and click **Apply layout** to rearrange the records already "
    "loaded in the browser. Physics layouts respond to graph connections, while "
    "Source positions restores the deterministic coordinates supplied by Python. "
    "This is an explicit, bounded layout run: physics stops after settling rather "
    "than continually moving the graph. Applying a layout changes positions only; "
    "it does not add records or replace the Cytoscape instance. "
    "Choose **One node** for BFS or Degree; choose **Two nodes** for Shortest Path. "
    "Then select the node(s) on the canvas and open **Analyze** "
    "(hover its icons for their names). In two-node mode, clicks toggle membership "
    "in the selection: select exactly two nodes, not an edge. Search highlights "
    "matches but does not select them: click the node after searching. "
    "**Selection > Clear Selection** clears selected records and analysis highlights. "
    "The details panel's **X** does the same; **Clear Search** separately clears search matches. "
    "Open **Selection > Move connected nodes** to drag a location and its visible "
    "one-hop vehicle group rigidly. Returned coordinates are copied into the "
    "Python checkpoint, so loading another batch preserves manual placement."
)
with st.echo():
    st.selectbox(
        "Layout to apply",
        list(LAYOUT_OPTIONS),
        key=LAYOUT_WIDGET_KEY,
        help="Physics layouts can take longer as the loaded graph grows.",
    )
    st.button(
        "Apply layout",
        icon=":material/account_tree:",
        on_click=apply_selected_layout,
        help="Rearrange the currently loaded browser graph without changing its records.",
    )
    analysis_selection = st.segmented_control(
        "Selection for analysis",
        ["One node", "Two nodes"],
        default="One node",
        required=True,
        key="progressive_demo_analysis_selection",
    )
    value = graph_workbench(
        st.session_state[STATE_KEY],
        layout={"name": "preset", "fit": True, "padding": 55},
        node_styles=node_styles,
        edge_styles=edge_styles,
        # BFS needs one selected node; shortest path needs exactly two.
        selection_mode="multiple" if analysis_selection == "Two nodes" else "single",
        return_selection=True,
        return_positions=True,
        search=True,
        analysis_actions=["degree", "bfs", "shortest_path", "connected_components"],
        graph_commands=st.session_state[COMMANDS_KEY],  # Only the latest patch.
        elements_sync="initial",
        progressive_loading=progressive_config,  # Adds the in-graph Load more control.
        # A 600-record location group remains below this automatic follower cap.
        connected_drag={
            "enabled": False,
            "depth": 1,
            "max_depth": 3,
            "max_nodes": 250,
        },
        performance_profile="large",
        key=COMPONENT_KEY,  # Keep this stable across loads and selections.
        on_change=handle_graph_event,
        height=640,
    )

with st.expander("How the layout update is sent to the graph"):
    st.markdown(
        "The callback builds a uniquely identified `run_layout` command. The live "
        "component applies it once, preserving the graph instance and source records."
    )
    st.code(inspect.getsource(apply_selected_layout), language="python")
    st.code(inspect.getsource(selected_layout), language="python")

st.markdown("## BFS experiments")
st.markdown(
    """
    **BFS means breadth-first search.** It starts at the selected node (zero
    hops), visits its immediate neighbors (one hop), then their unseen neighbors
    (two hops), and continues until no reachable records remain. Here it treats
    edges as **undirected**: it can follow a connection in either direction,
    regardless of its arrow. A hop counts relationships, not minutes or distance.

    **Experiment 1: change the starting node.** Reset to 60 vehicles. Search for
    `location-north`, click the location, and run BFS: expect **21 reached nodes**
    (the location and its 20 vehicles). Start instead at `vehicle-0001`: the
    same 21 records are reachable, but the hub is now one hop away and the other
    19 vehicles are two hops away. `vehicle-0002` explores the Central group
    instead. The root changes the visit order and hop distances.

    **Experiment 2: discover a connection that was not loaded yet.** Enable
    **Include cross-location sightings** above; this resets the exercise to 60.
    Run BFS from `location-north` after each step:

    - **60 vehicles:** 21 nodes reached; the other two groups are disconnected
      in the displayed graph. Connected components reports **3** groups.
    - **Load once, 120 vehicles:** `vehicle-0061` links North to Central.
      BFS now reaches **82 nodes**; there are **2** connected groups.
    - **Load again, 180 vehicles:** `vehicle-0122` links Central to South.
      BFS reaches **183 nodes**, up to **5 hops** from North; all three groups
      form **1** connected component. Run Degree on a linking vehicle to see
      its two incident relationships.

    Run BFS again after loading: earlier results are snapshots, not continuously
    recalculated queries. Without the optional sightings, North reaches only
    21, 41, then 61 nodes at these checkpoints; there remain three groups.

    **Keep exploring.** Pan or zoom before loading to check viewport preservation;
    use Fit when you want to frame the new nodes. Search `R-08` to find a route,
    or `vehicle-0600` before and after loading all pages. Search and analysis
    cannot see vehicles that have not been loaded. The `large` profile reduces
    drawing overhead; it does not fetch records or remove the need for limits.
    """
)

st.markdown("## BFS results as records")
st.markdown(
    "This table joins the browser's real BFS result back to Python records. "
    "Use it to inspect the reachable subset, group it by route, or pass its IDs "
    "to a downstream query. It is not an inference that two vehicles interacted."
)
bfs_snapshot = st.session_state[BFS_KEY]
if bfs_snapshot:
    result = bfs_snapshot["event"]["data"]
    rows = bfs_snapshot["rows"]
    st.caption(
        f"BFS root: {result['root_id']} | Reached: {len(rows)} nodes | "
        f"Snapshot: {bfs_snapshot['loaded_count']} loaded vehicles | "
        f"Analyzed graph: {result['node_count']} nodes / {result['edge_count']} edges"
    )
    if bfs_snapshot["loaded_count"] != loaded_count:
        st.warning(
            "More records have been loaded since this BFS. Run BFS again to update the result."
        )
    hop_counts = Counter(row["hops"] for row in rows)
    st.dataframe(
        [
            {"hops_from_root": hop, "reached_nodes": count}
            for hop, count in sorted(hop_counts.items())
        ],
        hide_index=True,
    )
    st.markdown(
        "`visit_order` is the traversal order; `hops` is the minimum number of "
        "relationships from the root. `discovered_from` identifies the BFS "
        "parent, not ownership. Routes and service windows are original record fields."
    )
    visited_frame = records_to_dataframe(rows)
    st.dataframe(
        visited_frame, hide_index=True, height=280, key="progressive_bfs_records"
    )
    st.download_button(
        "Download BFS records",
        visited_frame.to_csv(index=False),
        file_name="progressive-bfs.csv",
        mime="text/csv",
        icon=":material/download:",
        on_click="ignore",
    )
    with st.expander("How returned IDs become this table"):
        st.code(inspect.getsource(bfs_result_rows), language="python")
    render_dictionary_preview(
        "Latest BFS dictionary",
        bfs_snapshot["event"],
        "`root_id` is the starting node; `node_ids` lists visits in order, and "
        "`edge_ids` contains the discovery-tree edges, not every edge among reached nodes. "
        "`scope='visible'` means displayed records, including off-screen nodes. "
        "`node_count`/`edge_count` describe the analyzed graph, not the reached subset. "
        "`complete` refers to that scope; `source_complete=False` is not proof that "
        "the whole source dataset has been analyzed.",
        height=280,
        expanded=True,
    )
else:
    st.info(
        "Select one graph node and run BFS from Analyze to populate the visit table."
    )

st.markdown("## Shortest path experiment")
st.markdown("""
BFS answers **what can I reach from one node?** Shortest path answers **what is
the fewest relationships connecting these two nodes?** Here paths are
undirected and unweighted, so they are not driving routes or earliest-arrival
calculations, even though the records include locations and times.

1. Enable **Include cross-location sightings**, then choose **Two nodes** above
   the graph. Clear any previous selection and click North interchange and
   South terminal. Open **Analyze > Shortest Path**.
2. At 60 vehicles, there is **no path in the displayed graph**. Load once and
   rerun: at 120, South is still disconnected.
3. Load again and rerun: at 180, expect **4 relationships** connecting
   `location-north -> vehicle-0061 -> location-central -> vehicle-0122 -> location-south`.
4. For a shorter comparison, clear the selection and select `vehicle-0001` and
   `vehicle-0004`: both share North, so the path has **2 relationships**, even
   at the first checkpoint and without optional sightings.

The endpoints are taken from the selected set, not necessarily click order;
the undirected distance is the same either way. Loading more does not rerun the
query. A missing path only describes loaded, displayed records, not the full source.
""")
path_snapshot = st.session_state[PATH_KEY]
if path_snapshot:
    path_result = path_snapshot["event"]["data"]
    path_rows = path_snapshot["rows"]
    st.caption(
        f"Shortest path: {path_result['source_id']} to {path_result['target_id']} | "
        f"Snapshot: {path_snapshot['loaded_count']} loaded vehicles"
    )
    if path_snapshot["loaded_count"] != loaded_count:
        st.warning(
            "More records have been loaded since this shortest path. Run it again to update the result."
        )
    if path_rows:
        st.success(f"Shortest path found: {len(path_rows)} relationships.")
        st.markdown(
            "These source relationship records explain the connection and can be "
            "exported or joined to another dataset. Rows are in source-record order, "
            "not traversal order; source/target are stored arrow directions."
        )
        path_frame = records_to_dataframe(path_rows)
        st.dataframe(
            path_frame, hide_index=True, height=230, key="progressive_path_records"
        )
        st.download_button(
            "Download path relationships",
            path_frame.to_csv(index=False),
            file_name="progressive-shortest-path.csv",
            mime="text/csv",
            icon=":material/download:",
            on_click="ignore",
        )
    else:
        st.info(
            "No path between these nodes in the displayed graph at this checkpoint."
        )
    render_dictionary_preview(
        "Latest shortest-path dictionary",
        path_snapshot["event"],
        "`source_id` and `target_id` are the endpoints. `distance` is the number of "
        "relationships when reachable; an unreachable distance is non-finite and may "
        "arrive as null. `node_ids`/`edge_ids` identify path members, not traversal order. "
        "For these distinct endpoints, no returned edges means no path. "
        "`scope='visible'` includes displayed nodes outside the viewport; "
        "`node_count`/`edge_count` describe the analyzed graph, not just the path.",
        height=280,
        expanded=True,
    )
else:
    st.info(
        "Select two graph nodes and run Shortest Path from Analyze to inspect their connection."
    )

st.markdown("## Clear the canvas selection")
st.markdown(
    "Use **Selection > Clear Selection**, or the details panel's **X**, after an "
    "analysis. Both remove selected-node/edge styling and analysis-result highlighting, "
    "without deleting records or moving the graph. Clicking a blank canvas only "
    "deselects records; it does not clear analysis highlights. Search matches have "
    "their own **Clear Search** button. Saved BFS and path tables remain as snapshots "
    "for comparison or download; Reset clears them."
)

render_dictionary_preview(
    "Returned progressive-loading value",
    value or {},
    """
    A load request contains the opaque cursor, requested page size, configured
    progress, remaining count, and the browser's current node and edge totals.
    `action` identifies the interaction, `data` holds its fields, and `timestamp`
    distinguishes events. `request_id` identifies one load attempt; the configured
    acknowledgement releases the button after that attempt has been handled.
    Selection, search, and analysis actions use their normal event dictionaries.
    A `positions` action also includes `movement`: the anchor, native and
    connected moved IDs, depth, candidate count, limit, and outcome. This page
    saves those coordinates before processing a later incremental batch.
    """,
    height=340,
    expanded=True,
)

st.markdown("## Choosing A Scaling Strategy")
st.markdown(
    """
    Use progressive pages for ordered result sets, node expansion for
    topology-driven discovery, and server-side filtering when the full graph is
    too large to be useful in one canvas. `performance_profile="large"` reduces
    rendering overhead, while `elements_sync="initial"` and graph commands
    reduce repeated Python-to-browser transfer costs.
"""
)

st.markdown("## Continue with a scale activity")
st.markdown(
    "The separate **Progressive Loading Scale Test** activity renders the same "
    "vehicle/location pattern at 100, 600, 1,000, 5,000, and 10,000 records. "
    "Use it to learn where your browser and styling choices remain comfortable; "
    "the benchmark numbers are machine- and browser-dependent."
)
if st.button(
    "Open the Progressive Loading Scale Test",
    icon=":material/speed:",
):
    st.switch_page("demos/progressive_loading_scale.py")

st.markdown("## What you can add to this workflow")
st.markdown("""
These are application extensions, not extra data automatically fetched by the component:

- **Your own provider:** replace the synthetic generator with an ordered,
  authorized database or API query. Keep the cursor tied to that query and cap
  page sizes in Python rather than trusting a browser request.
- **Time, type, or property filters:** apply them at the source before paging;
  reset the cursor and graph when the query changes. A displayed service time
  is currently metadata, not an active traversal filter.
- **Loading history:** record request IDs, page sizes, durations, and errors to
  explain slow or incomplete responses. Never advance the cursor on failure.
- **Result handoff:** use the BFS table and CSV download for route summaries,
  case notes, or a follow-up query. Keep the root and loaded-data checkpoint
  alongside the result so another reader knows what was actually analyzed.
- **Source-wide questions:** run an authorized query or algorithm against the
  full source when you need a global answer. A disconnected group in a partial
  graph does not prove there is no connection in records still waiting to load.
""")

st.markdown("## Conclusion")
st.markdown(
    """
    Progressive loading is an application-owned data workflow with a native
    graph trigger. It keeps fetching policy in Python and gives the browser only
    the bounded batches needed for the current task.
    """
)

render_source_expander(__file__)
