import streamlit as st

from component_capability_map import javascript_capability_rows
from page_overview import render_javascript_capability_map, render_page_overview

st.markdown("# Frontend Architecture For Python Developers")
st.markdown(
    """
    The frontend is mostly a bridge between Python dictionaries and Cytoscape.js.
    """
)

render_page_overview(
    [
        (
            "Update flow",
            "The end-to-end rerun path from Python to Cytoscape and back to Streamlit.",
        ),
        (
            "JavaScript glossary",
            "Plain-language names for the browser-side objects and modules.",
        ),
        (
            "Feature to API map",
            "How JavaScript modules map to public Streamlit arguments and helpers.",
        ),
        (
            "Annotated snippet",
            "The main frontend render loop shown as a readable code example.",
        ),
        (
            "Reading the files",
            "Where to start when inspecting the component implementation.",
        ),
        (
            "CRUD, edit, and viewport events",
            "How browser interactions become dictionaries returned to Python.",
        ),
        (
            "Dynamic option updates",
            "Which Python options are synchronized onto an existing Cytoscape instance after reruns.",
        ),
        (
            "Layout lifecycle guard",
            "How asynchronous layout extension loading avoids applying stale positions after a newer rerun.",
        ),
        (
            "Light-DOM runtime choice",
            "Why the component uses Components v2 without an iframe but keeps Cytoscape in the light DOM.",
        ),
    ],
    description="This overview gives Python readers a route through the frontend notes.",
)

st.markdown("## Update Flow")
st.markdown(
    """
    1. Your Streamlit app calls `graph_workbench(...)`.
    2. Python validates `elements`, validates any `graph_commands`, and
       serializes options such as `layout`, `events`, `node_actions`,
       `edit_actions`, `viewport_actions`, `selection_mode`, and
       `analysis_actions`.
    3. Components v2 mounts the HTML directly in the Streamlit page.
    4. `index.js` creates one Cytoscape instance per component mount.
    5. Cytoscape events call small JavaScript handlers.
    6. Handlers send a trigger value back to Streamlit.
    7. Streamlit reruns your Python script.
    8. For normal mode, Python sends updated `elements`.
    9. For command mode, Python keeps full `elements` in session state but sends
       only small `graph_commands` such as `upsert_elements`.
    """
)

st.markdown("## Small JavaScript Glossary")
st.markdown(
    """
    - `cy`: the Cytoscape graph object.
    - `node`: one graph node.
    - `edge`: one graph relationship.
    - `selector`: a Cytoscape query string, similar in spirit to a CSS selector.
    - `style`: a Cytoscape stylesheet rule.
    - `layout`: the algorithm/options used to place nodes.
    - `event`: a click, selection, drag, layout, or custom action.
    - `renderData`: the normalized data sent from Python into JavaScript.
    - `context`: this component instance's DOM, Cytoscape, state, and Streamlit bridge.
    - `state`: frontend-only values such as current selection and badge visibility.
    - `graph_commands`: small one-time instructions such as add, update, delete,
      fit, center, pan, zoom, set viewport, set zoom bounds, or run layout.
    """
)

st.markdown("## JavaScript Feature To Streamlit API Map")
st.markdown(
    """
    The public Python API is intentionally smaller than the JavaScript
    implementation. Users do not need to call these JavaScript files directly;
    they enable them through `graph_workbench(...)` arguments, style helpers,
    event listeners, and graph command helpers.
    """
)
render_javascript_capability_map(javascript_capability_rows(), height=620)

st.markdown("## Annotated Snippet")
st.code(
    """
// Python passes elements and options into the component.
function renderGraph(component) {
    const renderData = normalizeRenderData(component.data);

    // Each Streamlit component mount gets its own Cytoscape instance.
    let instance = COMPONENT_INSTANCES.get(component.parentElement);
    if (!instance) {
        instance = initializeInstance(component, renderData);
    }

    // Full-sync mode: reconcile changed elements in place.
    if (renderData.hasElements) {
        reconcileElements(renderData.elements, lastExpandedNode, instance);
    }

    // Command mode: apply only unseen command IDs to the existing graph.
    applyGraphCommands(instance, renderData.graphCommands, renderData.layout);
}
""",
    language="javascript",
)

st.markdown("## Reading The Files")
st.markdown(
    """
    Start with `component.py` to see the public Python API. Then read `index.js`
    to see how Python data is normalized. The feature modules under
    `frontend/src/components` are intentionally small: one file owns search,
    one owns analysis, one owns selection controls, and so on.
    """
)

st.markdown("## Dynamic Option Updates")
st.markdown(
    """
    Most Streamlit reruns reuse the existing Cytoscape instance for smooth
    interaction.
    
    The renderer therefore synchronizes runtime-safe options after
    every rerun: `selection_mode` updates Cytoscape's `selectionType` and
    `boxSelectionEnabled` flags, while `boxSelection.js` provides a visible
    Pan/Box select switch so blank-canvas dragging can either navigate the
    graph or draw a node-selection rectangle.

    `min_zoom` and `max_zoom` update the graph's zoom bounds. `height` updates
    the component container on rerun, and a `ResizeObserver` calls `cy.resize()`
    when Streamlit or the browser changes the available graph space.
    
    When `min_zoom` or `max_zoom` is removed by sending `None`, the frontend restores
    Cytoscape's original default bound for that value. The same convention
    applies to `graph_commands`: `set_viewport` with `zoom=None` leaves the
    current zoom alone, and `set_zoom_bounds` with a `None` bound resets that
    side to the original Cytoscape default.
    
    Viewport command values that drive
    animation are validated in Python before they reach the browser: `duration`
    and `fit` `padding` must be finite non-negative numbers, zoom anchors must
    include numeric `x` and `y`, and `min_zoom` cannot exceed `max_zoom`.
    
    Direct `graph_workbench(...)` viewport arguments are checked the same way
    before rendering: `min_zoom`, `max_zoom`, and `wheel_sensitivity` must be
    finite numeric values when provided; `min_zoom` cannot exceed `max_zoom`;
    and `wheel_sensitivity` must be greater than zero.

    Some Cytoscape options are only read during initialization. For example,
    `wheel_sensitivity` should be paired with a changed component `key` when
    you want the browser graph to remount with a new wheel setting.
    """
)

st.markdown("## Layout Lifecycle Guard")
st.markdown(
    """
    Some Cytoscape layouts are loaded asynchronously as separate JavaScript
    chunks. The frontend gives every layout request a per-instance run token.
    If a slow older extension import finishes after a newer Streamlit rerun,
    the old callback is ignored and cannot run a stale layout or mark the graph
    ready. That keeps manual movement, progressive expansion, and layout
    switches tied to the newest graph state instead of a previous request.
    """
)

st.markdown("## Components V2 Runtime Choice")
st.markdown(
    """
    The component uses Streamlit Components v2 and does not render through a v1
    iframe. It intentionally mounts with `isolate_styles=False` because
    Cytoscape's box-selection pointer handling needs light-DOM browser events
    to hit nodes reliably. The frontend CSS stays scoped under the
    `.st-graph-workbench` root to avoid leaking graph styling into surrounding
    Streamlit content.
    """
)

st.markdown("## CRUD Events")
st.markdown(
    """
    CRUD buttons live in `frontend/src/components/crud.js`. They do not change
    your permanent graph by themselves. Instead, they read the current
    Cytoscape selection, create an event payload, and send it back to Streamlit.
    Your Python code then updates `elements` and can queue a `graph_commands`
    payload. In `elements_sync="initial"` mode, that lets the browser add,
    update, or delete only the changed graph pieces without receiving the full
    element dictionary again. Command lists are validated and applied in order,
    so a command can add a node and a later command in the same rerun can add
    an edge to that new node.
    """
)

st.markdown("## Edit And Viewport Events")
st.markdown(
    """
    Edit buttons live in `frontend/src/components/editTools.js`. They call
    Cytoscape directly for fast browser feedback: `cy.add(...)`,
    `eles.remove()`, `node.lock()`, `node.unlock()`, and
    `nodes.positions(...)`. After the browser graph changes, the component
    emits an `action == "edit"` payload with the small delta that Python can
    mirror into `st.session_state`. Toolbox dropdowns close after command
    buttons fire so the menu cannot sit above the canvas and intercept the next
    drag or pan gesture. Real drag-position events bypass the short suppression
    window used for edit-command payloads, which keeps manual layout updates
    visible to Python even when the user drags immediately after restoring a
    fixed or locked node.

    Viewport buttons live in `frontend/src/components/viewportTools.js`. They
    use Cytoscape viewport methods for user zoom/pan toggles, browser-local
    saved views, restore, and reset. Python can also send viewport
    `graph_commands` when it needs to drive the browser graph.
    """
)
