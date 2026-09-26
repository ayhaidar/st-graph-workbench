import json

import streamlit as st

from demos.demo_helpers import (
    capability_rows,
    render_capability_summary,
    render_dictionary_preview,
    render_elements_dataframe,
    render_source_expander,
)
from page_overview import render_page_overview
from st_graph_workbench import (
    EdgeStyle,
    NodeStyle,
    apply_graph_command,
    delete_elements_command,
    graph_workbench,
    set_elements_command,
    update_data_command,
    upsert_elements_command,
)

st.markdown("# Interactive CRUD / Data Loading")
st.markdown(
    """
    This demo keeps the graph in `st.session_state`. Cytoscape emits CRUD
    intent events, then Python opens a Streamlit dialog and sends a small graph
    command back to the existing browser graph instead of resending the full
    elements document after every edit.
    """
)

render_page_overview(
    [
        (
            "Capability coverage",
            "The CRUD, command, helper, and validation features covered by the demo.",
        ),
        (
            "Python-owned state",
            "The session-state graph, queued command list, active dialog state, and reset flow.",
        ),
        (
            "Data before rendering",
            "The current session-state graph that CRUD dialogs will mutate.",
        ),
        (
            "Dialog-driven CRUD",
            "Create, read, update, delete, and load-related dialogs opened from graph events.",
        ),
        (
            "Interactive graph",
            "The live component using `elements_sync='initial'` plus incremental graph commands.",
        ),
        (
            "Try these checks",
            "Actions that add nodes, add edges, update JSON data, delete records, and load related data.",
        ),
        (
            "Returned dictionaries",
            "The latest CRUD intent payload returned to Python from the browser.",
        ),
    ],
    description="This CRUD overview shows how the page is structured before the dialogs and graph.",
)

render_capability_summary(
    "What this demo covers",
    [
        row
        for row in capability_rows()
        if row["capability"]
        in {
            "CRUD intents",
            "Incremental browser updates",
            "Python element helpers",
            "Validation",
        }
    ],
    description="The graph-state and CRUD features demonstrated on this page.",
)

STATE_KEY = "crud_demo_elements"
ACTIVE_DIALOG_KEY = "crud_demo_active_dialog"
DIALOG_EVENT_KEY = "crud_demo_dialog_event"
LAST_EVENT_TS_KEY = "crud_demo_last_event_timestamp"
NOTICE_KEY = "crud_demo_notice"
COMMANDS_KEY = "crud_demo_graph_commands"
COMMAND_SEQ_KEY = "crud_demo_graph_command_seq"
COMPONENT_KEY = "interactive_crud_graph"
STATE_VERSION_KEY = "crud_demo_state_version"
STATE_VERSION = 2


def initial_elements():
    return {
        "nodes": [
            {
                "data": {
                    "id": "case",
                    "label": "CASE",
                    "name": "Case 73",
                    "status": "Open",
                },
                "position": {"x": 80, "y": 170},
            },
            {
                "data": {
                    "id": "vehicle",
                    "label": "MAIN_VEHICLE",
                    "name": "ABC123",
                    "risk": 8,
                },
                "position": {"x": 260, "y": 170},
            },
            {
                "data": {
                    "id": "maya",
                    "label": "PERSON",
                    "name": "Maya Reed",
                    "role": "Registered owner",
                },
                "position": {"x": 260, "y": 320},
            },
        ],
        "edges": [
            {
                "data": {
                    "id": "case-vehicle",
                    "label": "INVESTIGATES",
                    "source": "case",
                    "target": "vehicle",
                }
            },
            {
                "data": {
                    "id": "vehicle-maya",
                    "label": "REGISTERED_TO",
                    "source": "vehicle",
                    "target": "maya",
                }
            },
        ],
    }


RELATED_DATA = {
    "vehicle": {
        "nodes": [
            {
                "data": {
                    "id": "checkpoint",
                    "label": "LOCATION",
                    "name": "Harbor Camera 4",
                    "camera_id": "CAM-HARBOR-04",
                },
                "position": {"x": 470, "y": 90},
            },
            {
                "data": {
                    "id": "time_window",
                    "label": "TIME",
                    "name": "02 Sep 2024 08:14",
                    "observed_at": "2024-09-02 08:14",
                    "risk": 8,
                },
                "position": {"x": 470, "y": 250},
            },
        ],
        "edges": [
            {
                "data": {
                    "id": "vehicle-checkpoint",
                    "label": "SEEN_AT",
                    "source": "vehicle",
                    "target": "checkpoint",
                }
            },
            {
                "data": {
                    "id": "vehicle-time",
                    "label": "OBSERVED_DURING",
                    "source": "vehicle",
                    "target": "time_window",
                }
            },
        ],
    },
    "maya": {
        "nodes": [
            {
                "data": {
                    "id": "phone",
                    "label": "DEVICE",
                    "name": "Phone 0412",
                    "risk": 9,
                },
                "position": {"x": 680, "y": 170},
            }
        ],
        "edges": [
            {
                "data": {
                    "id": "maya-phone",
                    "label": "USES",
                    "source": "maya",
                    "target": "phone",
                }
            }
        ],
    },
}


def ensure_state():
    if st.session_state.get(STATE_VERSION_KEY) != STATE_VERSION:
        st.session_state[STATE_KEY] = initial_elements()
        st.session_state[ACTIVE_DIALOG_KEY] = None
        st.session_state[DIALOG_EVENT_KEY] = None
        st.session_state[LAST_EVENT_TS_KEY] = None
        st.session_state[NOTICE_KEY] = ""
        st.session_state[COMMANDS_KEY] = []
        st.session_state[COMMAND_SEQ_KEY] = 0
        st.session_state[STATE_VERSION_KEY] = STATE_VERSION
        return

    st.session_state.setdefault(STATE_KEY, initial_elements())
    st.session_state.setdefault(ACTIVE_DIALOG_KEY, None)
    st.session_state.setdefault(DIALOG_EVENT_KEY, None)
    st.session_state.setdefault(LAST_EVENT_TS_KEY, None)
    st.session_state.setdefault(NOTICE_KEY, "")
    st.session_state.setdefault(COMMANDS_KEY, [])
    st.session_state.setdefault(COMMAND_SEQ_KEY, 0)


def clear_dialog() -> None:
    st.session_state[ACTIVE_DIALOG_KEY] = None
    st.session_state[DIALOG_EVENT_KEY] = None


def next_command_id(prefix: str) -> str:
    st.session_state[COMMAND_SEQ_KEY] += 1
    return f"{prefix}-{st.session_state[COMMAND_SEQ_KEY]}"


def queue_graph_command(command) -> None:
    st.session_state[STATE_KEY] = apply_graph_command(
        st.session_state[STATE_KEY], command
    )
    st.session_state[COMMANDS_KEY] = [command]


def load_related(node_id):
    related = RELATED_DATA.get(node_id)
    if not related:
        st.session_state[NOTICE_KEY] = f"No extra demo data for `{node_id}`."
        return

    command = upsert_elements_command(
        next_command_id(f"load-{node_id}"),
        nodes=related["nodes"],
        edges=related["edges"],
    )
    queue_graph_command(command)
    st.session_state[NOTICE_KEY] = (
        f"Loaded {len(related['nodes'])} node(s) and "
        f"{len(related['edges'])} edge(s) for `{node_id}`."
    )


def handle_graph_event():
    event = st.session_state.get(COMPONENT_KEY)
    if not event or event.get("action") != "crud":
        return

    timestamp = event.get("timestamp")
    if timestamp == st.session_state.get(LAST_EVENT_TS_KEY):
        return

    data = event.get("data", {})
    operation = data.get("operation")
    if operation not in {
        "create_node",
        "create_edge",
        "read_selected",
        "update_selected",
        "delete_selected",
        "request_node_data",
    }:
        return

    st.session_state[LAST_EVENT_TS_KEY] = timestamp
    st.session_state[ACTIVE_DIALOG_KEY] = operation
    st.session_state[DIALOG_EVENT_KEY] = event


def node_ids():
    return [node["data"]["id"] for node in st.session_state[STATE_KEY]["nodes"]]


def element_ids():
    return {
        element["data"]["id"]
        for group in ("nodes", "edges")
        for element in st.session_state[STATE_KEY][group]
    }


def node_option_label(node_id):
    for node in st.session_state[STATE_KEY]["nodes"]:
        if node["data"]["id"] == node_id:
            name = node["data"].get("name", node_id)
            label = node["data"].get("label", "NODE")
            return f"{name} [{label}] ({node_id})"
    return str(node_id)


def selected_name(event):
    selected = event.get("data", {}).get("selected_elements", [])
    if not selected:
        return "selected element"
    data = selected[0].get("data", {})
    return data.get("name") or data.get("id") or selected[0].get("id")


@st.dialog("Add node", on_dismiss=clear_dialog)
def create_node_dialog(event):
    data = event.get("data", {})
    suggested_position = data.get("suggested_position", {"x": 360, "y": 220})

    with st.form("crud_create_node_form"):
        new_id = st.text_input("Node ID", value="new-location")
        label = st.selectbox(
            "Label",
            ["LOCATION", "VEHICLE", "PERSON", "TIME", "DOCUMENT", "DEVICE"],
        )
        name = st.text_input("Name", value="New location")
        raw_properties = st.text_area(
            "Additional properties (JSON object)",
            value='{"status": "New"}',
            height=120,
            help="Optional domain fields merged into the node data dictionary.",
        )
        submitted = st.form_submit_button("Create node")
        cancelled = st.form_submit_button("Cancel")

    if cancelled:
        clear_dialog()
        st.rerun()

    if submitted:
        try:
            new_id = new_id.strip()
            if not new_id:
                raise ValueError("Node ID cannot be empty.")
            if new_id in element_ids():
                raise ValueError(f"Element ID `{new_id}` already exists.")
            properties = json.loads(raw_properties or "{}")
            if not isinstance(properties, dict):
                raise ValueError("Additional properties must be a JSON object.")
            node_data = {**properties, "id": new_id, "label": label, "name": name}
            command = upsert_elements_command(
                next_command_id("create-node"),
                nodes={"data": node_data, "position": suggested_position},
            )
            queue_graph_command(command)
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            st.error(str(error))
            return
        st.session_state[NOTICE_KEY] = f"Created node `{new_id}`."
        clear_dialog()
        st.rerun()


@st.dialog("Add edge", on_dismiss=clear_dialog)
def create_edge_dialog(event):
    selected_nodes = event.get("data", {}).get("selected_node_ids", [])
    options = node_ids()
    source_default = selected_nodes[0] if selected_nodes else options[0]
    target_default = (
        selected_nodes[1]
        if len(selected_nodes) > 1
        else next(
            (node_id for node_id in options if node_id != source_default), options[0]
        )
    )

    with st.form("crud_create_edge_form"):
        edge_id = st.text_input("Edge ID", value="new-edge")
        label = st.text_input("Label", value="RELATED_TO")
        source = st.selectbox(
            "Source",
            options,
            index=options.index(source_default),
            format_func=node_option_label,
        )
        target = st.selectbox(
            "Target",
            options,
            index=options.index(target_default),
            format_func=node_option_label,
        )
        raw_properties = st.text_area(
            "Additional properties (JSON object)",
            value='{"confidence": 0.8}',
            height=120,
        )
        submitted = st.form_submit_button("Create edge")
        cancelled = st.form_submit_button("Cancel")

    if cancelled:
        clear_dialog()
        st.rerun()

    if submitted:
        try:
            edge_id = edge_id.strip()
            if not edge_id:
                raise ValueError("Edge ID cannot be empty.")
            if edge_id in element_ids():
                raise ValueError(f"Element ID `{edge_id}` already exists.")
            properties = json.loads(raw_properties or "{}")
            if not isinstance(properties, dict):
                raise ValueError("Additional properties must be a JSON object.")
            edge_data = {
                **properties,
                "id": edge_id,
                "label": label,
                "source": source,
                "target": target,
            }
            command = upsert_elements_command(
                next_command_id("create-edge"),
                edges={"data": edge_data},
            )
            queue_graph_command(command)
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            st.error(str(error))
            return
        st.session_state[NOTICE_KEY] = f"Created edge `{edge_id}`."
        clear_dialog()
        st.rerun()


@st.dialog("Read selected", width="large", on_dismiss=clear_dialog)
def read_selected_dialog(event):
    data = event.get("data", {})
    render_dictionary_preview(
        "Selected graph context dictionary",
        {
            "operation": data.get("operation"),
            "selected_node_ids": data.get("selected_node_ids", []),
            "selected_edge_ids": data.get("selected_edge_ids", []),
            "connected_node_ids": data.get("connected_node_ids", []),
            "connected_edge_ids": data.get("connected_edge_ids", []),
            "last_selected": data.get("last_selected"),
            "selected_elements": data.get("selected_elements", []),
            "connected_elements": data.get("connected_elements", []),
            "suggested_position": data.get("suggested_position"),
        },
        """
        This read-only dictionary is returned by the browser for the current
        selection. ID lists are useful for Python-side commands, while
        `selected_elements` and `connected_elements` preserve the graph records
        needed for inspection, export, or screenshots.
        """,
        height=360,
        expanded=True,
    )
    if st.button("Close", key="crud_read_close"):
        clear_dialog()
        st.rerun()


@st.dialog("Update selected", width="large", on_dismiss=clear_dialog)
def update_selected_dialog(event):
    selected = event.get("data", {}).get("selected_elements", [])
    if not selected:
        st.warning("No selected element was returned with this CRUD event.")
        if st.button("Close", key="crud_update_empty_close"):
            clear_dialog()
            st.rerun()
        return

    selected_element = selected[0]
    with st.form("crud_update_form"):
        raw_data = st.text_area(
            "Element data JSON",
            value=json.dumps(selected_element["data"], indent=2),
            height=220,
        )
        submitted = st.form_submit_button("Update element")
        cancelled = st.form_submit_button("Cancel")

    if cancelled:
        clear_dialog()
        st.rerun()

    if submitted:
        try:
            data = json.loads(raw_data)
            if not isinstance(data, dict):
                raise ValueError("Element data must be a JSON object.")
            if data.get("id") != selected_element["id"]:
                raise ValueError("An element ID cannot be changed during update.")
            if "source" in data or "target" in data:
                known_nodes = set(node_ids())
                if data.get("source") not in known_nodes:
                    raise ValueError("The edge source must reference an existing node.")
                if data.get("target") not in known_nodes:
                    raise ValueError("The edge target must reference an existing node.")
            command = update_data_command(
                next_command_id("update-data"),
                selected_element["id"],
                data,
                merge=False,
            )
            queue_graph_command(command)
        except (TypeError, ValueError, KeyError) as error:
            st.error(str(error))
            return
        st.session_state[NOTICE_KEY] = f"Updated `{selected_element['id']}`."
        clear_dialog()
        st.rerun()


@st.dialog("Delete selected", on_dismiss=clear_dialog)
def delete_selected_dialog(event):
    data = event.get("data", {})
    node_ids_to_delete = data.get("selected_node_ids", [])
    edge_ids_to_delete = data.get("selected_edge_ids", [])

    st.warning(
        "This removes selected nodes, selected edges, and incident edges "
        "from the Python session graph."
    )
    render_dictionary_preview(
        "Delete confirmation dictionary",
        {
            "node_ids": node_ids_to_delete,
            "edge_ids": edge_ids_to_delete,
        },
        """
        This dictionary lists exactly which node and edge IDs Python will send
        in the delete command if the analyst confirms the dialog.
        """,
        height=220,
        expanded=True,
    )

    with st.form("crud_delete_form"):
        submitted = st.form_submit_button("Confirm delete selected elements")
        cancelled = st.form_submit_button("Cancel")

    if cancelled:
        clear_dialog()
        st.rerun()

    if submitted:
        command = delete_elements_command(
            next_command_id("delete-elements"),
            node_ids=node_ids_to_delete,
            edge_ids=edge_ids_to_delete,
        )
        queue_graph_command(command)
        st.session_state[NOTICE_KEY] = "Deleted selected graph element(s)."
        clear_dialog()
        st.rerun()


@st.dialog("Load related data", on_dismiss=clear_dialog)
def load_related_dialog(event):
    data = event.get("data", {})
    selected_node_ids = data.get("selected_node_ids", [])
    node_id = selected_node_ids[0] if selected_node_ids else None

    if not node_id:
        st.warning("No selected node was returned with this CRUD event.")
        if st.button("Close", key="crud_load_empty_close"):
            clear_dialog()
            st.rerun()
        return

    st.markdown(f"Load related demo data for `{selected_name(event)}`?")
    related = RELATED_DATA.get(node_id)
    if related:
        render_dictionary_preview(
            "Related data load dictionary",
            {
                "node_id": node_id,
                "new_nodes": [node["data"]["id"] for node in related["nodes"]],
                "new_edges": [edge["data"]["id"] for edge in related["edges"]],
            },
            """
            This dictionary previews the related records that Python will merge
            into the session graph and send to the browser as a graph command.
            """,
            height=260,
            expanded=True,
        )
    else:
        st.info(f"No extra demo data is configured for `{node_id}`.")

    with st.form("crud_load_related_form"):
        submitted = st.form_submit_button("Load related data")
        cancelled = st.form_submit_button("Cancel")

    if cancelled:
        clear_dialog()
        st.rerun()

    if submitted:
        load_related(node_id)
        clear_dialog()
        st.rerun()


def render_active_dialog():
    event = st.session_state.get(DIALOG_EVENT_KEY)
    operation = st.session_state.get(ACTIVE_DIALOG_KEY)
    if not event or not operation:
        return

    if operation == "create_node":
        create_node_dialog(event)
    elif operation == "create_edge":
        create_edge_dialog(event)
    elif operation == "read_selected":
        read_selected_dialog(event)
    elif operation == "update_selected":
        update_selected_dialog(event)
    elif operation == "delete_selected":
        delete_selected_dialog(event)
    elif operation == "request_node_data":
        load_related_dialog(event)


ensure_state()

if st.button("Reset demo graph"):
    command = set_elements_command(next_command_id("reset"), initial_elements())
    queue_graph_command(command)
    clear_dialog()
    st.session_state[NOTICE_KEY] = ""
    st.rerun()

if st.session_state[NOTICE_KEY]:
    st.info(st.session_state[NOTICE_KEY])

render_active_dialog()

node_styles = [
    NodeStyle("CASE", "#3D405B", "name", "folder"),
    NodeStyle("MAIN_VEHICLE", "#2A629A", "name", "directions_car"),
    NodeStyle("PERSON", "#FF7F3E", "name", "person"),
    NodeStyle("LOCATION", "#2D936C", "name", "place"),
    NodeStyle("TIME", "#8A5A44", "name", "schedule"),
    NodeStyle("DOCUMENT", "#8A5A44", "name", "description"),
    NodeStyle("DEVICE", "#4F6F52", "name", "smartphone"),
]

edge_styles = [
    EdgeStyle("INVESTIGATES", "#3D405B", "label", directed=True),
    EdgeStyle("REGISTERED_TO", "#2A629A", "label", directed=True),
    EdgeStyle("SEEN_AT", "#2D936C", "label", directed=True),
    EdgeStyle("OBSERVED_DURING", "#D72638", "label", directed=True),
    EdgeStyle("USES", "#4F6F52", "label", directed=True),
    EdgeStyle("RELATED_TO", "#5F5AA2", "label", directed=True),
]

st.markdown("## Data before rendering")
st.markdown(
    """
    The CRUD graph starts from this Python-owned dataframe. Dialog actions
    mutate `st.session_state`, queue a graph command, and keep the browser
    canvas synchronized with these records.
    """
)
render_elements_dataframe(st.session_state[STATE_KEY], "Current CRUD graph records")

value = graph_workbench(
    st.session_state[STATE_KEY],
    layout={"name": "preset", "fit": True, "padding": 50},
    node_styles=node_styles,
    edge_styles=edge_styles,
    selection_mode="multiple",
    crud_actions=[
        "create_node",
        "create_edge",
        "read_selected",
        "update_selected",
        "delete_selected",
        "request_node_data",
    ],
    graph_commands=st.session_state[COMMANDS_KEY],
    elements_sync="initial",
    key=COMPONENT_KEY,
    on_change=handle_graph_event,
    height=560,
)

st.markdown("## Try These Checks")
st.markdown(
    """
    - Select `ABC123`, open `Data`, click `Load Related Data`, and
      confirm the Streamlit dialog.
    - Select any node and click `Read Selected` to inspect selected and connected
      elements in a read-only dialog.
    - Click `Add Node` to open a dialog, then create a new node.
    - Select a node, click `Add Edge`, and connect it to another visible node.
    - Select one element, click `Update Selected`, and edit its JSON data in the
      dialog.
    - Select elements, click `Delete Selected`, and confirm the Python-side
      deletion in the dialog.
    """
)

render_dictionary_preview(
    "Returned CRUD component value",
    value or {},
    """
    This dictionary is the latest browser event from the graph. CRUD actions
    return an `operation`, selected IDs, selected records, and connected context
    so Streamlit can open the correct dialog.
    """,
    height=360,
    expanded=True,
)

st.markdown("## What The JavaScript Is Doing")
st.markdown(
    """
    Cytoscape tracks the selected nodes and edges in the browser. CRUD buttons
    package that selection into an event and send it to Streamlit. Python opens
    a dialog, updates the authoritative `st.session_state` graph, and sends a
    small `graph_commands` payload such as `upsert_elements` or
    `delete_elements`. The component applies unseen command IDs directly to the
    existing Cytoscape instance with `cy.batch(...)`.
    """
)


render_source_expander(__file__)
