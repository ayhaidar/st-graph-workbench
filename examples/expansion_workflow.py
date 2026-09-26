"""The same executable exploration workflow serves Tutorials and Feature Lab."""

import json
from pathlib import Path
from uuid import uuid4
import streamlit as st
from demos.demo_helpers import demo_node_styles, render_dictionary_preview
from expansion_data import ExampleExpansionProvider, expansion_source, expansion_start
from st_graph_workbench import (
    ExpansionConfig,
    ExpansionController,
    StyleRule,
    graph_workbench,
    records_to_dataframe,
    viewport_command,
)
from tutorials.common import show_example, show_function


def render_expansion_workflow(state, key):
    provider = ExampleExpansionProvider(expansion_source())
    if "controller" not in state:
        # Keep the controller across reruns so cached branches and revisions survive.
        state["controller"] = ExpansionController(
            expansion_start(),
            source_id="connected-records",
            source_version="2026-01",
            config=ExpansionConfig(page_size=2),
        )
        state["elements"] = state["controller"].view()
    controller = state["controller"]

    def receive():
        event = st.session_state.get(key)
        if not event:
            return
        before = controller.view()
        state["event"] = event
        data = event.get("data", {})
        if event["action"] == "positions":
            controller.update_records(
                {
                    "nodes": [
                        {"data": {"id": row["id"]}, "position": row["position"]}
                        for row in data.get("positions", [])
                    ]
                }
            )
        elif event["action"] == "selection":
            state["selection"] = data
        elif event["action"] == "viewport":
            controller.viewport = {
                field: data[field] for field in ("zoom", "pan") if field in data
            }
        elif event["action"] == "visibility":
            if data["operation"] == "restore_hidden":
                controller.set_visibility(hidden=[], filtered=[])
            else:
                visible = set(data["visible_node_ids"] + data["visible_edge_ids"])
                excluded = {
                    str(e["data"]["id"])
                    for group in ("nodes", "edges")
                    for e in before[group]
                } - visible
                mask = (
                    "hidden" if data["operation"] == "hide_unselected" else "filtered"
                )
                masks = controller.snapshot()
                controller.set_visibility(**{mask: sorted(set(masks[mask]) | excluded)})
        else:
            # The controller validates and deduplicates managed expansion requests.
            controller.handle_event(event, provider)
        # Send only the difference from the browser's previous accepted view.
        state["commands"] = controller.commands(state.get("rendered_elements", before))
        state["elements"] = controller.view()

    st.header("Code and working graph")
    st.markdown(
        "Expand ABC123 to reveal both locations. Each location has its own connections. Location 1 and Location 2 share a report; closing one branch keeps that report when the other still needs it. Pages contain two neighbors so Load more is visible in this example."
    )
    st.subheader("How this example works")
    st.markdown("""
    Expansion separates three different sets of records. The **source** is the
    complete example dataset. The **loaded cache** holds records already fetched
    by Python. The **displayed graph**, returned by `controller.view()`, is the
    subset currently needed by the starting records and active branches.

    `ExampleExpansionProvider` supplies pages from the source;
    `ExpansionController` remembers branch contributions, filters, cached edits,
    and positions. This example sets `page_size=2` to make pagination easy to see;
    the normal default is 50. `controller.describe(provider)` supplies the
    browser's controls and counts. A right-click action returns an `expansion`
    intent; the callback handles it, then sends the difference as graph commands.

    **Collapse is not deletion.** Closing Location 1's branch hides records
    exclusively supported by that branch, while keeping its starting location.
    A shared report remains visible if Location 2 still needs it. Reopening
    restores cached nested exploration instead of automatically fetching it again.
    **Keep visible** protects a record independently of branch collapse; it is
    different from locking a node's position.

    The connections dialog can create separate filtered branches from the same
    node using relationship labels, direction, exact-match attributes, and time
    ranges. Incoming/outgoing refers to edge endpoints, not the order in which
    records were loaded. Node and edge badge counts are separate: `+2n/2e` means
    two additional nodes and two edges, not four new nodes. A page can add only
    edges, and an unknown total must not be interpreted as zero.
    """)
    with st.container(horizontal=True):
        if st.button(
            "Expand all within scope", icon=":material/unfold_more:", key=f"{key}_all"
        ):
            controller.start_bulk(["ABC123"])
        if st.button(
            "Collapse all", icon=":material/unfold_less:", key=f"{key}_collapse"
        ):
            before = controller.view()
            controller.collapse_all()
            state["commands"] = controller.commands(before)
            state["elements"] = controller.view()
    if controller.last_error:
        st.error(controller.last_error)
    st.caption(
        "Right-click a node for branch actions. The connections tool opens filters and cached branches. This control-heavy graph uses the compact toolbar at narrower widths; select its search icon to open the search row. Analysis scope defaults to the displayed graph; the example provider also supports source-level degree."
    )
    with show_example(__file__):
        # A collapsed branch stays cached; only view() determines displayed records.
        result = graph_workbench(
            controller.view(),
            expansion=controller.describe(provider),
            graph_commands=state["commands"],
            # Commands carry later changes without replacing the initial checkpoint.
            elements_sync="initial",
            layout={
                "name": "preset",
                "padding": 80,
                "fit": False,
                "zoom": 0.65,
                "pan": {"x": 40, "y": 250},
            },
            node_styles=[
                *demo_node_styles(text_size=18),
                StyleRule("node", {"width": 46, "height": 46}),
            ],
            node_actions=[
                "show_neighbors",
                "show_incoming",
                "show_outgoing",
                "hide_unselected",
                "restore_hidden",
            ],
            return_positions=True,
            return_selection=True,
            search=True,
            analysis_actions=[
                "shortest_path",
                "bfs",
                "dfs",
                "connected_components",
                "degree",
            ],
            viewport_actions=["save_viewport", "restore_viewport"],
            selection_mode="multiple",
            key=key,
            on_change=receive,
            height=650,
        )
    state["rendered_elements"] = controller.view()
    st.subheader("Try it and check the result")
    st.markdown("""
    1. Right-click ABC123 and expand it. Expect the vehicle plus Location 1 and
       Location 2. Expand each location and use **Load more** where offered so
       both branches' records have been retrieved.
    2. Collapse Location 1's connections. ABC123, both locations, and Location 2's
       connections remain. The shared report stays visible because another
       branch still contributes it. Reopen Location 1 and compare the restored
       records and positions with the previous view.
    3. Expand Camera 1 to explore a nested branch, then collapse and reopen its
       parent location. Nested exploration is remembered, not discarded.
    4. Compare displayed, loaded, and source counts below. **Collapse all**
       retains the starting graph and protected records; it does not empty the
       cache. The change table explains added, hidden, and retained records.
    5. When the toolbar is compact, select the search icon to open its separate
       row. Closing that row restores canvas space without clearing search or
       branch state.

    **Further experiments.** Create a relationship-filtered branch and close it
    individually in the connections dialog. Try bulk expansion within its finite
    depth/node/edge limits; cancellation prevents further batches, not an already
    running provider call. Compare displayed and loaded analysis after collapse.
    This example provider supports source-level degree only, so other source
    algorithms are explicitly unavailable rather than silently using less data.
    """)
    st.subheader("Code in practice")
    show_function(
        receive,
        "**From event to a new view.** This is the callback attached to the graph "
        "above. Positions update the cache; visibility masks stay separate from "
        "branch ownership; managed intents go through handle_event. The final "
        "commands describe the validated view difference, not source-record deletion.",
    )
    with show_example(__file__):
        # Compare scopes explicitly: collapsing changes displayed, not loaded.
        displayed = controller.view()
        loaded = controller.loaded()
        changes = records_to_dataframe(controller.changes)
    st.header("Data and practical result")
    st.markdown(
        "These counts distinguish the records on the canvas from the retained cache and the source dataset. Collapse never removes source records."
    )
    with st.container(horizontal=True):
        st.metric("Displayed nodes", len(displayed["nodes"]))
        st.metric("Loaded nodes", len(loaded["nodes"]))
        st.metric("Source nodes", len(expansion_source()["nodes"]))
    st.markdown(
        "The change table identifies records added, hidden, or retained after the last update. A shared record remains supported by another active branch."
    )
    st.dataframe(changes, hide_index=True, height=220)
    if state.get("selection") is not None:
        selected = set(state["selection"].get("selected_node_ids", []))
        st.markdown(
            "Selected records are available for filtering tables or passing IDs to another application step."
        )
        st.dataframe(
            records_to_dataframe(
                [
                    n["data"]
                    for n in controller.view()["nodes"]
                    if n["data"]["id"] in selected
                ]
            ),
            hide_index=True,
            height=180,
        )
    render_dictionary_preview(
        "Latest event",
        state.get("event") or result,
        "Read `action` first because this view retains the latest event of any kind.\n\n"
        "For expansion, `data.operation` identifies the intent, `node_ids` gives its anchors, "
        "`branch_id` identifies a filtered branch when supplied, and `request_id` deduplicates delivery. "
        "Receipt of an intent is not proof that a provider batch succeeded.\n\n"
        "Analysis payloads include scope, source version, counts, and any collapsed result IDs. "
        "Selection payloads instead contain selected IDs and record context.",
        height=230,
    )
    if controller.analysis_result:
        render_dictionary_preview(
            "Source analysis",
            controller.analysis_result,
            "This result was computed by the Python provider against the full source, not the displayed subset.",
            height=200,
        )
    with st.expander("Search and restore source records"):
        st.markdown(
            "Search here queries the Python provider, including records not yet loaded. "
            "Try `Camera 1`: the result supplies real connecting paths from ABC123. "
            "Reveal uses that context to display the match; it does not invent a shortcut edge. "
            "The graph toolbar's displayed/loaded search covers only those smaller scopes."
        )
        text = st.text_input("Source search", key=f"{key}_source_search")
        if st.button("Search source", key=f"{key}_source_apply"):
            controller.search_result = provider.search(text, roots=["ABC123"])
        if controller.search_result:
            render_dictionary_preview(
                "Search result and real paths",
                controller.search_result,
                "node_ids lists matches; paths contains existing relationship paths from ABC123; elements supplies those records. Unreachable matches are reported, not silently connected.",
                height=220,
            )
            for node_id in controller.search_result["paths"]:
                if st.button(f"Reveal {node_id}", key=f"{key}_reveal_{node_id}"):
                    before = controller.view()
                    controller.reveal_search_result(controller.search_result, node_id)
                    state["commands"] = controller.commands(before)
                    st.rerun()
    with st.expander("Edit cached records and save exploration"):
        st.markdown(
            "Edit a loaded record, collapse its branch, and reopen it to check that "
            "the cached edit survives. This demonstration changes the cache, not an external database. "
            "An exploration snapshot includes cached records, branch/filter state, protected IDs, "
            "and saved positions. Save the viewport in the graph before downloading when camera "
            "restoration matters. Restore checks source identity/version; review record properties "
            "for sensitive information before sharing a snapshot."
        )
        options = [n["data"]["id"] for n in controller.loaded()["nodes"]]
        node_id = st.selectbox("Loaded record", options, key=f"{key}_edit_id")

        @st.dialog("Edit cached record")
        def edit_record():
            node = next(
                n for n in controller.loaded()["nodes"] if n["data"]["id"] == node_id
            )
            with st.form(f"{key}_edit_form"):
                name = st.text_input(
                    "Display name", value=node["data"].get("name", node_id)
                )
                if st.form_submit_button("Save record"):
                    before = controller.view()
                    controller.update_records(
                        {"nodes": [{"data": {"id": node_id, "name": name}}]}
                    )
                    state["commands"] = controller.commands(before)
                    st.rerun()

        if st.button("Edit record", key=f"{key}_edit"):
            edit_record()
        st.download_button(
            "Download exploration snapshot",
            json.dumps(controller.snapshot(), indent=2),
            "exploration.json",
            "application/json",
            key=f"{key}_download",
        )
        upload = st.file_uploader(
            "Restore exploration snapshot", type=["json"], key=f"{key}_upload"
        )
        if upload and st.button("Restore snapshot", key=f"{key}_restore"):
            try:
                restored = ExpansionController.restore(
                    json.loads(upload.getvalue()),
                    source_version=controller.source_version,
                    source_id=controller.source_id,
                )
                state["commands"] = restored.commands(
                    controller.view(), restore_positions=True
                )
                if restored.viewport:
                    state["commands"].append(
                        viewport_command(
                            uuid4().hex, "set_viewport", **restored.viewport
                        )
                    )
                state["controller"] = restored
                st.rerun()
            except (ValueError, KeyError, TypeError) as error:
                st.error(str(error))
        st.dataframe(
            records_to_dataframe(controller.loaded()), hide_index=True, height=220
        )
    with st.expander("Complete shared workflow source"):
        st.code(Path(__file__).read_text(encoding="utf-8"), language="python")
