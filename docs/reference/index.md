# API reference

## On this page

- [Component](#component)
- [Styling](#styling)
- [Data and elements](#data-and-elements)
- [Commands](#commands)
- [Managed expansion](#managed-expansion)
- [Events and types](#events-and-types)
- [Errors](#errors)

Import the supported public surface from `st_graph_workbench`.

Use this page to find the right function or type by task. Follow each section's
link for generated signatures, parameter defaults, accepted values, return
shapes, validation behavior, and source definitions.

## Component

See the generated [component API](component.md) for complete call details.

- `graph_workbench`: renders the interactive graph and returns browser events to Streamlit.
- `AnalysisAction`: identifies the supported shortest-path, traversal, component, and degree actions.
- `CrudAction`: identifies application-owned create, read, update, delete, and data-request intents.
- `EditAction`: identifies browser editing operations such as add, connect, lock, snap, undo, and redo.
- `ElementsSync`: selects full reconciliation or initial-elements-plus-command synchronization.
- `NodeAction`: identifies expansion, removal, neighborhood, and visibility controls.
- `PerformanceProfile`: selects rendering defaults for ordinary, large, or dense graphs.
- `ProgressiveLoadConfig`: configures cursor-aware batch requests and in-canvas loading progress.
- `ConnectedDragConfig`: configures bounded one-to-three-hop rigid movement of visible connected nodes.
- `ToolbarConfig`: configures adaptive, expanded, compact, or minimized graph controls and reserved canvas space.
- `SelectionMode`: selects single, multiple, or rectangular box selection.
- `ViewportAction`: identifies zoom, pan, save, restore, and reset viewport tools.

## Styling

See the generated [styling API](styles.md) for constructor parameters and output.

- `NodeStyle`: defines the appearance, caption, size, and icon for a node label.
- `EdgeStyle`: defines edge captions, color, width, line treatment, and direction arrows.
- `StyleRule`: applies raw Cytoscape style properties through an explicit selector.

## Data and elements

See the generated [data and element API](data-elements.md) for accepted record forms.

- `dataframe_to_records`: converts dataframe-like rows into JSON-compatible dictionaries.
- `records_to_dataframe`: converts ordinary records, grouped records, or graph elements into a dataframe.
- `validate_elements`: validates IDs, edge endpoints, compound parents, positions, and expansion metadata.
- `get_element`: returns a node or edge by its stable element ID.
- `upsert_elements`: immutably inserts new elements or replaces matching elements in Python-owned state.
- `update_element_data`: immutably updates the data fields of one existing node or edge.
- `delete_elements`: immutably removes requested elements and optionally their incident edges.

## Commands

See the generated [command API](commands.md) for payload fields and validation.

- `add_elements_command`: builds an incremental command that adds only missing nodes and edges.
- `upsert_elements_command`: builds a command that inserts new elements and updates matching IDs.
- `update_data_command`: builds a command that merges or replaces an element's data properties.
- `delete_elements_command`: builds a command that removes selected nodes, edges, and optional incident edges.
- `set_elements_command`: builds a command that replaces the browser graph with a complete element set.
- `clear_graph_command`: builds a command that removes every browser graph element.
- `viewport_command`: builds a fit, center, zoom, pan, position, or layout request.
- `validate_graph_commands`: validates command IDs, payloads, transitions, and graph references in order.
- `apply_graph_command`: applies one validated browser command to Python-owned graph state.
- `apply_graph_commands`: applies a sequence of commands to Python-owned state in command order.

## Managed expansion

See the [expansion API](expansion.md) for lifecycle, defaults, return values and provider contracts.

- `ExpansionController`: manages reversible branches, shared records, loaded data, view changes, and snapshots.
- `ExpansionConfig`: defines finite page-size, traversal-depth, node, and edge limits.
- `ExpansionOperation`: identifies explicit branch, loading, search, analysis, and protection operations.
- `ExpansionProvider`: defines the application-owned paginated loading interface.
- `ExpansionRequest`: identifies one versioned branch query, cursor, and requested batch size.
- `ExpansionResponse`: returns a validated batch, continuation cursor, and separate optional node/edge totals.
- `InMemoryExpansionProvider`: loads neighboring records and finds contextual source-search paths from an indexed dictionary graph.

## Events and types

See the generated [events and types API](events-types.md) for event construction and data contracts.

- `Event`: maps a Cytoscape event and selector to a named Streamlit event payload.
- `Element`: describes one Cytoscape-compatible node or edge dictionary.
- `ElementId`: describes a normalized scalar ID accepted by graph records.
- `ElementIdInput`: describes a single ID or iterable of IDs accepted by helper functions.
- `Elements`: describes the top-level `nodes` and `edges` graph dictionary.
- `GraphCommand`: describes one idempotent incremental browser command.
- `GraphEvent`: describes the action, data, and timestamp returned to Streamlit.
- `Layout`: describes a supported layout name or a layout options dictionary.
- `Record`: describes one JSON-compatible table or business-data dictionary.

## Errors

See the generated error definitions in the [data API](data-elements.md) and
[command API](commands.md).

- `ElementValidationError`: reports invalid element IDs, relationships, parents, positions, or metadata.
- `GraphCommandValidationError`: reports malformed commands or invalid command transitions.

See the [capability matrix](capability-matrix.md) to move from a user task to
the relevant API, frontend behavior, and Streamlit demonstration.
