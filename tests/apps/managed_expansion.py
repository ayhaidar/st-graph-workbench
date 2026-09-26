"""Independent controllers, without the tutorial's presentation layer."""

import streamlit as st
from st_graph_workbench import (
    ExpansionController,
    InMemoryExpansionProvider,
    graph_workbench,
)

st.set_page_config(layout="wide")
source = {
    "nodes": [
        {"data": {"id": i}, "position": {"x": x, "y": 160}}
        for i, x in [("root", 160), ("child", 380)]
    ],
    "edges": [{"data": {"id": "link", "source": "root", "target": "child"}}],
}
provider = InMemoryExpansionProvider(source)


def instance(key):
    state = st.session_state.setdefault(
        key + "_state",
        {
            "controller": ExpansionController(
                {"nodes": source["nodes"][:1], "edges": []}
            ),
            "commands": [],
        },
    )
    controller = state["controller"]

    def receive():
        before = controller.view()
        controller.handle_event(st.session_state.get(key), provider)
        state["commands"] = controller.commands(before)

    graph_workbench(
        controller.view(),
        expansion=controller.describe(provider),
        elements_sync="initial",
        graph_commands=state["commands"],
        key=key,
        on_change=receive,
        height=400,
        layout={"name": "preset", "fit": False},
    )


instance("first")
instance("second")
