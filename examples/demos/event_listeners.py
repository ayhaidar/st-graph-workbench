import streamlit as st

from demos.demo_helpers import (
    demo_edge_styles,
    demo_graph,
    demo_node_styles,
    render_demo_intro,
    render_dictionary_preview,
    render_elements_dataframe,
    render_source_expander,
)
from st_graph_workbench import Event, graph_workbench


RUN_COUNT_KEY = "event_listeners_run_count"
st.session_state[RUN_COUNT_KEY] = st.session_state.get(RUN_COUNT_KEY, 0) + 1

render_demo_intro(
    "Event listeners",
    """
    Most apps should start with `return_selection`, `node_actions`,
    `crud_actions`, and `analysis_actions`. Use `Event(...)` when you need a
    raw Cytoscape event that is not covered by those higher-level options.
    """,
    [
        (
            "Custom event names",
            "`Event(name, event_type, selector)` labels the returned event with a non-reserved application name.",
        ),
        (
            "Cytoscape events",
            "`click tap`, `dblclick dbltap`, and other event names are accepted.",
        ),
        (
            "Selectors",
            "`node`, `edge`, `*`, or full Cytoscape selectors scope the listener.",
        ),
        (
            "Stable mounting",
            "Changing the event list updates the same browser graph instance.",
        ),
    ],
    sections=[
        (
            "Capability coverage",
            "When to use raw `Event(...)` listeners instead of higher-level options.",
        ),
        (
            "Event listener definitions",
            "The exact dictionaries sent to the component for the selected listener set.",
        ),
        (
            "Data before rendering",
            "The graph records that the raw Cytoscape listeners can target.",
        ),
        (
            "Interactive graph",
            "A graph that emits custom Cytoscape click, tap, and double-click events.",
        ),
        (
            "Try these checks",
            "Short interactions that confirm the returned event payload shape.",
        ),
        (
            "Returned value",
            "The custom event dictionary returned to Python after a matching browser event.",
        ),
    ],
)

event_mode = st.segmented_control(
    "Event set",
    ["Basic", "Node and edge", "High-priority selector"],
    default="Basic",
)

if event_mode == "Node and edge":
    events = [
        Event("node_click", "click tap", "node"),
        Event("edge_click", "click tap", "edge"),
    ]
elif event_mode == "High-priority selector":
    events = [
        Event("main_vehicle_click", "click tap", "node[label = 'MAIN_VEHICLE']"),
        Event("place_double_click", "dblclick dbltap", "node[label = 'PLACE']"),
    ]
else:
    events = [
        Event("clicked_node", "click tap", "node"),
        Event("double_clicked_anything", "dblclick dbltap", "*"),
    ]

elements = demo_graph()

st.markdown("#### Event listener definitions")
render_dictionary_preview(
    "Event listener definition dictionaries",
    [event.dump() for event in events],
    """
    Each dictionary defines one raw Cytoscape listener. `name` is the action
    returned to Python, `event_type` is the browser event to listen for, and
    `selector` scopes the listener to nodes, edges, or a Cytoscape selector.
    Names used by built-in component actions, such as `selection`, `search`,
    `analysis`, and `crud`, are reserved so event routing stays unambiguous.
    """,
    height=280,
    expanded=True,
)
st.caption(f"Page reruns in this session: {st.session_state[RUN_COUNT_KEY]}")

st.markdown("## Data before rendering")
st.markdown(
    """
    The listener selectors below run against this graph. A selector such as
    `node[label = 'MAIN_VEHICLE']` only emits events for matching records.
    """
)
render_elements_dataframe(elements, "Input graph records")

value = graph_workbench(
    elements,
    layout={"name": "preset", "fit": True, "padding": 60},
    node_styles=demo_node_styles(),
    edge_styles=demo_edge_styles(),
    events=events,
    selection_mode="multiple",
    return_selection=True,
    key="event-listeners",
    height=560,
)

st.markdown("## Try these checks")
st.markdown(
    """
    - Click a vehicle or location and inspect the returned event name.
    - Double-click the canvas or an element when the basic event set is active.
    - Switch event sets; the same graph instance updates its custom listeners.
    """
)

st.markdown("#### Returned value")
render_dictionary_preview(
    "Returned custom event dictionary",
    value or {},
    """
    This dictionary appears after a matching Cytoscape event fires. It names
    the custom action and includes the event type, target ID, and target group
    so Python can route raw graph interactions.
    """,
    height=300,
    expanded=True,
)

render_source_expander(__file__)
