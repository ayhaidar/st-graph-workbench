from st_graph_workbench import EdgeStyle, NodeStyle, graph_workbench

# Match the label in each node's data; display its name and a packaged icon.
node_styles = [
    NodeStyle("VEHICLE", "#2A629A", "name", "directions_car", size=40),
    NodeStyle("LOCATION", "#2D936C", "name", "place", size=40),
]
edge_styles = [
    EdgeStyle("SEEN_AT", "#2D936C", "label", directed=True),
]

# Reuse elements from the previous example with a separate component key.
event = graph_workbench(
    elements,
    layout="cose",
    node_styles=node_styles,
    edge_styles=edge_styles,
    selection_mode="multiple",
    return_selection=True,
    search=True,
    key="readme_styled_output",
    height=420,
)
