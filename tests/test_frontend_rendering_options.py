from pathlib import Path


def test_dense_profile_does_not_hide_edges_during_viewport_movement():
    graph_source = Path(
        "st_graph_workbench/frontend/src/components/graph.js"
    ).read_text(encoding="utf-8")

    assert "hideEdgesOnViewport" not in graph_source


def test_search_does_not_hide_or_restore_graph_elements():
    search_source = Path(
        "st_graph_workbench/frontend/src/components/search.js"
    ).read_text(encoding="utf-8")

    assert ".hide(" not in search_source
    assert ".show(" not in search_source


def test_action_controls_refresh_from_latest_component_options():
    index_source = Path("st_graph_workbench/frontend/src/index.js").read_text(
        encoding="utf-8"
    )
    toolbox_source = Path(
        "st_graph_workbench/frontend/src/components/toolbox.js"
    ).read_text(encoding="utf-8")
    crud_source = Path("st_graph_workbench/frontend/src/components/crud.js").read_text(
        encoding="utf-8"
    )
    analysis_source = Path(
        "st_graph_workbench/frontend/src/components/analysis.js"
    ).read_text(encoding="utf-8")
    selection_source = Path(
        "st_graph_workbench/frontend/src/components/selectionControls.js"
    ).read_text(encoding="utf-8")
    node_actions_source = Path(
        "st_graph_workbench/frontend/src/components/nodeActions.js"
    ).read_text(encoding="utf-8")

    assert 'nodeActions: data["nodeActions"] || []' in index_source
    assert "instance.updateToolbox();" in index_source
    assert "instance.updateAnalysis();" in index_source
    assert "instance.updateCrud();" in index_source
    assert "context.options.nodeActions || []" in toolbox_source
    assert "context.options.nodeActions || []" in selection_source
    assert "context.options.crudActions || []" in crud_source
    assert "context.options.analysisActions || []" in analysis_source
    assert "return update;" in crud_source
    assert "return update;" in analysis_source
    assert "return update;" in selection_source
    assert "nodeActions.length === 0" not in node_actions_source
    assert 'hasNodeAction(context, "expand")' in node_actions_source


def test_progressive_loading_emits_cursor_aware_batch_requests():
    index_source = Path("st_graph_workbench/frontend/src/index.js").read_text(
        encoding="utf-8"
    )
    component_html = Path("st_graph_workbench/frontend/src/component.html").read_text(
        encoding="utf-8"
    )
    loading_source = Path(
        "st_graph_workbench/frontend/src/components/progressiveLoading.js"
    ).read_text(encoding="utf-8")

    assert 'progressiveLoading: data["progressiveLoading"] || null' in index_source
    assert "instance.updateProgressiveLoading();" in index_source
    assert 'id="progressiveLoadingButton"' in component_html
    assert 'action: "load_more"' in loading_source
    for field in (
        "request_id",
        "acknowledged_request_id",
        "cursor",
        "page_size",
        "loaded_count",
        "total_count",
        "remaining_count",
        "current_node_count",
        "current_edge_count",
    ):
        assert field in loading_source


def test_cytoscape_options_refresh_from_latest_component_options():
    index_source = Path("st_graph_workbench/frontend/src/index.js").read_text(
        encoding="utf-8"
    )
    graph_source = Path(
        "st_graph_workbench/frontend/src/components/graph.js"
    ).read_text(encoding="utf-8")

    assert "syncGraphOptions(instance.context, instance.cy);" in index_source
    assert "function syncGraphOptions(context, cy)" in graph_source
    assert "cy.selectionType(nextSelectionType);" in graph_source
    assert "cy.boxSelectionEnabled(nextBoxSelectionEnabled);" in graph_source
    assert "context.defaultMinZoom = cy.minZoom();" in graph_source
    assert "context.defaultMaxZoom = cy.maxZoom();" in graph_source
    assert "context.defaultMinZoom" in graph_source
    assert "context.defaultMaxZoom" in graph_source
    assert "cy.minZoom(minZoom);" in graph_source
    assert "cy.maxZoom(maxZoom);" in graph_source


def test_box_selection_has_an_explicit_pan_mode():
    box_selection_source = Path(
        "st_graph_workbench/frontend/src/components/boxSelection.js"
    ).read_text(encoding="utf-8")

    assert 'const PAN_MODE = "pan";' in box_selection_source
    assert 'const BOX_MODE = "box";' in box_selection_source
    assert "context.isBoxSelectionInteractionActive" in box_selection_source
    assert "context.syncBoxSelectionInteraction" in box_selection_source
    assert "cy.boxSelectionEnabled(boxSelectionActive);" in box_selection_source
    assert 'panButton.addEventListener("click", onPanClick);' in box_selection_source
    assert 'boxButton.addEventListener("click", onBoxClick);' in box_selection_source


def test_viewport_commands_treat_null_zoom_values_as_optional_or_reset():
    commands_source = Path(
        "st_graph_workbench/frontend/src/components/graphCommands.js"
    ).read_text(encoding="utf-8")

    assert (
        'hasCommandField(command, "zoom") && command.zoom !== null' in commands_source
    )
    assert "const minZoom = zoomBoundValue(" in commands_source
    assert "command.min_zoom," in commands_source
    assert "context.defaultMinZoom" in commands_source
    assert "const maxZoom = zoomBoundValue(" in commands_source
    assert "command.max_zoom," in commands_source
    assert "context.defaultMaxZoom" in commands_source


def test_viewport_commands_sanitize_optional_numeric_values():
    commands_source = Path(
        "st_graph_workbench/frontend/src/components/graphCommands.js"
    ).read_text(encoding="utf-8")

    assert "function nonnegativeNumber(value, fallback)" in commands_source
    assert (
        "const duration = nonnegativeNumber(command.duration, 180);" in commands_source
    )
    assert "fit: { padding: nonnegativeNumber(command.padding, 30) }" in commands_source
    assert (
        "const viewportDuration = nonnegativeNumber(command.duration, 0);"
        in commands_source
    )
    assert "const animation = { duration: viewportDuration };" in commands_source


def test_async_layout_runs_ignore_stale_callbacks():
    layouts_source = Path("st_graph_workbench/frontend/src/utils/layouts.js").read_text(
        encoding="utf-8"
    )

    assert "function nextLayoutRunToken(context)" in layouts_source
    assert (
        "context.layoutRunToken = (context.layoutRunToken || 0) + 1;" in layouts_source
    )
    assert "function isCurrentLayoutRun(context, token)" in layouts_source
    assert "const token = nextLayoutRunToken(context);" in layouts_source
    assert (
        "context?.isDestroyed || !isCurrentLayoutRun(context, token)" in layouts_source
    )
    assert "markReadyAfterLayout(context, cy, token);" in layouts_source


def test_layout_runner_normalizes_named_layout_commands():
    layouts_source = Path("st_graph_workbench/frontend/src/utils/layouts.js").read_text(
        encoding="utf-8"
    )

    assert "function getLayoutOptions(layout)" in layouts_source
    assert 'typeof layout === "string" ? { name: layout } : layout' in layouts_source
    assert "cy.layout(getLayoutOptions(layout)).run();" in layouts_source


def test_infopanel_renders_element_data_as_text_not_html():
    infopanel_source = Path(
        "st_graph_workbench/frontend/src/components/infopanel.js"
    ).read_text(encoding="utf-8")

    assert ".innerHTML" not in infopanel_source
    assert "createPropertyRow(" in infopanel_source
    assert "valueElement.textContent = valueText(value);" in infopanel_source
    assert "props.replaceChildren(" in infopanel_source


def test_infopanel_clears_selection_without_changing_details_preference():
    component_html = Path("st_graph_workbench/frontend/src/component.html").read_text(
        encoding="utf-8"
    )
    selection_source = Path(
        "st_graph_workbench/frontend/src/components/selectionControls.js"
    ).read_text(encoding="utf-8")

    assert 'id="infopanelClear"' in component_html
    assert 'aria-label="Clear selection"' in component_html
    assert 'id="selectionShowDetails"' in component_html
    assert 'infopanelClear?.addEventListener("click"' in selection_source
    assert 'cy.elements(":selected").unselect()' in selection_source
    assert 'updateState("selectionDetailsVisible", false)' not in selection_source
    assert 'updateState("selectionDetailsVisible", details.checked)' in selection_source


def test_toolbox_dropdowns_close_after_command_clicks():
    toolbox_source = Path(
        "st_graph_workbench/frontend/src/components/toolbox.js"
    ).read_text(encoding="utf-8")

    assert "function initMenuAutoClose(context)" in toolbox_source
    assert "button.toolbox__button" in toolbox_source
    assert 'button.closest("details.toolbox__menu")' in toolbox_source
    assert "menu.open = false;" in toolbox_source
    assert "toolbox.removeEventListener" in toolbox_source


def test_toolbar_layout_is_lazy_responsive_and_reserves_graph_space():
    index_source = Path("st_graph_workbench/frontend/src/index.js").read_text(
        encoding="utf-8"
    )
    toolbar_source = Path(
        "st_graph_workbench/frontend/src/components/toolbarLayout.js"
    ).read_text(encoding="utf-8")
    component_html = Path("st_graph_workbench/frontend/src/component.html").read_text(
        encoding="utf-8"
    )
    style_source = Path("st_graph_workbench/frontend/src/style.css").read_text(
        encoding="utf-8"
    )

    assert 'import("./components/toolbarLayout.js")' in index_source
    assert 'toolbar: data["toolbar"] || null' in index_source
    assert "new ResizeObserver(update)" in toolbar_source
    assert '"--graph-stage-top"' in toolbar_source
    assert 'cy.on("layoutstop", scheduleInitialStageCheck)' in toolbar_source
    assert "nodes.renderedBoundingBox" in toolbar_source
    assert 'id="toolbarCollapse"' in component_html
    assert 'id="toolbarSearchToggle"' in component_html
    assert "top: var(--graph-stage-top, 0px);" in style_source


def test_button_state_helper_is_shared_across_frontend_modules():
    helper_source = Path("st_graph_workbench/frontend/src/utils/dom.js").read_text(
        encoding="utf-8"
    )
    component_paths = [
        Path("st_graph_workbench/frontend/src/components/analysis.js"),
        Path("st_graph_workbench/frontend/src/components/crud.js"),
        Path("st_graph_workbench/frontend/src/components/editTools.js"),
        Path("st_graph_workbench/frontend/src/components/selectionControls.js"),
        Path("st_graph_workbench/frontend/src/components/toolbox.js"),
        Path("st_graph_workbench/frontend/src/components/viewportTools.js"),
    ]

    assert "function setButtonState(" in helper_source
    assert "aria-disabled" in helper_source
    assert "aria-pressed" in helper_source

    for path in component_paths:
        source = path.read_text(encoding="utf-8")
        assert 'import { setButtonState } from "../utils/dom.js";' in source
        assert "function setButtonState(" not in source


def test_drag_position_events_ignore_edit_command_suppression():
    graph_source = Path(
        "st_graph_workbench/frontend/src/components/graph.js"
    ).read_text(encoding="utf-8")

    assert "function emitPositions(" in graph_source
    assert "{ respectSuppression = true, movement = null } = {}" in graph_source
    assert "respectSuppression &&" in graph_source
    assert "respectSuppression: false" in graph_source
    assert "movement: context.consumeDragMovement?.() || null" in graph_source


def test_custom_event_listeners_refresh_without_remount():
    index_source = Path("st_graph_workbench/frontend/src/index.js").read_text(
        encoding="utf-8"
    )
    graph_source = Path(
        "st_graph_workbench/frontend/src/components/graph.js"
    ).read_text(encoding="utf-8")

    assert (
        "function syncCustomEventListeners(context, cy, listeners = [])" in graph_source
    )
    assert "clearCustomEventListeners(context, cy);" in graph_source
    assert (
        "cy.off(binding.event_type, binding.selector, binding.handler);" in graph_source
    )
    assert "cy.on(listener.event_type, listener.selector, handler);" in graph_source
    assert "syncCustomEventListeners(" in index_source
    assert "renderData.events" in index_source
