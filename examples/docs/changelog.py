import re
from pathlib import Path

import streamlit as st

from page_overview import render_page_overview

ROOT_DIR = Path(__file__).resolve().parents[2]

changelog = (ROOT_DIR / "CHANGELOG.md").read_text(encoding="utf-8")

changelog = re.sub(r"(\n##) (.+)", r"\n---\n \1 :blue[\2]", changelog)
changelog = changelog.replace("##", "####").replace("# Changelog", "")

st.markdown("## Changelog")
render_page_overview(
    [
        (
            "Release entries",
            "Versioned changes, fixes, and additions in chronological documentation form.",
        ),
        (
            "Upgrade notes",
            "Compatibility details and behavioral changes to check when updating.",
        ),
        (
            "Feature trail",
            "A quick history of component capabilities as they were added.",
        ),
    ],
    description="This overview frames the changelog before the release notes.",
)
st.markdown(changelog, unsafe_allow_html=False)
