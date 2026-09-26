import streamlit as st

from page_overview import render_page_overview

st.markdown("# Graph Data Format")
st.markdown(
    """
    In this library, the graph you pass from Python is called `elements`.

    You may also see this called an **element data contract**. That just means:
    the component expects your graph data to follow a known dictionary shape. If
    your data follows that shape, Python can validate it and Cytoscape.js can
    draw it in the browser.
    """
)

render_page_overview(
    [
        (
            "The minimum graph",
            "The smallest valid `elements` dictionary with node and edge lists.",
        ),
        (
            "What the fields mean",
            "The required IDs, labels, source/target fields, and optional extra data.",
        ),
        (
            "The most important rule",
            "How node IDs and edge endpoints must match for Cytoscape to render correctly.",
        ),
        (
            "Optional data",
            "How application-specific values can stay attached to graph elements.",
        ),
        (
            "Expansion data",
            "The optional node metadata that drives expand/collapse badges.",
        ),
        (
            "Validation and flow",
            "What Python validates before sending graph data to the browser.",
        ),
    ],
    description="This overview summarizes the graph data contract before the examples.",
)

st.info(
    "`elements` is the source graph document: it contains your nodes, your edges, "
    "and any extra properties you want to keep on those nodes and edges.",
    icon=":material/info:",
)

st.markdown("## The Minimum Graph")
st.markdown(
    """
    A graph needs two lists:

    - `nodes`: the things you want to display.
    - `edges`: the relationships between those things.

    Each node and edge has a `data` dictionary. The required values live inside
    that `data` dictionary.
    """
)

st.code(
    """
elements = {
    "nodes": [
        {
            "data": {
                "id": "vehicle-1",
                "label": "VEHICLE",
                "name": "ABC123",
            }
        },
        {
            "data": {
                "id": "place-1",
                "label": "PLACE",
                "name": "Harbor Camera 4",
            }
        },
    ],
    "edges": [
        {
            "data": {
                "id": "edge-1",
                "label": "SEEN_AT",
                "source": "vehicle-1",
                "target": "place-1",
                "observed_at": "2024-09-02 08:14",
            }
        }
    ],
}
""",
    language="python",
)

st.markdown("## What The Fields Mean")
st.markdown(
    """
    | Field | Where | Meaning |
    | --- | --- | --- |
    | `data.id` | Node and edge | Unique ID. Every node and edge needs one. |
    | `data.label` | Node and edge | Category/type, such as `VEHICLE`, `PLACE`, or `SEEN_AT`. Styles use this. |
    | `data.source` | Edge only | The ID of the node where the edge starts. |
    | `data.target` | Edge only | The ID of the node where the edge ends. |
    | Extra fields | Node and edge | Your own data, such as `name`, `email`, `risk`, `country`, or `amount`. |
    """
)

st.markdown(
    """
    The `label` field is especially important because `NodeStyle` and `EdgeStyle`
    match against it:
    """
)

st.code(
    """
node_styles = [
    NodeStyle("VEHICLE", color="#FF7F3E", caption="name", icon="directions_car"),
    NodeStyle("PLACE", color="#2A629A", caption="name", icon="place"),
]

edge_styles = [
    EdgeStyle("SEEN_AT", caption="label", directed=True),
]
""",
    language="python",
)

st.markdown("## The Most Important Rule")
st.markdown(
    """
    Edge `source` and `target` values must point to existing node IDs.

    In the example above:

    - `source="vehicle-1"` works because a node with `id="vehicle-1"` exists.
    - `target="place-1"` works because a node with `id="place-1"` exists.
    """
)

st.code(
    """
# This is invalid because there is no node with id "missing-place".
bad_elements = {
    "nodes": [{"data": {"id": "vehicle-1", "label": "VEHICLE"}}],
    "edges": [
        {
            "data": {
                "id": "edge-1",
                "label": "SEEN_AT",
                "source": "vehicle-1",
                "target": "missing-place",
            }
        }
    ],
}
""",
    language="python",
)

st.markdown("## Optional Data Is Yours")
st.markdown(
    """
    Anything extra inside `data` stays attached to the element. The component can
    show it in the info panel, use it in search, return it in selection or CRUD
    events, and pass it back to your Streamlit app.
    """
)

st.code(
    """
{
    "data": {
        "id": "vehicle-1",
        "label": "VEHICLE",
        "name": "ABC123",
        "plate_state": "NSW",
        "risk_score": 82,
        "status": "Under review",
    }
}
""",
    language="python",
)

st.markdown("## Optional Expansion Data")
st.markdown(
    """
    Expansion data controls the small `+N` or `-N` badge on a node. It is useful
    when your Streamlit callback can load more related nodes on demand.
    """
)

st.code(
    """
{
    "data": {
        "id": "vehicle-1",
        "label": "VEHICLE",
        "name": "ABC123",
        "expansion": {
            "state": "collapsed",
            "next_count": 12,
            "total_count": 1250,
            "depth": 4,
        },
    }
}
""",
    language="python",
)

st.markdown(
    """
    | Expansion field | Meaning |
    | --- | --- |
    | `state` | `collapsed` or `expanded`. |
    | `next_count` | How many nodes the next expand click will reveal. This is what appears on the badge. |
    | `total_count` | Total hidden descendants across deeper layers. This appears in the info panel. |
    | `depth` | Number of hidden layers below this node. |
    | `collapse_count` | How many currently visible descendants a collapse action would hide. |
    """
)

st.markdown("## What Validation Checks")
st.markdown(
    """
    `graph_workbench(..., validate=True)` is the default. Before the graph reaches
    the browser, Python checks for common mistakes:

    - `elements` is not a dictionary.
    - `nodes` or `edges` is not a list.
    - A node or edge is missing `data`.
    - A node or edge is missing `data.id`.
    - Two elements have the same ID.
    - An edge points to a node ID that does not exist.
    - A compound node uses `data.parent`, but the parent node does not exist.
    - Expansion data is malformed, such as negative counts or an unknown state.
    """
)

st.markdown("## Python To Browser Flow")
st.markdown(
    """
    The flow is:

    1. You create `elements` in Python.
    2. You pass it to `graph_workbench(elements, ...)`.
    3. Python validates the dictionary.
    4. Streamlit Components v2 sends it to the browser.
    5. Cytoscape.js reads the same nodes and edges and draws the graph.

    So the contract is simply the shared format between your Python code and
    Cytoscape.js.
    """
)
