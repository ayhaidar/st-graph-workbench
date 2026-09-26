"""Experiment with the same managed expansion workflow taught in lesson 9."""

import streamlit as st
from expansion_data import expansion_source
from expansion_workflow import render_expansion_workflow
from tutorials.common import show_graph_data

st.title("Branch exploration")
st.markdown(
    "Explore independent branches, shared records, scoped analysis, and reproducible graph views."
)
st.markdown("### On this page")
st.markdown(
    "- Source data\n- Code and working graph\n- Data and practical result\n- Search, edits, and exploration snapshots"
)
state = st.session_state.setdefault("branch_lab_state", {"commands": [], "event": None})
show_graph_data(expansion_source())
render_expansion_workflow(state, "branch_lab_graph")
st.header("Common mistakes and conclusion")
st.markdown(
    "Collapse changes the view, not the source. Keep analysis scope explicit, preserve provider versions, and retry failed pages without advancing their cursors. Shared branches and cached snapshots make exploration reversible."
)
