import copy
import json
from pathlib import Path

import streamlit as st

from demos.demo_helpers import (
    RELATED_RECORDS,
    SIGHTING_RECORDS,
    build_sighting_graph,
    demo_edge_styles,
    demo_node_styles,
    graph_summary_rows,
    render_demo_intro,
    render_dictionary_preview,
    render_elements_dataframe,
    render_source_expander,
)
from st_graph_workbench import (
    Element,
    Elements,
    GraphCommand,
    GraphCommandValidationError,
    add_elements_command,
    apply_graph_command,
    apply_graph_commands,
    clear_graph_command,
    dataframe_to_records,
    delete_elements,
    delete_elements_command,
    get_element,
    graph_workbench,
    records_to_dataframe,
    set_elements_command,
    update_data_command,
    update_element_data,
    upsert_elements,
    upsert_elements_command,
    validate_elements,
    validate_graph_commands,
    viewport_command,
)
from st_graph_workbench.component.validation import ElementValidationError


STATE_KEY = "data_helpers_commands_elements"
COMMANDS_KEY = "data_helpers_commands_commands"
COMMAND_SEQ_KEY = "data_helpers_commands_sequence"
NOTICE_KEY = "data_helpers_commands_notice"
LAST_COMMAND_KEY = "data_helpers_commands_last_command"
COMPONENT_KEY = "data_helpers_commands_graph"
SAMPLE_GRAPH_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "intelligence_case.json"
)


@st.cache_data
def load_graph_file(path: str) -> Elements:
    """Load a Cytoscape elements dictionary from a local JSON file."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Graph JSON must contain an object at the top level.")
    validate_elements(payload)
    return payload


def initial_elements() -> Elements:
    return build_sighting_graph(SIGHTING_RECORDS)


def ensure_state() -> None:
    st.session_state.setdefault(STATE_KEY, initial_elements())
    st.session_state.setdefault(COMMANDS_KEY, [])
    st.session_state.setdefault(COMMAND_SEQ_KEY, 0)
    st.session_state.setdefault(NOTICE_KEY, "")
    st.session_state.setdefault(LAST_COMMAND_KEY, None)


def next_command_id(prefix: str) -> str:
    st.session_state[COMMAND_SEQ_KEY] += 1
    return f"{prefix}-{st.session_state[COMMAND_SEQ_KEY]}"


def queue_command(command: GraphCommand, *, mutate_python_graph: bool = True) -> None:
    try:
        validate_graph_commands([command], elements=st.session_state[STATE_KEY])
        if mutate_python_graph:
            st.session_state[STATE_KEY] = apply_graph_command(
                st.session_state[STATE_KEY],
                command,
            )
        st.session_state[COMMANDS_KEY] = [command]
        st.session_state[LAST_COMMAND_KEY] = command
        st.session_state[NOTICE_KEY] = f"Queued `{command['operation']}`."
    except (GraphCommandValidationError, ElementValidationError, KeyError) as error:
        st.session_state[NOTICE_KEY] = str(error)


def checkpoint_element() -> tuple[Element, Element]:
    next_index = st.session_state[COMMAND_SEQ_KEY] + 1
    node_id = f"checkpoint_{next_index}"
    node = {
        "data": {
            "id": node_id,
            "label": "CHECKPOINT",
            "name": f"Checkpoint {next_index}",
        },
        "position": {"x": 610, "y": 520 + 30 * (next_index % 3)},
    }
    edge = {
        "data": {
            "id": f"{node_id}-location_2",
            "label": "Related",
            "source": node_id,
            "target": "location_2",
        }
    }
    return node, edge


def add_checkpoint() -> None:
    node, edge = checkpoint_element()
    queue_command(
        add_elements_command(
            next_command_id("add-checkpoint"),
            nodes=node,
            edges=edge,
        )
    )


def upsert_owner_branch() -> None:
    graph = st.session_state[STATE_KEY]
    command = upsert_elements_command(
        next_command_id("upsert-owner"),
        nodes=[
            {
                "data": {
                    "id": "Person_MReed",
                    "label": "PERSON",
                    "name": "Maya Reed",
                    "priority": "review",
                },
                "position": {"x": 610, "y": 130},
            },
            {
                "data": {
                    "id": "Phone_0412",
                    "label": "PHONE",
                    "name": "0412 000 111",
                    "priority": "review",
                },
                "position": {"x": 610, "y": 330},
            },
        ],
        edges=[
            {
                "data": {
                    "id": "ABC123-Person_MReed",
                    "label": "Registered To",
                    "source": "ABC123",
                    "target": "Person_MReed",
                }
            },
            {
                "data": {
                    "id": "Person_MReed-Phone_0412",
                    "label": "Uses",
                    "source": "Person_MReed",
                    "target": "Phone_0412",
                }
            },
        ],
        replace=False,
    )
    validate_graph_commands([command], elements=graph)
    queue_command(command)


def update_main_vehicle() -> None:
    queue_command(
        update_data_command(
            next_command_id("update-main-vehicle"),
            "ABC123",
            {"priority": "critical", "reviewed": True},
            merge=True,
        )
    )


def delete_checkpoints() -> None:
    graph = st.session_state[STATE_KEY]
    node_ids = [
        str(node["data"]["id"])
        for node in graph.get("nodes", [])
        if str(node["data"].get("label")) == "CHECKPOINT"
    ]
    queue_command(
        delete_elements_command(
            next_command_id("delete-checkpoints"),
            node_ids=node_ids,
        )
    )


def reset_graph() -> None:
    command = set_elements_command(next_command_id("reset"), initial_elements())
    st.session_state[STATE_KEY] = initial_elements()
    st.session_state[COMMANDS_KEY] = [command]
    st.session_state[LAST_COMMAND_KEY] = command
    st.session_state[NOTICE_KEY] = "Reset the Python graph and browser graph."


def clear_graph() -> None:
    queue_command(clear_graph_command(next_command_id("clear")))


def fit_graph() -> None:
    queue_command(
        viewport_command(next_command_id("fit"), "fit", padding=60),
        mutate_python_graph=False,
    )


def run_circle_layout() -> None:
    queue_command(
        viewport_command(
            next_command_id("circle-layout"),
            "run_layout",
            layout="circle",
        ),
        mutate_python_graph=False,
    )


ensure_state()
sample_file_elements = load_graph_file(str(SAMPLE_GRAPH_PATH))

render_demo_intro(
    "Data helpers and commands",
    """
    This demo covers the Python-side helper API that prepares graph data,
    validates it, mutates Python-owned element dictionaries, and sends
    incremental commands to the browser graph.
    """,
    [
        (
            "Dataframe and record conversion",
            "`records_to_dataframe(...)` and `dataframe_to_records(...)`.",
        ),
        (
            "JSON graph loading",
            "Load, validate, and inspect a Cytoscape graph dictionary from a file.",
        ),
        (
            "Element helpers",
            "`get_element(...)`, `upsert_elements(...)`, "
            "`update_element_data(...)`, and `delete_elements(...)`.",
        ),
        (
            "Validation",
            "`validate_elements(...)` and `validate_graph_commands(...)`.",
        ),
        (
            "Graph commands",
            "Add, upsert, update, delete, set, clear, fit, and run-layout commands.",
        ),
    ],
    sections=[
        (
            "Capability coverage",
            "The Python helper APIs used to prepare, validate, mutate, and command graph records.",
        ),
        (
            "Table to records to graph",
            "Table-first source records converted through dataframes into graph elements.",
        ),
        (
            "Load a graph JSON file",
            "A packaged intelligence graph loaded with `json.loads(...)` and validated before use.",
        ),
        (
            "Validation",
            "Validation examples for element dictionaries and graph command payloads.",
        ),
        (
            "Pure Python element helpers",
            "Examples for reading, upserting, updating, and deleting element dictionaries before rendering.",
        ),
        (
            "Command playground",
            "Buttons that queue add, upsert, update, delete, set, clear, fit, and layout commands.",
        ),
        (
            "Data before rendering",
            "The current Python-owned graph after helper and command mutations.",
        ),
        (
            "Executed output",
            "The live graph plus returned command and component dictionaries.",
        ),
    ],
)

st.markdown(
    """
    ## `commands.py` summary

    - Builds command dictionaries for browser updates (`add_elements`, `upsert_elements`,
      `update_data`, `delete_elements`, `set_elements`, `clear`, and viewport/layout actions).
    - Validates every command payload before it is sent so malformed IDs, bad
      endpoints, and invalid transitions fail early.
    - Applies the same command safely to Python-owned `nodes`/`edges` state with
      `apply_graph_command(s)` so Streamlit state and the browser stay in sync.
    """
)

st.markdown(
    """
    The live sections below run `records_to_dataframe`, `dataframe_to_records`,
    `validate_elements`, `validate_graph_commands`, `apply_graph_command`, and
    `apply_graph_commands`.
    """
)

records_table = records_to_dataframe(
    {"sightings": SIGHTING_RECORDS, "related_records": RELATED_RECORDS}
)
sighting_records = dataframe_to_records(
    records_table[records_table["record_group"] == "sightings"].drop(
        columns=["record_group"]
    )
)
converted_elements = build_sighting_graph(sighting_records)
drop_missing_preview = dataframe_to_records(
    records_table.head(2).drop(columns=["record_group"]),
    drop_missing=True,
)
nested_element_table = records_to_dataframe(
    converted_elements,
    group_key="element_type",
    flatten_data=False,
)

st.markdown("## Table to records to graph")
left, right = st.columns([0.55, 0.45])
with left:
    st.markdown("#### Grouped source records")
    st.dataframe(records_table, hide_index=True)
with right:
    st.markdown("#### Converted graph summary")
    st.dataframe(graph_summary_rows(converted_elements), hide_index=True)
    render_dictionary_preview(
        "Converted sighting record dictionaries",
        sighting_records[:2],
        """
        These are the first two row dictionaries after dataframe conversion.
        They remain table-shaped records before `build_sighting_graph(...)`
        turns entities and targets into graph nodes and sighting edges.
        """,
        height=240,
        expanded=False,
    )

st.markdown("#### Conversion options")
st.markdown(
    """
    `dataframe_to_records(..., drop_missing=True)` removes blank table cells
    from each returned dictionary. `records_to_dataframe(..., flatten_data=False)`
    keeps graph element `data` dictionaries nested, which is useful when you
    want to inspect or export raw Cytoscape-style records.
    """
)
options_left, options_right = st.columns([0.42, 0.58])
with options_left:
    render_dictionary_preview(
        "`drop_missing=True` record output",
        drop_missing_preview,
        """
        Missing cells from the grouped source table are omitted. This makes
        row dictionaries smaller before graph-building code reads entity,
        target, location, and time fields.
        """,
        height=240,
        expanded=False,
    )
with options_right:
    st.markdown("##### Nested graph rows with `flatten_data=False`")
    st.dataframe(nested_element_table.head(4), hide_index=True)

st.markdown("## Load A Graph JSON File")
st.markdown(
    """
    Existing graph data can be loaded from JSON when it already follows the
    `{"nodes": [...], "edges": [...]}` contract. Resolve the path from the
    application file, parse the object, and call `validate_elements(...)`
    before it reaches the browser. The packaged sample keeps vehicles,
    locations, times, people, and devices in a reusable data file.
    """
)
file_left, file_right = st.columns([0.4, 0.6])
with file_left:
    st.markdown("#### Loaded graph summary")
    st.dataframe(graph_summary_rows(sample_file_elements), hide_index=True)
with file_right:
    render_dictionary_preview(
        "Loaded JSON dictionary excerpt",
        {
            "source": SAMPLE_GRAPH_PATH.relative_to(
                SAMPLE_GRAPH_PATH.parents[1]
            ).as_posix(),
            "first_node": sample_file_elements["nodes"][0],
            "first_edge": sample_file_elements["edges"][0],
        },
        """
        This preview identifies the source file and shows one complete node and
        edge record. The entire parsed dictionary is ready to pass directly to
        `graph_workbench(...)` after validation.
        """,
        height=300,
        expanded=True,
    )

st.markdown("## Validation")
valid_column, invalid_column = st.columns(2)
with valid_column:
    try:
        validate_elements(st.session_state[STATE_KEY])
        st.success("Current graph passed `validate_elements(...)`.")
    except ElementValidationError as error:
        st.error(str(error))

with invalid_column:
    invalid_elements = copy.deepcopy(st.session_state[STATE_KEY])
    invalid_elements.setdefault("edges", []).append(
        {
            "data": {
                "id": "broken-edge",
                "label": "Related",
                "source": "ABC123",
                "target": "missing_location",
            }
        }
    )
    try:
        validate_elements(invalid_elements)
        st.success("Unexpectedly valid.")
    except ElementValidationError as error:
        st.warning(str(error))

st.markdown("## Pure Python element helpers")
helper_graph = upsert_elements(
    initial_elements(),
    nodes={
        "data": {"id": "Phone_0412", "label": "PHONE", "name": "0412 000 111"},
        "position": {"x": 610, "y": 330},
    },
)
helper_graph = update_element_data(
    helper_graph,
    "ABC123",
    {"priority": "critical"},
)
helper_graph = delete_elements(
    helper_graph,
    edge_ids="ABC123-location_1-2024-09-02 0814",
)
render_dictionary_preview(
    "Pure Python helper result dictionary",
    {
        "get_element": get_element(helper_graph, "ABC123"),
        "node_count_after_helpers": len(helper_graph["nodes"]),
        "edge_count_after_helpers": len(helper_graph["edges"]),
    },
    """
    This dictionary shows the result of Python-only graph helpers before
    anything is sent to the browser. It confirms that lookup, update, upsert,
    and delete helpers operate on the same `nodes`/`edges` contract. The delete
    example uses a single edge ID string; passing a list of IDs works too.
    """,
    height=300,
    expanded=False,
)
st.caption(
    "`update_element_data(...)` follows the same identity rule as "
    "`update_data_command(...)`: it changes properties on an existing element, "
    "but it does not rename `data.id`."
)

st.markdown("## Command playground")
st.markdown(
    """
    The buttons below build command dictionaries with the public command helper
    functions. Mutating commands are applied to Python state with
    `apply_graph_command(...)`; viewport commands are sent to the browser only.
    Command batches are validated in order, which is important when one command
    creates a node that a later edge command references.
    `update_element_data(...)` and `update_data_command(...)` change properties
    on an existing element; they do not rename `data.id`. Use delete/add or
    upsert when an element identity needs to change. If you delete a node with
    `remove_incident_edges=False`, include its connected edge IDs in the same
    command so the Python graph cannot keep dangling edge references.
    """
)
with st.container(horizontal=True):
    st.button("Add checkpoint", icon=":material/add:", on_click=add_checkpoint)
    st.button(
        "Upsert owner branch",
        icon=":material/account_tree:",
        on_click=upsert_owner_branch,
    )
    st.button("Update ABC123", icon=":material/edit:", on_click=update_main_vehicle)
    st.button(
        "Delete checkpoints", icon=":material/delete:", on_click=delete_checkpoints
    )

with st.container(horizontal=True):
    st.button("Fit graph", icon=":material/center_focus_strong:", on_click=fit_graph)
    st.button("Run circle layout", icon=":material/hub:", on_click=run_circle_layout)
    st.button("Clear graph", icon=":material/clear_all:", on_click=clear_graph)
    st.button("Reset graph", icon=":material/restart_alt:", on_click=reset_graph)

# Keep the graph at the same Streamlit position when a command adds feedback.
notice = st.empty()
if st.session_state[NOTICE_KEY]:
    notice.info(st.session_state[NOTICE_KEY])

validate_graph_commands(
    st.session_state[COMMANDS_KEY],
    elements=st.session_state[STATE_KEY],
)
preview_graph = apply_graph_commands(
    st.session_state[STATE_KEY],
    [],
)

st.markdown("## Data before rendering")
st.markdown(
    """
    The command buttons mutate this Python-owned graph before the component
    renders. The live graph below receives these records plus the latest
    command patch queued for the browser.
    """
)
render_elements_dataframe(st.session_state[STATE_KEY], "Current Python-owned graph")

event = graph_workbench(
    st.session_state[STATE_KEY],
    layout={"name": "preset", "fit": True, "padding": 60},
    node_styles=demo_node_styles(),
    edge_styles=demo_edge_styles(),
    graph_commands=st.session_state[COMMANDS_KEY],
    elements_sync="initial",
    selection_mode="multiple",
    return_selection=True,
    return_positions=True,
    search=True,
    key=COMPONENT_KEY,
    height=560,
)

st.markdown("## Executed output")
metric_row = st.container(horizontal=True)
metric_row.metric("Python nodes", len(st.session_state[STATE_KEY]["nodes"]))
metric_row.metric("Python edges", len(st.session_state[STATE_KEY]["edges"]))
metric_row.metric("Queued commands", len(st.session_state[COMMANDS_KEY]))
metric_row.metric("Preview nodes", len(preview_graph["nodes"]))

left_output, right_output = st.columns(2)
with left_output:
    render_dictionary_preview(
        "Last command sent to browser",
        st.session_state[LAST_COMMAND_KEY] or {},
        """
        This command dictionary is the last patch sent to Cytoscape. Command
        IDs prevent duplicate application, while the action and payload describe
        the add, upsert, update, delete, layout, or viewport change.
        """,
        height=320,
        expanded=True,
    )
with right_output:
    render_dictionary_preview(
        "Last component event",
        event or {},
        """
        This event dictionary comes back from the browser after selection,
        position, or command-related interaction. Use it to decide which Python
        state update or audit display should run next.
        """,
        height=320,
        expanded=True,
    )

render_source_expander(__file__)
