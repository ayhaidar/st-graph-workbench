"""A task-oriented finder for the existing interactive playgrounds."""

import streamlit as st
from page_catalog import LAB_PAGES

st.title("Feature finder")
st.markdown(
    "Choose a playground to experiment with a particular capability. Each example includes source records, working controls, and explained results."
)
st.markdown("### On this page")
st.markdown("- Find a feature\n- Open its working example")
query = (
    st.text_input(
        "Find a feature",
        placeholder="Search, layouts, CRUD, icons...",
        icon=":material/search:",
    )
    .casefold()
    .strip()
)
matches = [
    guide
    for guide in LAB_PAGES
    if guide.path != "demos/demo_overview.py"
    and query
    in f"{guide.title} {guide.summary} {guide.api} {guide.contents}".casefold()
]
if not matches:
    st.info("No matching playgrounds.")
for guide in matches:
    st.page_link(guide.path, label=guide.title, icon=guide.icon)
    st.caption(guide.summary)
