"""Stable-layout fixture for loading completion, failure, and stale responses."""

import streamlit as st

from st_graph_workbench import (
    add_elements_command,
    apply_graph_command,
    graph_workbench,
)

st.session_state.setdefault("graph", {"nodes": [{"data": {"id": "root"}}], "edges": []})
st.session_state.setdefault("ack", None)
st.session_state.setdefault("request", {})
st.session_state.setdefault("attempts", 0)
st.session_state.setdefault("cursor", 0)
st.session_state.setdefault("has_more", True)
st.session_state.setdefault("commands", [])
st.session_state.setdefault("status", "Ready")


def on_change():
    event = st.session_state.get("fixture") or {}
    if event.get("action") != "load_more":
        return
    request = event["data"]
    if request["request_id"] == st.session_state.request.get("request_id"):
        return
    st.session_state.request = request
    st.session_state.attempts += 1
    st.session_state.commands = []
    mode = st.session_state.mode
    if mode == "Deferred":
        st.session_state.status = "Waiting for response"
        return
    try:
        if mode == "Failure":
            raise OSError("Source unavailable")
        if mode == "Empty":
            st.session_state.has_more = False
        elif mode == "Duplicate":
            # An application filters already-known records before issuing adds.
            st.session_state.cursor += 1
        else:
            node_id = str(st.session_state.attempts)
            command = add_elements_command(
                f"batch-{st.session_state.attempts}",
                nodes=[{"data": {"id": node_id}, "position": {"x": 100, "y": 100}}],
            )
            st.session_state.graph = apply_graph_command(
                st.session_state.graph, command
            )
            st.session_state.commands = [command]
            st.session_state.cursor += 1
        st.session_state.status = "Completed"
    except OSError as error:
        st.session_state.status = str(error)
    finally:
        st.session_state.ack = request["request_id"]


st.selectbox(
    "Response", ["Failure", "Success", "Deferred", "Empty", "Duplicate"], key="mode"
)
st.button("Rerun unchanged")
if st.button("Send stale acknowledgment"):
    st.session_state.ack = "old-request"
if st.button("Complete pending request"):
    st.session_state.ack = st.session_state.request.get("request_id")
    st.session_state.status = "Completed"
st.metric("Attempts", st.session_state.attempts)
st.write(st.session_state.status)
graph_workbench(
    st.session_state.graph,
    key="fixture",
    layout={"name": "preset", "fit": False},
    graph_commands=st.session_state.commands,
    elements_sync="initial",
    progressive_loading={
        "cursor": st.session_state.cursor,
        "loaded_count": len(st.session_state.graph["nodes"]),
        "has_more": st.session_state.has_more,
        "acknowledged_request_id": st.session_state.ack,
    },
    on_change=on_change,
)
