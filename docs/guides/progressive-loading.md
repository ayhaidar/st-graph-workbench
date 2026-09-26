# Progressive loading

## On this page

- [Introduction](#introduction)
- [Why load graph data progressively](#why-load-graph-data-progressively)
- [Configuration](#configuration)
- [Runnable pattern](#runnable-pattern)
- [Returned dictionary](#returned-dictionary)
- [Failures and retries](#failures-and-retries)
- [Explore with BFS](#explore-with-bfs)
- [Compare shortest paths](#compare-shortest-paths)
- [Clear analysis highlights](#clear-analysis-highlights)
- [Update the loaded layout](#update-the-loaded-layout)
- [Move a loaded neighborhood](#move-a-loaded-neighborhood)
- [Scale activity](#scale-activity)
- [Choosing the right scaling tool](#choosing-the-right-scaling-tool)
- [Common mistakes](#common-mistakes)
- [Interactive example](#interactive-example)
- [Conclusion](#conclusion)

## Introduction

`progressive_loading` adds a small progress indicator and Load more command to
the graph canvas. The component does not fetch data itself. It returns a
cursor-aware request to Streamlit, where the application can enforce access,
filtering, ordering, and persistence rules before adding the next batch.

This separates data retrieval from graph interaction and works with SQL,
REST/GraphQL APIs, files, graph databases, and generated records.

## Why load graph data progressively

Sending every available node and edge at startup can create three independent
costs: Python serialization, component transfer, and browser layout/rendering.
Bounded pages improve time to first interaction and let users stop when the
visible graph already answers their question.

Unlike conventional table pagination, graph pages are additive. Existing
topology remains on screen while each new batch is appended with an idempotent
browser command.

## Configuration

`ProgressiveLoadConfig` accepts these fields:

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `page_size` | positive integer | `100` | Maximum domain records requested next |
| `loaded_count` | non-negative integer | `0` | Domain records already loaded |
| `total_count` | non-negative integer or `None` | `None` | Known total, or unknown for streaming sources |
| `has_more` | boolean | inferred | Whether Load more remains available |
| `cursor` | finite JSON scalar or `None` | `None` | Opaque continuation value returned unchanged |
| `acknowledged_request_id` | non-empty string or `None` | `None` | ID of the request Python finished handling, whether successfully or with a handled error |

`loaded_count` describes the application's paged records. It does not have to
equal the browser node count; one source record may create several nodes and
edges. The emitted event also reports the current browser counts separately.

## Runnable pattern

```python
--8<-- "docs/snippets/progressive_loading.py"
```

Use a stable component `key`, `elements_sync="initial"`, and a unique command
ID for every loaded batch. Mirror the command into Python-owned graph state so
a future remount can reconstruct the complete graph. Command IDs must remain
unique across resets of the data while the same browser component is mounted.
Keep the command sequence outside the reset operation, or use a session namespace.

The example displays five source records before the graph. Each vehicle gets
a deterministic position from its absolute source index. The first populated
batch is fitted into view; later batches keep existing positions and the
analyst's pan and zoom. Click the fit control to see the whole growing graph.

## Returned dictionary

Clicking Load more returns a dictionary like this:

```json
{
  "action": "load_more",
  "data": {
    "request_id": "64ff101f067c495992d70cd63a091bfb",
    "cursor": 300,
    "page_size": 100,
    "loaded_count": 300,
    "total_count": 10000,
    "remaining_count": 9700,
    "current_node_count": 304,
    "current_edge_count": 300
  },
  "timestamp": 1780000000000
}
```

| Field | Practical use |
| --- | --- |
| `action` | Route `load_more` to the loading callback, separately from selection or analysis |
| `data.request_id` | Deduplicate the request and acknowledge its completion; a retry receives a new ID |
| `data.cursor` | Query the next page using the application's continuation value |
| `data.page_size` | Bound the number of domain records fetched |
| `data.loaded_count` | Compare the request with the application's authoritative progress |
| `data.total_count` | Display the known total, or `None` when unknown |
| `data.remaining_count` | Report the configured total minus loaded count, or `None` |
| `data.current_node_count` | Compare browser nodes with the expected graph state |
| `data.current_edge_count` | Compare browser relationships with the expected graph state |
| `timestamp` | Record when the request was emitted; prefer `request_id` for deduplication |

## Failures and retries

The browser disables Load more immediately while one request is pending.
In a callback's `finally` block, echo `event["data"]["request_id"]` into
`progressive_loading["acknowledged_request_id"]`. This acknowledges handling,
not successful retrieval. On a handled failure, keep the graph, cursor, and
counts unchanged, show an application error, and let the user retry. Do not
acknowledge before an asynchronous fetch actually finishes.

The browser ignores an acknowledgment for a different request. An unrelated
Streamlit rerun does not unlock the button. Existing configurations without
acknowledgments still complete when their cursor, counts, or other progress
fields change. They need the new acknowledgment field to recover when nothing
changes, such as a failed or duplicate-only page.

An empty final page should set `has_more=False`; unknown totals can remain
`None`. If a page only repeats existing nodes, advance the source cursor as
appropriate and acknowledge the request without inventing new graph counts.
The component never retries a database or API call automatically.

## Explore with BFS

The **Progressive Loading** demo starts in single-node selection mode. Select
one node, then choose **Analyze > BFS**. BFS (breadth-first search) visits the
root, its neighbors, then the next layer of unseen neighbors. The component's
traversal is undirected and unweighted: arrows do not restrict it, and a hop
counts relationships rather than time or geographic distance. Search highlights
matches but does not select a BFS root.

At 60 vehicles, `location-north` reaches 21 nodes: itself and its 20 vehicles.
Starting at `vehicle-0001` reaches the same set, but other vehicles are two hops
away. Starting at `vehicle-0002` explores the Central group instead.

Enable **Include cross-location sightings** to restart with an optional scenario:

- At 60 vehicles, BFS from North reaches 21 nodes; there are three components.
- At 120, `vehicle-0061` is also seen at Central. North reaches 82 nodes across
  two locations; the displayed graph has two components.
- At 180, `vehicle-0122` connects Central to South. North reaches all 183 nodes,
  with a maximum of five hops; the graph has one component.

The optional sightings appear in the source preview before loading, but enter
the graph only with the matching page. Their timestamps are descriptive data,
not a time filter. Without the option, the three groups remain disconnected.

The page converts the actual browser result into a bounded visit table and CSV:
`node_ids` preserves visit order; `edge_ids` contains BFS discovery-tree edges,
not every edge in the reached subgraph. Joining those edges to the source data
recovers each record's parent and hop distance without running a second BFS.

Results retain their original loaded-record count. Loading more does not
automatically rerun analysis; the page marks the old snapshot and asks you to
run BFS again. `scope="visible"` means the displayed graph, including nodes
outside the viewport, not the unloaded source. `complete` describes that scope;
it is not a guarantee of source-wide coverage. A missing connection in a partial
graph is not evidence that the full dataset lacks that connection.

## Compare shortest paths

Choose **Two nodes** in the demo's **Selection for analysis** control. Clear any
old selection, click exactly two nodes, and choose **Analyze > Shortest Path**.
The library uses undirected, unweighted paths: distance counts relationships,
not minutes or road distance. BFS instead explores everything reachable from
one root. Switch back to **One node** for BFS or Degree.

With **Include cross-location sightings** enabled, compare `location-north`
and `location-south`. At 60 and 120 vehicles there is no path in the displayed
graph. At 180, the linking vehicles yield four relationships:
North, vehicle-0061, Central, vehicle-0122, South. As a simpler comparison,
`vehicle-0001` and `vehicle-0004` already share North at 60 vehicles: two hops.

The returned dictionary identifies the endpoints, distance, and path-member
IDs. Endpoints need not follow click order; node/edge ID arrays are not a
traversal sequence. The demo joins the returned edge IDs to Python records and
offers a relationship table and CSV. It keeps the loaded-count checkpoint and
marks stale results after another batch. No path means no path in that snapshot,
not proof of disconnection in unloaded source data.

## Clear analysis highlights

Choose **Selection > Clear Selection**, or the details panel's **X**, to clear
both selected records and analysis highlighting on nodes and edges. Graph
records, positions, zoom, and pan stay intact. Clicking blank canvas only
deselects records; **Clear Search** separately removes search matches.

The demo retains BFS and shortest-path tables as saved snapshots for comparison
and download, even after clearing canvas highlights. Resetting the graph or
changing the scenario clears those saved results.

## Update the loaded layout

The demo can rearrange the records currently loaded in the browser without
replacing the graph or fetching another page. Choose a layout and click **Apply
layout**. This sends a uniquely identified `run_layout` command:

```python
viewport_command(
    "layout-fcose-1",
    "run_layout",
    layout={
        "name": "fcose",
        "randomize": False,
        "fit": True,
        "padding": 55,
        "animate": False,
    },
)
```

`fCoSE`, `CoSE`, and `Cola` use graph relationships to calculate a
force-directed arrangement. Their simulations are bounded layout operations,
not permanent physics: nodes stop moving when the layout finishes. Structured
layouts such as breadth-first, Dagre, circle, and grid answer different visual
questions. **Source positions** restores the deterministic coordinates held in
the Python checkpoint.

Loading another page preserves the resulting browser positions. Apply a layout
again when the new topology should influence placement. Force-directed work
becomes more expensive as the loaded graph grows, so preset positions and local
exploration are usually preferable for very large views.

## Move a loaded neighborhood

The demo also passes a bounded `connected_drag` configuration. Open Selection,
enable **Move connected nodes**, and drag a location to move its currently
visible one-hop vehicle group without selecting every vehicle. The gesture scope
is frozen at grab time; records from a later Load more batch participate in the
next gesture.

`return_positions=True` returns all model coordinates plus a `movement`
explanation. The demo copies those coordinates into its Python checkpoint before
handling later batches. This is why Load more can append records without snapping
the manually arranged nodes back to their original source positions.

The 600-record lesson allows 250 automatic followers, enough for one location
group. The scale activity uses a conservative limit of 100: dragging a vehicle
can move a small local scope, while dragging a high-degree location is refused
atomically. This makes the cost boundary visible and avoids surprising partial
movement in a very large neighborhood.

## Choosing the right scaling tool

- Use progressive loading for ordered result sets and query pages.
- Use node expansion for topology-driven requests around selected nodes.
- Use `performance_profile="large"` when node count and layout cost dominate.
- Use `performance_profile="dense"` when edge count and visual density dominate.
- Use server-side search or filtering when the full result would not be useful
  on one canvas.
- Use compound nodes to summarize groups, not merely to conceal volume.

Progressive loading and node expansion can coexist. A global Load more action
can page through query results while node context-menu expansion retrieves a
specific neighborhood.

## Scale activity

Open **Progressive Loading Scale Test** in the local Feature Lab to render the
same deterministic vehicle/location graph at 100, 600, 1,000, 5,000, and 10,000
vehicle records. Each checkpoint creates three shared location nodes, one node
per vehicle, and one `SERVES` edge per vehicle. The page shows a source sample
before the graph and uses `performance_profile="large"` with preset positions.

Run the repeatable Chromium measurement from the repository root:

```powershell
uv run python scripts/benchmark_browser_graph.py --base-url http://localhost:8502
```

The command reports node and edge counts, time until each checkpoint is present
in Cytoscape, and JavaScript heap when Chromium exposes it. These are local
measurements, not a universal maximum. Topology, labels, styles, browser,
device memory, and interaction expectations all change the useful limit. When
the full graph becomes slow or visually unhelpful, keep the initial view small
and use **Load more**, server-side filters, or node expansion.

## Common mistakes

- Reusing a `command_id`, which causes the browser to ignore a later batch.
- Resetting the command counter when only the graph data is reset.
- Leaving a failed request pending instead of acknowledging it.
- Adding nodes without positions after starting with an empty graph: incremental
  additions do not automatically rerun a layout.
- Updating the browser command without applying the same mutation to Python.
- Passing already-known records to Python's strict `add_elements` helper.
  Filter duplicates first, or use an upsert command when replacing their data
  is intentional.
- Returning edges before their source and target nodes exist.
- Running a full animated layout after every small page.
- Enabling deep connected dragging without a finite follower limit.
- Ignoring returned positions, then reapplying stale source coordinates on rerun.
- Treating `loaded_count` as a security boundary instead of enforcing access in
  the Python data query.
- Loading indefinitely when server-side filtering would produce a clearer graph.

## Interactive example

Run the Streamlit examples app and open **Progressive Loading**:

```powershell
uv run streamlit run examples/app.py --server.port 8502
```

The page starts with visible mobility records, grows to 600 records in bounded
batches, and keeps selection, search, analysis, and viewport interaction active.

## Conclusion

The component owns the request control; the application owns the data policy.
Together with incremental commands, this gives large graphs a responsive,
auditable loading path without forcing every dataset into browser memory at
startup.
