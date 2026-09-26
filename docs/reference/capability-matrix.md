# Capability matrix

Managed branch controls, filtered exploration, and loaded-record analysis live in
`expansionControls.js`, exposed through `expansion=controller.describe(provider)`.
See [managed expansion](expansion.md) and open **Branch Exploration** at
`/branch_expansion` in the local examples app.

## On this page

- [Python and browser responsibilities](#python-and-browser-responsibilities)
- [Coverage matrix](#coverage-matrix)
- [Choosing an integration surface](#choosing-an-integration-surface)

## Python and browser responsibilities

The public Python API configures and validates the component. Focused JavaScript
modules implement the live Cytoscape behaviors. This matrix identifies where a
feature enters the Python API, what happens in the browser, and where to run it.

## Coverage matrix

| Frontend module | Browser responsibility | Python surface | Streamlit demonstration |
| --- | --- | --- | --- |
| `index.js` | Mount and reconcile the graph | `graph_workbench`, `elements`, `layout`, `height`, `key` | Graph Workbench Showcase |
| `graph.js` | Cytoscape instance, selection, positions, viewport limits | `selection_mode`, `return_selection`, `return_positions`, `events`, zoom options | Investigation Tools |
| `boxSelection.js` | Pan/box-select canvas mode | `selection_mode="box"` | Investigation Tools |
| `styles.js` | Convert and apply style records | `NodeStyle`, `EdgeStyle`, `StyleRule` | Node Styles, Edge Styles |
| `search.js` | Text, label, property, and selector search | `search=True` | Investigation Tools |
| `nodeActions.js` | Expansion/removal intents and neighborhood visibility | `node_actions` | Node Actions |
| `toolbox.js` | Tool groups, statuses, and action availability | Action-list options | Graph Workbench Showcase |
| `dom.js` | Accessible control states and labels | Action-list options | Editing And Viewport Tools |
| `expansionBadges.js` | Expansion count badges | `node.data.expansion` | Node Actions |
| `analysis.js` | Path, traversal, component, and degree algorithms | `analysis_actions` | Investigation Tools |
| `crud.js` | CRUD intents with selected context | `crud_actions`, `on_change` | Interactive CRUD / Data Loading |
| `graphCommands.js` | Idempotent incremental graph/viewport commands | `graph_commands`, `elements_sync` | Data Helpers And Commands |
| `progressiveLoading.js` | Cursor-aware Load more requests and progress | `progressive_loading` | Progressive Loading |
| `selectionControls.js` | Select, clear, focus, hide, restore, and toggle details | `show_selection_details`, selection and visibility options | Investigation Tools |
| `connectedDrag.js` | Lazy bounded visible-hop following during a node drag | `connected_drag`, `ConnectedDragConfig`, `return_positions` | Select and use records, Progressive Loading |
| `toolbarLayout.js` | Adaptive expanded/compact controls, minimize/restore state, and measured canvas reservation | `toolbar`, `ToolbarConfig`, stable `key` | Arrange and navigate, Investigation Tools |
| `editTools.js` | Add, connect, delete, lock, drag state, snap, undo/redo | `edit_actions` | Editing And Viewport Tools |
| `viewportTools.js` / `viewbar.js` | Pan/zoom toggles and saved/reset views | `viewport_actions`, viewport options | Editing And Viewport Tools |
| `toolbar.js` | JSON, image, selected graph, and position exports | Toolbar plus `return_positions` | Investigation Tools |
| `graphStats.js` / `infopanel.js` | Counts and selected-element details | Elements and selection options | Graph Workbench Showcase |
| `payloads.js` | Normalize event dictionaries | `GraphEvent` return values | Investigation Tools |
| `layouts.js` | Load and run the newest valid layout | `layout`, `run_layout` command | Layout Algorithms |
| `expansion.js` | Format expansion counts and summaries | `node.data.expansion` | Node Actions |
| `helpers.js` / `state.js` | Isolate instance context and persistent UI state | Stable `key`, Components v2 state | Components V2 Validation |

## Choosing an integration surface

- Use component options to enable durable application capabilities.
- Use high-level action families before custom `Event` listeners.
- Use Python element helpers for full-state applications.
- Use graph commands for incremental browser updates.
- Use browser-local edit tools only when immediate visual feedback matters.

## Conclusion

Every browser capability has a documented Streamlit surface. Internal modules
are implementation details; consuming applications should import only from the
root `st_graph_workbench` package.
