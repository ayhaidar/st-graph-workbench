"""Pure command and position examples, executable without a Streamlit session."""

from copy import deepcopy
import math

from st_graph_workbench import (
    add_elements_command,
    apply_graph_command,
    clear_graph_command,
    delete_elements_command,
    records_to_dataframe,
    set_elements_command,
    update_data_command,
    upsert_elements_command,
    validate_graph_commands,
    viewport_command,
)
from tutorials.data import checkpoint, fleet_graph


def edit_report_frame(data):
    """Display only records actually returned by an edit, never infer a full graph."""
    if "elements" in data:
        records = data["elements"]
    elif "added_elements" in data:
        records = data["added_elements"]
    elif "updated_elements" in data:
        records = data["updated_elements"]
    elif data.get("operation") == "delete_selected":
        # Deletion reports IDs, not full deleted records; do not invent their fields.
        records = [
            {"record_group": group, "id": record_id, "change": "Deleted"}
            for group, field in (
                ("node", "deleted_node_ids"),
                ("edge", "deleted_edge_ids"),
            )
            for record_id in data.get(field, [])
        ]
    else:
        records = data.get("positions", [])
    frame = records_to_dataframe(records)
    return frame if not frame.empty else frame.reindex(columns=["id", "label", "name"])


def command_example(operation, command_id):
    node = {
        "data": {"id": "checkpoint", "label": "PLACE", "name": "Checkpoint"},
        "position": {"x": 650, "y": 300},
    }
    if operation == "add_elements":
        # This builder creates an instruction; it does not mutate Python data.
        return add_elements_command(command_id, nodes=node)
    if operation == "upsert_elements":
        node["data"]["name"] = "Updated checkpoint"
        return upsert_elements_command(command_id, nodes=node)
    if operation == "update_data":
        return update_data_command(command_id, "ABC123", {"name": "Vehicle ABC123"})
    if operation == "delete_elements":
        return delete_elements_command(command_id, node_ids=["checkpoint"])
    if operation == "set_elements":
        return set_elements_command(command_id, checkpoint())
    if operation == "clear":
        return clear_graph_command(command_id)
    # View instructions affect the browser camera/layout, not source relationships.
    params = {
        "fit": {"padding": 50},
        "center": {},
        "pan": {"pan": {"x": 100, "y": 80}},
        "zoom": {"level": 1.2},
        "set_viewport": {"zoom": 0.8, "pan": {"x": 120, "y": 100}},
        "set_zoom_bounds": {"min_zoom": 0.2, "max_zoom": 3},
        "run_layout": {"layout": {"name": "circle", "animate": False}},
    }
    return viewport_command(command_id, operation, **params[operation])


def queue_command(state, command):
    # Reject invalid changes before replacing the last accepted checkpoint.
    command = missing_elements_command(state["elements"], command)
    validate_graph_commands([command], elements=state["elements"])
    state["elements"] = apply_graph_command(state["elements"], command)
    # Keep the full checkpoint for remounts; send this small change to the live graph.
    state["commands"] = [command]


def missing_elements_command(elements, command):
    """Python's strict add applier rejects duplicates; filter overlapping pages."""
    if command["operation"] != "add_elements":
        return command
    known = {
        item["data"]["id"] for group in ("nodes", "edges") for item in elements[group]
    }
    return add_elements_command(
        command["command_id"],
        **{
            group: [
                item
                for item in command.get(group, [])
                if item["data"]["id"] not in known
            ]
            for group in ("nodes", "edges")
        },
    )


def next_command_id(state, prefix):
    state["sequence"] += 1
    return f"{prefix}-{state['generation']}-{state['sequence']}"


def restore_positions(elements, payload):
    """Reject an invalid snapshot atomically; ignore IDs outside this graph."""
    if not isinstance(payload, dict) or not isinstance(payload.get("positions"), list):
        raise ValueError("Expected a dictionary containing a positions list.")
    positions = {}
    for row in payload["positions"]:
        if not isinstance(row, dict) or not isinstance(row.get("position"), dict):
            raise ValueError("Each position needs an id and an x/y dictionary.")
        position = row["position"]
        if not all(
            isinstance(position.get(axis), (int, float))
            and not isinstance(position[axis], bool)
            and math.isfinite(position[axis])
            for axis in ("x", "y")
        ):
            raise ValueError("Coordinates must be finite numbers.")
        positions[str(row["id"])] = position
    # Validation is complete; copy before assigning coordinates to preserve the input.
    graph = deepcopy(elements)
    for node in graph["nodes"]:
        if str(node["data"]["id"]) in positions:
            node["position"] = deepcopy(positions[str(node["data"]["id"])])
    return graph


def loading_checkpoint():
    return fleet_graph(30)


def load_next_batch(state, request, *, outcome="Success", total=180):
    """Acknowledge every request, including stale cursors and failed reads."""
    request_id = request["request_id"]
    # Components can redeliver the same request during reruns.
    if request_id == state.get("acknowledged"):
        return
    state["commands"] = []
    state["error"] = ""
    try:
        start = state.get("loaded", 30)
        # A delayed request for a previous cursor must not advance the current page.
        if request.get("cursor") != start:
            return
        if outcome == "Fail once":
            raise OSError("Simulated data-source failure. Retry the same cursor.")
        if outcome == "Empty final batch":
            state["complete"] = True
            return
        stop = min(start + int(request.get("page_size", 30)), total)
        if stop <= start:
            state["complete"] = True
            return
        # The response deliberately overlaps earlier pages; add ignores known IDs.
        batch = fleet_graph(stop)
        command = add_elements_command(next_command_id(state, "batch"), **batch)
        queue_command(state, command)
        # Advance only after the validated merge succeeds.
        state["loaded"] = stop
        state["complete"] = stop == total
    except OSError as error:
        state["error"] = str(error)
    finally:
        # Release the browser request even on failure so it can offer an explicit retry.
        state["acknowledged"] = request_id
