"""Lesson presentation and isolated, non-widget session state."""

from copy import deepcopy
import ast
from contextlib import nullcontext
import inspect
from pathlib import Path
import textwrap

import streamlit as st

from demos.demo_helpers import render_dictionary_preview
from st_graph_workbench import records_to_dataframe
from tutorials.data import checkpoint


def example_source(source, line):
    """Extract an executing with-block, including its leading teaching comments."""
    block = next(
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.With) and node.lineno == line
    )
    lines = source.splitlines()
    start = block.body[0].lineno - 1
    # AST statement locations skip comments between the with header and first line.
    while start > block.lineno and (
        not lines[start - 1].strip() or lines[start - 1].lstrip().startswith("#")
    ):
        start -= 1
    return textwrap.dedent("\n".join(lines[start : block.body[-1].end_lineno]))


def show_example(path):
    """Display the executing block before mounting components below it.

    Render source first so inserting a code block never shifts a live canvas.
    """
    frame = inspect.currentframe()
    try:
        line = frame.f_back.f_lineno
    finally:
        del frame
    source = Path(path).read_text(encoding="utf-8")
    st.code(example_source(source, line), language="python", wrap_lines=True)
    return nullcontext()


def show_function(function, description):
    """Show the actual helper used by a lesson, not a separately maintained copy."""
    st.markdown(description)
    source = textwrap.dedent(inspect.getsource(inspect.unwrap(function)))
    st.code(
        source,
        language="python",
        wrap_lines=True,
        height=360 if len(source.splitlines()) > 24 else "content",
    )


def state_key(number):
    return f"tutorial_{number:02}_state"


def lesson_state(number, factory=checkpoint):
    key = state_key(number)
    if key not in st.session_state:
        st.session_state[key] = {
            "elements": factory(),
            "event": None,
            "selection": {},
            "commands": [],
            "sequence": 0,
            "generation": 0,
        }
    return st.session_state[key]


def component_key(number, instance="graph"):
    state = lesson_state(number)
    return f"tutorial_{number:02}_{instance}_{state['generation']}"


def reset_lesson(number, factory):
    previous = lesson_state(number)
    generation = previous["generation"] + 1
    del st.session_state[state_key(number)]
    state = lesson_state(number, factory)
    state["generation"] = generation
    for key in list(st.session_state):
        if key.startswith(f"tutorial_{number:02}_widget_"):
            del st.session_state[key]


def begin_lesson(number, factory=checkpoint, *, contents=None):
    from page_catalog import TUTORIAL_PAGES

    guide = TUTORIAL_PAGES[number - 1]
    state = lesson_state(number, factory)
    st.caption(f"{guide.section} / Lesson {number} of {len(TUTORIAL_PAGES)}")
    st.title(guide.title)
    st.markdown(guide.summary)
    st.subheader("Learning objectives")
    st.markdown("By the end of this lesson, you will be able to:")
    st.markdown("\n".join(f"- {target}" for target in guide.learning_objectives))
    st.markdown("### On this page")
    st.markdown(
        "\n".join(
            f"- {heading}"
            for heading in contents
            or (
                "Source data",
                "Code and working graph",
                "How this example works",
                "Try it and check the result",
                "Code in practice",
                "Data and practical result",
                "Common mistakes and next step",
            )
        )
    )
    st.button(
        "Reset lesson",
        icon=":material/restart_alt:",
        key=f"tutorial_{number:02}_reset",
        on_click=reset_lesson,
        args=(number, factory),
    )
    return state


def show_workflow_comparison(number):
    """Keep the two mutation lessons explicit about authority and useful scenarios."""
    st.subheader("CRUD or browser editing?")
    st.markdown("""
**Validated application changes (CRUD):** request, Python dialog, validation,
then an accepted change to Python records and the graph. A cancelled or invalid
request leaves both unchanged. The example uses session state, not a database.

**Immediate browser edits:** change the graph first, then receive an `edit`
event in Python. The browser-editing lesson displays that report without accepting its records
into the Python checkpoint. Undo/redo belongs to the browser, not a database.

**Where each workflow is useful**

- **Observations and evidence:** use CRUD to record a confirmed vehicle sighting
  with the right location and time. Use browser editing to sketch a possible
  connection during review without treating it as confirmed evidence.
- **Service dependencies:** use CRUD to maintain an approved inventory of
  services and relationships. Use browser editing to try a proposed dependency,
  remove it, or undo it during a design discussion.
- **Processes and knowledge graphs:** use CRUD to validate a published step or
  relationship. Use browser editing to explore alternative flows in a workshop
  before deciding which changes belong in the maintained dataset.

**Using both together:** let users draft locally, review the returned records,
assign domain types, then explicitly validate and save accepted changes in
Python. These lessons do not implement automatic draft promotion or database
saving. Styling a node as a draft is a visual convention, not a permission rule.
""")
    st.page_link(
        "tutorials/editing.py" if number == 10 else "tutorials/crud.py",
        label="Compare with immediate browser edits"
        if number == 10
        else "Compare with validated CRUD changes",
        icon=":material/compare_arrows:",
    )


def show_graph_data(
    elements,
    description="These are the Python-owned nodes and relationships used below.",
):
    st.header("Source data")
    st.markdown(description)
    st.dataframe(records_to_dataframe(elements), hide_index=True, height=240)
    st.caption(f"{len(elements['nodes'])} nodes / {len(elements['edges'])} edges")
    st.markdown(
        "**Reading the records.** `record_group` distinguishes nodes from edges. "
        "`id` identifies a record; `label` groups records "
        "for styling; `name` is display text. Edge rows also have `source` and "
        "`target`, which refer to node IDs. Blank cells can be expected when "
        "nodes and edges do not share the same properties. This table shows "
        "Python data, not a live export of browser-only edits."
    )


def receive_event(number, instance="graph"):
    """Keep useful results beyond widget cleanup when leaving a lesson."""
    state = lesson_state(number)
    event = st.session_state.get(component_key(number, instance))
    if not isinstance(event, dict) or event == state.get(f"event_{instance}"):
        return None
    # Copy results out of widget state so later selection events cannot erase them.
    state[f"event_{instance}"] = deepcopy(event)
    state["event"] = deepcopy(event)
    state.setdefault("results", {})[event.get("action")] = deepcopy(event)
    state.setdefault(f"results_{instance}", {})[event.get("action")] = deepcopy(event)
    data = event.get("data", {})
    if event.get("action") == "selection":
        state["selection"] = deepcopy(data)
    if event.get("action") == "positions":
        positions = {row["id"]: row["position"] for row in data.get("positions", [])}
        for node in state["elements"]["nodes"]:
            if node["data"]["id"] in positions:
                node["position"] = deepcopy(positions[node["data"]["id"]])
    return event


def show_result(payload, description, title="Data and practical result", *, label):
    """Label inputs, helper results, saved state, and component events explicitly."""
    st.header(title)
    render_dictionary_preview(label, payload, description, height=280)


def finish_lesson(number, path, *, mistakes, conclusion):
    from page_catalog import TUTORIAL_PAGES
    from page_links import docs_url

    guide = TUTORIAL_PAGES[number - 1]
    st.header("Common mistakes and next step")
    st.markdown(mistakes)
    st.markdown(f"**Conclusion.** {conclusion}")
    with st.expander("Check your understanding", icon=":material/checklist:"):
        st.markdown(
            "Use the source data, executing examples, and results above to explain each outcome:"
        )
        st.markdown("\n".join(f"- {target}" for target in guide.learning_objectives))
    st.markdown(f"[Guide and API details]({docs_url(guide.manual)})")
    st.page_link(
        guide.lab, label="Explore the related Feature Lab", icon=":material/science:"
    )
    with st.expander("Complete lesson source", icon=":material/code:"):
        st.code(Path(path).read_text(encoding="utf-8"), language="python")
        st.caption(
            "Run through examples/app.py; shared lesson and dataset helpers are in examples/tutorials/."
        )
    with st.container(horizontal=True):
        if number > 1:
            st.page_link(
                TUTORIAL_PAGES[number - 2].path,
                label="Previous lesson",
                icon=":material/arrow_back:",
            )
        if number < len(TUTORIAL_PAGES):
            st.page_link(
                TUTORIAL_PAGES[number].path,
                label="Next lesson",
                icon=":material/arrow_forward:",
            )
