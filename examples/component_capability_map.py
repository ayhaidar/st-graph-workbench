from __future__ import annotations


def javascript_capability_rows() -> list[dict[str, str]]:
    return [
        {
            "javascript module": "expansionControls.js",
            "browser responsibility": "Provides independent branch actions, filtered exploration dialogs, bounded bulk scheduling, and loaded-record analysis.",
            "Streamlit surface": "expansion=ExpansionController.describe(provider)",
            "example": "Branch Exploration",
        },
        {
            "javascript module": "index.js",
            "browser responsibility": "Mounts Cytoscape, reconciles full element updates, applies styles/layouts, and coordinates feature modules.",
            "Streamlit surface": "graph_workbench(elements, layout, height, key)",
            "example": "Graph Workbench Showcase",
        },
        {
            "javascript module": "graph.js",
            "browser responsibility": "Creates the Cytoscape instance, handles selection mode, emits selection and position events.",
            "Streamlit surface": "selection_mode, return_selection, return_positions, events, min_zoom, max_zoom, wheel_sensitivity",
            "example": "Investigation Tools",
        },
        {
            "javascript module": "boxSelection.js",
            "browser responsibility": "Switches blank-canvas dragging between graph panning and a visible node-selection rectangle.",
            "Streamlit surface": "selection_mode='box'",
            "example": "Investigation Tools",
        },
        {
            "javascript module": "styles.js",
            "browser responsibility": "Converts Python style records into Cytoscape style rules and applies highlight styles.",
            "Streamlit surface": "NodeStyle, EdgeStyle, StyleRule, node_styles, edge_styles",
            "example": "Node Styles, Edge Styles",
        },
        {
            "javascript module": "search.js",
            "browser responsibility": "Runs text, label, property, and selector search without hiding graph context.",
            "Streamlit surface": "search=True",
            "example": "Investigation Tools",
        },
        {
            "javascript module": "nodeActions.js",
            "browser responsibility": "Emits expand/remove intents and applies neighbor, incoming, outgoing, hide, and restore visibility tools.",
            "Streamlit surface": "node_actions=[...]",
            "example": "Node Actions, right-click expand/collapse",
        },
        {
            "javascript module": "toolbox.js",
            "browser responsibility": "Updates toolbox groups, selection status, action button states, and the expansion badge visibility toggle.",
            "Streamlit surface": "node_actions, selection_mode, return_selection",
            "example": "Graph Workbench Showcase, Investigation Tools",
        },
        {
            "javascript module": "dom.js",
            "browser responsibility": "Shares accessible button disabled, title, label, and pressed-state updates across toolbox modules.",
            "Streamlit surface": "Action lists such as node_actions, crud_actions, edit_actions, viewport_actions, and analysis_actions",
            "example": "Graph Workbench Showcase, Editing And Viewport Tools",
        },
        {
            "javascript module": "expansionBadges.js",
            "browser responsibility": "Draws expand/collapse count badges from node metadata.",
            "Streamlit surface": "node.data.expansion",
            "example": "Node Actions",
        },
        {
            "javascript module": "analysis.js",
            "browser responsibility": "Runs Cytoscape shortest path, BFS, DFS, connected components, and degree analysis.",
            "Streamlit surface": "analysis_actions=[...]",
            "example": "Investigation Tools",
        },
        {
            "javascript module": "crud.js",
            "browser responsibility": "Packages create/read/update/delete/load-related intents with selected graph context.",
            "Streamlit surface": "crud_actions=[...], on_change, st.session_state",
            "example": "Interactive CRUD / Data Loading",
        },
        {
            "javascript module": "graphCommands.js",
            "browser responsibility": "Applies one-time add, upsert, update, delete, set, clear, layout, and viewport commands.",
            "Streamlit surface": "graph_commands, elements_sync='initial'",
            "example": "Data Helpers And Commands",
        },
        {
            "javascript module": "progressiveLoading.js",
            "browser responsibility": "Shows loading progress and emits cursor-aware requests for the next bounded graph batch.",
            "Streamlit surface": "progressive_loading: ProgressiveLoadConfig",
            "example": "Progressive Loading",
        },
        {
            "javascript module": "selectionControls.js",
            "browser responsibility": "Selects, clears, focuses, hides/restores context, and toggles details without deselecting records.",
            "Streamlit surface": "show_selection_details, selection_mode, return_selection, node_actions visibility tools",
            "example": "Investigation Tools",
        },
        {
            "javascript module": "connectedDrag.js",
            "browser responsibility": "Lazily loads Cytoscape Automove, freezes a visible undirected hop scope for each gesture, and rigidly moves bounded connected followers.",
            "Streamlit surface": "connected_drag: ConnectedDragConfig, return_positions",
            "example": "Select and use records, Progressive Loading, Progressive Loading Scale Test",
        },
        {
            "javascript module": "toolbarLayout.js",
            "browser responsibility": "Chooses expanded or compact controls from component width, minimizes/restores the toolbar, and reserves its measured canvas space.",
            "Streamlit surface": "toolbar: ToolbarConfig, stable key",
            "example": "Arrange and navigate, Investigation Tools",
        },
        {
            "javascript module": "editTools.js",
            "browser responsibility": "Performs browser-local add, connect, delete, lock, unlock, grabbable, snap, undo, and redo edits.",
            "Streamlit surface": "edit_actions=[...]",
            "example": "Editing And Viewport Tools",
        },
        {
            "javascript module": "viewportTools.js / viewbar.js",
            "browser responsibility": "Controls pan/zoom, saved views, reset, fit, center, and zoom buttons.",
            "Streamlit surface": "viewport_actions=[...], min_zoom, max_zoom, wheel_sensitivity",
            "example": "Editing And Viewport Tools",
        },
        {
            "javascript module": "toolbar.js",
            "browser responsibility": "Exports visible graph JSON, full graph JSON, selected JSON, PNG, JPG, and node positions.",
            "Streamlit surface": "Built-in toolbar; return_positions for Python-side position payloads",
            "example": "Investigation Tools",
        },
        {
            "javascript module": "graphStats.js / infopanel.js",
            "browser responsibility": "Shows visible/hidden counts and selected element details.",
            "Streamlit surface": "elements, selection_mode, return_selection",
            "example": "Investigation Tools, Graph Workbench Showcase",
        },
        {
            "javascript module": "payloads.js",
            "browser responsibility": "Normalizes selection, search, CRUD, and positions payloads before returning them to Python.",
            "Streamlit surface": "Returned event dictionaries with action, data, timestamp",
            "example": "Investigation Tools, Interactive CRUD / Data Loading",
        },
        {
            "javascript module": "layouts.js",
            "browser responsibility": "Loads optional Cytoscape layout extensions, ignores stale async layout callbacks, and runs the newest layout request.",
            "Streamlit surface": "layout='cose' or layout={'name': 'preset', ...}",
            "example": "Layout Algorithms",
        },
        {
            "javascript module": "expansion.js",
            "browser responsibility": "Formats compact badge counts and expansion summaries from node metadata.",
            "Streamlit surface": "node.data.expansion",
            "example": "Graph Workbench Showcase, Node Actions",
        },
        {
            "javascript module": "helpers.js / state.js",
            "browser responsibility": "Keeps per-instance context, emitted events, Cytoscape references, and persistent UI state separated.",
            "Streamlit surface": "stable key, Components v2 state and trigger values",
            "example": "Components V2 Validation",
        },
    ]
