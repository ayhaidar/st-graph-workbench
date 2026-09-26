from pathlib import Path

import streamlit as st

from page_catalog import PAGE_CATALOG, PageGuide
from page_links import docs_url

EXAMPLES_DIR = Path(__file__).resolve().parent
ROOT_DIR = EXAMPLES_DIR.parent
LOGO_PATH = ROOT_DIR / "images" / "logo.png"
LOGO_ICON_PATH = ROOT_DIR / "images" / "logo_icon.png"
APP_ICON = str(LOGO_ICON_PATH) if LOGO_ICON_PATH.exists() else ":material/account_tree:"
SIDEBAR_LOGO_PATH = LOGO_ICON_PATH if LOGO_ICON_PATH.exists() else LOGO_PATH
DEBUG_DIR = EXAMPLES_DIR / "debug"


def page_path(relative_path: str) -> str:
    return str(EXAMPLES_DIR / relative_path)


def navigation_page(guide: PageGuide):
    page_options = {
        "title": guide.title,
        "icon": guide.icon,
        "default": guide.default,
    }
    if guide.url_path:
        page_options["url_path"] = guide.url_path
    return st.Page(page_path(guide.path), **page_options)


st.set_page_config(
    layout="wide",
    page_icon=APP_ICON,
)

if SIDEBAR_LOGO_PATH.exists():
    st.logo(
        str(SIDEBAR_LOGO_PATH),
        icon_image=APP_ICON,
        size="large",
    )

pages = {guide.path: navigation_page(guide) for guide in PAGE_CATALOG}

# --------- Debugging ---------
debug_pages = []
if DEBUG_DIR.exists():
    debug_pages = [
        st.Page(str(path), title=path.stem) for path in sorted(DEBUG_DIR.glob("*.py"))
    ]

# Register every route before choosing the links for the current view.
pg = st.navigation([*pages.values(), *debug_pages], position="hidden")
current = next(
    (guide for guide in PAGE_CATALOG if pages[guide.path].url_path == pg.url_path), None
)
area = current.area if current and current.area != "Reference" else "Tutorials"
if st.session_state.get("examples_last_route") != pg.url_path:
    st.session_state["examples_area"] = area
    st.session_state["examples_last_route"] = pg.url_path
if current and current.area != "Reference":
    st.session_state[f"examples_last_{area}"] = current.path

with st.sidebar:
    selected_area = st.segmented_control(
        "Examples",
        ["Tutorials", "Feature Lab"],
        required=True,
        key="examples_area",
    )
    if selected_area != area:
        destination = st.session_state.get(f"examples_last_{selected_area}")
        if destination is None:
            destination = next(
                guide.path for guide in PAGE_CATALOG if guide.area == selected_area
            )
        st.switch_page(pages[destination])
    section = None
    for guide in PAGE_CATALOG:
        if guide.area != selected_area:
            continue
        if guide.section != section:
            section = guide.section
            st.markdown(f"**{section}**")
        label = f"{guide.lesson}. {guide.title}" if guide.lesson else guide.title
        st.page_link(pages[guide.path], label=label, icon=guide.icon)
    st.divider()
    st.page_link(docs_url(), label="Manual", icon=":material/menu_book:")
    st.page_link(
        docs_url("reference/index.md"), label="API reference", icon=":material/code:"
    )
    with st.expander("Developer reference"):
        st.page_link(docs_url("advanced/architecture.md"), label="Architecture")
        st.page_link(docs_url("changelog.md"), label="Changelog")
        for debug_page in debug_pages:
            st.page_link(debug_page)
pg.run()
