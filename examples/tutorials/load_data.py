"""Round-trip records and validate imported graph JSON."""

import json
import streamlit as st
from demos.demo_helpers import SIGHTING_RECORDS, build_sighting_graph, demo_node_styles
from st_graph_workbench import (
    ElementValidationError,
    dataframe_to_records,
    graph_workbench,
    records_to_dataframe,
    validate_elements,
)
from tutorials.common import (
    show_example,
    begin_lesson,
    component_key,
    finish_lesson,
    show_graph_data,
    show_result,
    show_function,
)

state = begin_lesson(5)
show_graph_data(state["elements"])
st.markdown(
    "**Input table.** Vehicle, target, time, and confidence columns are ordinary application fields. Conversion preserves records; the graph builder decides which columns identify nodes and edges."
)
table = records_to_dataframe(SIGHTING_RECORDS)
table = st.data_editor(
    table, hide_index=True, key="tutorial_05_widget_table", num_rows="dynamic"
)
st.header("Code and working graph")
st.subheader("How this example works")
st.markdown("""
There are two separate transformations here. `records_to_dataframe` makes the
source dictionaries editable as rows; `dataframe_to_records` converts the edited
rows back to plain records. Neither function decides what an entity or a
relationship means in your application.

The sample `build_sighting_graph` function makes that decision explicitly:
`Entity` becomes a vehicle ID, `Target` becomes a normalized location ID, and
each sighting supplies an edge between them. Repeated entities share a node.
`Time` and `Confidence` remain properties of the relationship, rather than
creating a new node for every table cell. Edge IDs include the entity, location,
and time; a production dataset should use a reliable event key when available.

Editing the table prepares a candidate graph. **Build from table** accepts it
only after validation. JSON import follows the same boundary: parse the text,
validate the complete candidate, then replace the current checkpoint. The last
accepted graph remains visible if parsing or validation fails.
""")
with show_example(__file__):
    # Conversion makes plain row dictionaries; the builder assigns graph meaning.
    records = dataframe_to_records(table)
    try:
        graph = build_sighting_graph(records)
        # Never replace the current checkpoint with an invalid candidate.
        validate_elements(graph)
    except (ValueError, KeyError, TypeError) as error:
        st.error(f"Cannot build this table: {error}")
    else:
        if st.button("Build from table", icon=":material/account_tree:"):
            state["elements"] = graph
            st.rerun()
with st.expander("Import graph JSON"):
    text = st.text_area(
        "Graph JSON",
        json.dumps(state["elements"], indent=2),
        height=220,
        key="tutorial_05_widget_json",
    )
    with show_example(__file__):
        if st.button("Validate and load", icon=":material/upload:"):
            try:
                # Parse and validate before changing any accepted source records.
                candidate = json.loads(text)
                validate_elements(candidate)
            except (
                json.JSONDecodeError,
                ElementValidationError,
                TypeError,
                ValueError,
            ) as error:
                st.error(str(error))
            else:
                state["elements"] = {
                    "nodes": candidate.get("nodes", []),
                    "edges": candidate.get("edges", []),
                }
                st.rerun()
with show_example(__file__):
    result = graph_workbench(
        state["elements"],
        layout={"name": "grid", "padding": 60},
        node_styles=demo_node_styles(text_size=18),
        key=component_key(5),
        height=600,
    )
st.subheader("Try it and check the result")
st.markdown("""
1. Change a confidence value and inspect the converted row dictionary below.
   Until you choose **Build from table**, the graph still shows the last accepted
   checkpoint. After building, the edge carries the new `confidence` value.
2. Compare the five source rows with the resulting seven nodes and five edges.
   Shared entity IDs explain why a row count is not the same as a node count.
3. In **Import graph JSON**, change an edge endpoint to an ID that is absent
   from `nodes` and choose **Validate and load**. Read the error and confirm that
   the existing graph is retained. Restore the valid endpoint before loading.

For your own dataset, replace the sample builder's column mapping while keeping
the conversion and validation steps. Keep original IDs stable across reloads.
""")
st.subheader("Code in practice")
show_function(
    build_sighting_graph,
    "**From rows to relationships.** This is the sample builder executed above. "
    "Read the node-ID mapping first, then the source/target fields and retained "
    "time/confidence properties. Replace this application-specific mapping for your own columns.",
)
show_result(
    records[:2],
    "Each dictionary is one source-table row. `Entity` and `Target` become graph endpoints; `Time` and `Confidence` remain relationship properties. `records_to_dataframe` also accepts grouped graph dictionaries and flattens their `data` fields.",
    label="Converted source records",
)
finish_lesson(
    5,
    __file__,
    mistakes="Dataframe conversion alone does not infer relationships. Use explicit column mapping and stable IDs. Invalid JSON or dangling edges leave the current graph unchanged.",
    conclusion="The library handles record conversion and graph validation; your application chooses the meaning of its columns.",
)
