import streamlit as st
from st_graph_workbench import Event, NodeStyle, graph_workbench
from demos.demo_helpers import (
    capability_rows,
    render_capability_summary,
    render_dictionary_preview,
    render_elements_dataframe,
    render_source_expander,
)
from page_overview import render_page_overview

st.markdown("# Components V2 Validation")
st.markdown(
    """
    This page mounts two graph components at the same time to validate the v2
    no-iframe runtime. The graphs use independent keys, callback events, toolbox
    state, icon assets, expansion badges, and light-DOM Cytoscape pointer
    handling. The keys deliberately include `__` and `--` variants to catch
    lossy key normalization bugs.
    """
)

render_page_overview(
    [
        (
            "Capability coverage",
            "Components v2 multi-instance behavior, raw events, validation, and expansion badges.",
        ),
        (
            "Left component",
            "A vehicle graph instance with independent key, dynamic selection mode, dynamic zoom bounds, events, toolbox state, and badge data.",
        ),
        (
            "Right component",
            "A person graph instance mounted beside the first graph without an iframe or shared state.",
        ),
        (
            "Data before rendering",
            "The independent left and right graph records sent to two component instances.",
        ),
        (
            "Returned dictionaries",
            "Independent returned values from both graph components.",
        ),
    ],
    description="This validation overview explains what the side-by-side component test shows.",
)

render_capability_summary(
    "What this demo covers",
    [
        row
        for row in capability_rows()
        if row["capability"]
        in {
            "Components v2 multi-instance behavior",
            "Custom event listeners",
            "Validation",
        }
    ],
    description="The runtime and validation behavior demonstrated by the two graph instances.",
)

layout = {
    "name": "preset",
    "fit": True,
    "padding": 40,
}

left_box_selection = st.toggle(
    "Use box selection on left graph",
    value=False,
    help=(
        "Reruns the page with the same component key. The existing Cytoscape "
        "instance should switch selection behavior without remounting."
    ),
    key="v2_validation_left_box_selection",
)
left_selection_mode = "box" if left_box_selection else "single"
left_limit_zoom = st.toggle(
    "Limit left graph zoom bounds",
    value=False,
    help=(
        "Reruns the page with the same component key. The existing Cytoscape "
        "instance should apply and clear zoom bounds without remounting."
    ),
    key="v2_validation_left_limit_zoom",
)
left_min_zoom = 0.5 if left_limit_zoom else None
left_max_zoom = 2.0 if left_limit_zoom else None

node_styles = [
    NodeStyle("MAIN_VEHICLE", "#2A629A", "name", "directions_car"),
    NodeStyle("PERSON", "#FF7F3E", "name", "person"),
]

left_elements = {
    "nodes": [
        {
            "data": {
                "id": "left_root",
                "label": "MAIN_VEHICLE",
                "name": "ABC123",
                "expansion": {
                    "state": "collapsed",
                    "next_count": 2,
                    "total_count": 1250,
                    "depth": 4,
                },
            },
            "position": {"x": 100, "y": 100},
        }
    ],
    "edges": [],
}

right_elements = {
    "nodes": [
        {
            "data": {
                "id": "right_root",
                "label": "PERSON",
                "name": "Right Root",
                "expansion": {
                    "state": "collapsed",
                    "next_count": 3,
                    "total_count": 3,
                    "depth": 1,
                },
            },
            "position": {"x": 100, "y": 100},
        }
    ],
    "edges": [],
}

left_events = [Event("left_node_click", "click tap", "node")]
right_events = [Event("right_node_click", "click tap", "node")]

st.markdown("## Data before rendering")
st.markdown(
    """
    These two element dictionaries are intentionally small and separate. They
    prove that keys, expansion badges, event payloads, and selection state stay
    isolated across mounted Components v2 instances.
    """
)
data_left, data_right = st.columns(2)
with data_left:
    render_elements_dataframe(left_elements, "Left graph records")
with data_right:
    render_elements_dataframe(right_elements, "Right graph records")

left_col, right_col = st.columns(2)

with left_col:
    st.markdown("### Left Component")
    left_value = graph_workbench(
        left_elements,
        layout=layout,
        node_styles=node_styles,
        events=left_events,
        node_actions=["remove", "expand"],
        selection_mode=left_selection_mode,
        min_zoom=left_min_zoom,
        max_zoom=left_max_zoom,
        key="V2_VALIDATION__GRAPH",
        height=420,
    )
    render_dictionary_preview(
        "Left returned value",
        left_value or {},
        """
        This dictionary belongs only to the left component instance. It verifies
        that events, selected IDs, and expansion actions stay scoped to the
        left graph key.
        """,
        height=300,
        expanded=True,
    )

with right_col:
    st.markdown("### Right Component")
    right_value = graph_workbench(
        right_elements,
        layout=layout,
        node_styles=node_styles,
        events=right_events,
        node_actions=["remove", "expand"],
        key="V2_VALIDATION--GRAPH",
        height=420,
    )
    render_dictionary_preview(
        "Right returned value",
        right_value or {},
        """
        This dictionary belongs only to the right component instance. It should
        update independently from the left graph, proving that Components v2
        state does not leak between mounted graphs.
        """,
        height=300,
        expanded=True,
    )


render_source_expander(__file__)
