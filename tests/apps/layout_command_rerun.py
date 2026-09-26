"""Run the real command demo with a controlled delay before rendering its graph."""

import runpy
import sys
import time
from pathlib import Path

import st_graph_workbench
import streamlit as st
from st_graph_workbench.component.component import graph_workbench

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "examples"))
st.set_page_config(layout="wide")


def delayed_graph(*args, **kwargs):
    # Let Streamlit flush the status message before the next graph delta arrives.
    if st.session_state.get("data_helpers_commands_sequence", 0):
        time.sleep(1.5)
    return graph_workbench(*args, **kwargs)


st_graph_workbench.graph_workbench = delayed_graph
runpy.run_path(str(ROOT / "examples/demos/data_helpers_commands.py"))
