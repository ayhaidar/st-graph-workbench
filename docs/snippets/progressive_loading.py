import streamlit as st

from st_graph_workbench import (
    ProgressiveLoadConfig,
    add_elements_command,
    apply_graph_command,
    graph_workbench,
    viewport_command,
)

TOTAL_RECORDS = 10_000
PAGE_SIZE = 100

st.session_state.setdefault("graph", {"nodes": [], "edges": []})
st.session_state.setdefault("loaded", 0)
st.session_state.setdefault("commands", [])
st.session_state.setdefault("command_sequence", 0)
st.session_state.setdefault("acknowledged_request_id", None)
st.session_state.setdefault("last_request_id", None)
st.session_state.setdefault("has_more", True)
st.session_state.setdefault("load_error", "")


def fetch_page(cursor: int, page_size: int) -> dict:
    """Replace this body with a database, API, or graph-store query."""
    stop = min(cursor + page_size, TOTAL_RECORDS)
    return {
        "nodes": [
            {
                "data": {
                    "id": f"vehicle-{index}",
                    "label": "VEHICLE",
                    "name": f"Vehicle {index}",
                },
                # Absolute record indices keep positions stable across pages.
                "position": {"x": (index % 20) * 80, "y": (index // 20) * 80},
            }
            for index in range(cursor, stop)
        ],
        "edges": [],
    }


def on_graph_change() -> None:
    event = st.session_state.get("fleet-graph")
    if not event or event.get("action") != "load_more":
        return

    request = event["data"]
    request_id = request.get("request_id")
    if request_id and request_id == st.session_state.last_request_id:
        return
    st.session_state.last_request_id = request_id
    st.session_state.commands = []
    st.session_state.load_error = ""
    try:
        load_page(request)
    except (OSError, ValueError, KeyError) as error:
        st.session_state.load_error = (
            f"Could not load this page: {error}. Retry Load more."
        )
    finally:
        # A handled failure completes the request, but never advances its cursor.
        st.session_state.acknowledged_request_id = request_id


def load_page(request: dict) -> None:
    cursor = int(request["cursor"])
    if cursor != st.session_state.loaded:
        return  # Ignore requests issued before the application's data changed.
    batch = fetch_page(cursor, int(request["page_size"]))
    if not batch["nodes"]:
        st.session_state.has_more = False
        return
    st.session_state.command_sequence += 1
    command = add_elements_command(
        f"page-{st.session_state.command_sequence}",
        nodes=batch["nodes"],
        edges=batch["edges"],
    )
    st.session_state.graph = apply_graph_command(st.session_state.graph, command)
    st.session_state.commands = [command]
    if st.session_state.loaded == 0:
        st.session_state.commands.append(
            viewport_command(f"first-fit-{st.session_state.command_sequence}", "fit")
        )
    st.session_state.loaded += len(batch["nodes"])
    st.session_state.has_more = st.session_state.loaded < TOTAL_RECORDS


st.markdown("## Vehicle source records")
st.markdown("The first five source records below become nodes as pages are loaded.")
st.dataframe([node["data"] for node in fetch_page(0, 5)["nodes"]], hide_index=True)
with st.container():
    if st.session_state.load_error:
        st.error(st.session_state.load_error)


progress: ProgressiveLoadConfig = {
    "cursor": st.session_state.loaded,
    "page_size": PAGE_SIZE,
    "loaded_count": st.session_state.loaded,
    "total_count": TOTAL_RECORDS,
    "has_more": st.session_state.has_more,
    "acknowledged_request_id": st.session_state.acknowledged_request_id,
}

graph_workbench(
    st.session_state.graph,
    layout={"name": "preset", "fit": False},
    graph_commands=st.session_state.commands,
    elements_sync="initial",
    progressive_loading=progress,
    performance_profile="large",
    key="fleet-graph",
    on_change=on_graph_change,
)
