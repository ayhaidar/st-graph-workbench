import { createState } from "./utils/state.js";
import { getSelectionPayload } from "./utils/payloads.js";
import {
    createComponentContext,
    debounce,
    updateComponentContext,
} from "./utils/helpers.js";
import initCyto, {
    createGraph,
    suppressLayoutPositionEvent,
    syncCustomEventListeners,
    syncGraphOptions,
    syncSelectionState,
} from "./components/graph.js";
import { runLayout } from "./utils/layouts.js";
import initToolbar from "./components/toolbar.js";
import initViewbar from "./components/viewbar.js";
import initNodeActions, { animateNeighbors } from "./components/nodeActions.js";
import updateInfopanel from "./components/infopanel.js";
import initExpansionBadges from "./components/expansionBadges.js";
import initToolbox from "./components/toolbox.js";
import initSelectionControls from "./components/selectionControls.js";
import initSearch, { updateSearchVisibility } from "./components/search.js";
import initAnalysis from "./components/analysis.js";
import initCrud from "./components/crud.js";
import applyGraphCommands from "./components/graphCommands.js";
import initGraphStats from "./components/graphStats.js";
import initEditTools from "./components/editTools.js";
import initViewportTools from "./components/viewportTools.js";
import initProgressiveLoading from "./components/progressiveLoading.js";
import initExpansionControls from "./components/expansionControls.js";

const CONTAINER_ID = "container";
const SYNC_REQUEST_ACTION = "_graph_workbench_sync_request";
const CONTAINER_RESIZE_DEBOUNCE_MS = 80;
const COMPONENT_INSTANCES = new WeakMap();
const COMPONENT_UI_STATE = new Map();

function initConnectedDragLoader(context) {
    let controllerUpdate = null;
    let loading = null;

    return () => {
        if (controllerUpdate) {
            controllerUpdate();
            return;
        }
        if (!context.options.connectedDrag || loading) {
            return;
        }
        loading = import("./components/connectedDrag.js")
            .then((module) => {
                if (context.isDestroyed) return;
                controllerUpdate = module.default(context);
                controllerUpdate();
            })
            .catch((error) => {
                console.error("Failed to load connected-drag controls", error);
            });
    };
}

function initToolbarLayoutLoader(context) {
    let controllerUpdate = null;
    let loading = null;

    return () => {
        if (controllerUpdate) {
            controllerUpdate();
            return;
        }
        if (loading) return;
        loading = import("./components/toolbarLayout.js")
            .then((module) => {
                if (context.isDestroyed) return;
                controllerUpdate = module.default(context);
                controllerUpdate();
            })
            .catch((error) => {
                console.error("Failed to load toolbar layout controls", error);
            });
    };
}

function getPersistentStateKey(component) {
    return (
        component.data?.componentKey || component.name || component.key || null
    );
}

function getPersistentUiState(component) {
    const key = getPersistentStateKey(component);
    return key ? COMPONENT_UI_STATE.get(key) : null;
}

function updatePersistentUiState(component, updates) {
    const key = getPersistentStateKey(component);
    if (!key) {
        return;
    }

    COMPONENT_UI_STATE.set(key, {
        ...(COMPONENT_UI_STATE.get(key) || {}),
        ...updates,
    });
}

function cloneElements(elements) {
    if (!elements || !Array.isArray(elements.nodes)) {
        return null;
    }
    return JSON.parse(JSON.stringify(elements));
}

function hasElementDefinitions(elements) {
    return Boolean(
        elements &&
            ((Array.isArray(elements.nodes) && elements.nodes.length > 0) ||
                (Array.isArray(elements.edges) && elements.edges.length > 0))
    );
}

function getPersistedElements(component) {
    return cloneElements(getPersistentUiState(component)?.elements);
}

function rememberCyElements(component, cy, { allowEmpty = true } = {}) {
    if (!cy || cy.destroyed?.()) {
        return;
    }

    const elements = cloneElements(cy.json().elements);
    if (!elements || (!allowEmpty && !hasElementDefinitions(elements))) {
        return;
    }

    updatePersistentUiState(component, {
        elements: elements,
    });
}

function restorePersistentUiState(component, state) {
    const persisted = getPersistentUiState(component);
    for (const name of [
        "expansionBadgesVisible",
        "selectionDetailsVisible",
        "selectionDetailsOption",
        "toolbarMinimized",
        "toolbarSearchExpanded",
    ]) {
        if (typeof persisted?.[name] === "boolean") {
            state.updateState(name, persisted[name]);
        }
    }
    if (typeof persisted?.connectedDragEnabled === "boolean") {
        state.updateState(
            "connectedDragEnabled",
            persisted.connectedDragEnabled
        );
    }
    if ([1, 2, 3].includes(persisted?.connectedDragDepth)) {
        state.updateState("connectedDragDepth", persisted.connectedDragDepth);
    }
    if (
        typeof persisted?.connectedDragOption === "string" ||
        persisted?.connectedDragOption === null
    ) {
        state.updateState("connectedDragOption", persisted.connectedDragOption);
    }
    if (
        typeof persisted?.toolbarOption === "string" ||
        persisted?.toolbarOption === null
    ) {
        state.updateState("toolbarOption", persisted.toolbarOption);
    }
}

function persistUiState(component, state) {
    const key = getPersistentStateKey(component);
    if (!key) {
        return;
    }

    for (const name of [
        "expansionBadgesVisible",
        "selectionDetailsVisible",
        "selectionDetailsOption",
        "connectedDragEnabled",
        "connectedDragDepth",
        "connectedDragOption",
        "toolbarMinimized",
        "toolbarSearchExpanded",
        "toolbarOption",
    ]) {
        state.subscribe(name, (value) => {
            updatePersistentUiState(component, { [name]: value });
        });
    }
}

function syncSelectionDetailsPreference(context) {
    const preference = context.options.showSelectionDetails;
    // Repeated Python defaults must not undo the user's browser preference.
    if (context.state.getState("selectionDetailsOption") !== preference) {
        context.state.updateState("selectionDetailsOption", preference);
        context.state.updateState("selectionDetailsVisible", preference);
    }
}

function getElementDefinitions(nextElements) {
    return [...(nextElements["nodes"] || []), ...(nextElements["edges"] || [])];
}

function getElementId(element) {
    if (element?.data?.id === undefined) {
        return null;
    }
    return String(element.data.id);
}

function resolveAssetUrl(path, assetBasePath) {
    const assetPath = path.replace(/^\.\//, "");
    return `${assetBasePath.replace(/\/$/, "")}/${assetPath}`;
}

function resolveStyleAssetUrls(style, assetBasePath) {
    return style.map((styleDefinition) => {
        const backgroundImage = styleDefinition?.style?.["background-image"];
        if (typeof backgroundImage !== "string") {
            return styleDefinition;
        }

        const isResolvableAsset =
            backgroundImage.includes("_") || backgroundImage.endsWith(".svg");
        if (
            !isResolvableAsset ||
            backgroundImage.startsWith("url(") ||
            backgroundImage.startsWith("http") ||
            backgroundImage.startsWith("data:")
        ) {
            return styleDefinition;
        }

        return {
            ...styleDefinition,
            style: {
                ...styleDefinition.style,
                "background-image": resolveAssetUrl(
                    backgroundImage,
                    assetBasePath
                ),
            },
        };
    });
}

function parseRgbColor(color) {
    const channels = color.match(/\d+(\.\d+)?/g)?.map(Number);
    if (!channels || channels.length < 3) {
        return null;
    }
    return channels.slice(0, 3);
}

function isDarkColor(color) {
    const rgb = parseRgbColor(color);
    if (!rgb) {
        return false;
    }

    const [red, green, blue] = rgb;
    const luminance = 0.299 * red + 0.587 * green + 0.114 * blue;
    return luminance < 128;
}

function getThemeBase(parentElement) {
    const container =
        parentElement.getElementById?.(CONTAINER_ID) ||
        parentElement.querySelector(`#${CONTAINER_ID}`);
    if (!container) {
        return "light";
    }
    const styles = getComputedStyle(container);
    const backgroundColor =
        styles.getPropertyValue("--st-background-color") ||
        styles.backgroundColor;

    return isDarkColor(backgroundColor) ? "dark" : "light";
}

function normalizeRenderData(data = {}) {
    const assetBasePath =
        data["assetBasePath"] ||
        "/_stcore/bidi-components/st_graph_workbench.graph_workbench";
    const performanceProfile = data["performanceProfile"] || "default";
    const hasElements =
        Object.prototype.hasOwnProperty.call(data, "elements") &&
        data["elements"] !== null;
    return {
        elements: hasElements ? data["elements"] : { nodes: [], edges: [] },
        hasElements,
        style: resolveStyleAssetUrls(data["style"] || [], assetBasePath),
        layout: applyPerformanceProfile(
            data["layout"] || {},
            performanceProfile
        ),
        height: data["height"] || "500px",
        nodeActions: data["nodeActions"] || [],
        graphCommands: data["graphCommands"] || [],
        elementsSync: data["elementsSync"] || "always",
        events: data["events"] || [],
        options: {
            analysisActions: data["analysisActions"] || [],
            crudActions: data["crudActions"] || [],
            editActions: data["editActions"] || [],
            nodeActions: data["nodeActions"] || [],
            performanceProfile: performanceProfile,
            progressiveLoading: data["progressiveLoading"] || null,
            expansion: data["expansion"] || null,
            connectedDrag: data["connectedDrag"] || null,
            toolbar: data["toolbar"] || null,
            returnPositions: Boolean(data["returnPositions"]),
            returnSelection: Boolean(data["returnSelection"]),
            showSelectionDetails: data["showSelectionDetails"] !== false,
            search: Boolean(data["search"]),
            selectionMode: data["selectionMode"] || "single",
            viewportActions: data["viewportActions"] || [],
            viewportOptions: data["viewportOptions"] || {},
        },
    };
}

function applyPerformanceProfile(layout, profile) {
    if (profile === "default") {
        return layout;
    }

    return {
        ...layout,
        animate: false,
        animationDuration: 0,
        nodeDimensionsIncludeLabels: profile === "large",
    };
}

function edgeEndpointsChanged(currentElement, nextElement) {
    if (!currentElement.isEdge()) {
        return false;
    }
    const data = nextElement.data || {};
    return (
        data.source !== undefined &&
        data.target !== undefined &&
        (String(data.source) !== String(currentElement.data("source")) ||
            String(data.target) !== String(currentElement.data("target")))
    );
}

function normalizePosition(position) {
    const x = Number(position?.x);
    const y = Number(position?.y);

    if (!Number.isFinite(x) || !Number.isFinite(y)) {
        return null;
    }

    return { x, y };
}

function sortAddedElements(elementDefs) {
    return [
        ...elementDefs.filter((element) => element.group !== "edges"),
        ...elementDefs.filter((element) => element.group === "edges"),
    ];
}

function updateExistingElementData(
    nextElementDefs,
    currentIds,
    replaceIds,
    cy,
    { applyPositions = false } = {}
) {
    nextElementDefs.forEach((element) => {
        const id = getElementId(element);
        if (id === null || !currentIds.has(id) || replaceIds.has(id)) {
            return;
        }

        const currentElement = cy.getElementById(id);
        if (currentElement.length > 0) {
            currentElement.json({ data: element.data });
            const position = normalizePosition(element.position);
            if (
                applyPositions &&
                currentElement.isNode() &&
                position !== null &&
                currentElement.grabbed?.() !== true
            ) {
                currentElement.position(position);
            }
        }
    });
}

function reconcileElements(nextElements, expandedNode, instance) {
    const cy = instance.cy;
    const currentElements = cy.elements();
    const nextElementDefs = getElementDefinitions(nextElements);
    const currentIds = new Set(currentElements.map((ele) => ele.id()));
    const nextIds = new Set(
        nextElementDefs.map(getElementId).filter((id) => id !== null)
    );
    const replaceIds = new Set(
        nextElementDefs
            .filter((element) => {
                const id = getElementId(element);
                if (id === null || !currentIds.has(id)) {
                    return false;
                }
                return edgeEndpointsChanged(cy.getElementById(id), element);
            })
            .map(getElementId)
    );

    const removedElements = currentElements.filter(
        (ele) => !nextIds.has(ele.id()) || replaceIds.has(ele.id())
    );
    const addedElementDefs = nextElementDefs.filter((ele) => {
        const id = getElementId(ele);
        return id !== null && (!currentIds.has(id) || replaceIds.has(id));
    });

    const hasRemovals = removedElements.length > 0;
    let newElements = cy.collection();

    cy.batch(() => {
        updateExistingElementData(nextElementDefs, currentIds, replaceIds, cy, {
            applyPositions: Boolean(instance.context.options.returnPositions),
        });

        if (hasRemovals) {
            removedElements.remove();
        }

        if (addedElementDefs.length > 0) {
            newElements = cy.add(sortAddedElements(addedElementDefs));
        }
    });

    if (newElements.length === 0) {
        return;
    }
    const newNodes = newElements.filter("node");
    if (
        !hasRemovals &&
        expandedNode &&
        expandedNode.inside?.() &&
        newNodes.length > 0
    ) {
        instance.context.suppressPositionEmitUntil = Date.now() + 900;
        animateNeighbors(expandedNode, newNodes, instance.context);
    }
}

function initializeInstance(component, renderData) {
    const state = createState();
    restorePersistentUiState(component, state);
    persistUiState(component, state);
    const context = createComponentContext(component, state);
    context.options = renderData.options;
    syncSelectionDetailsPreference(context);
    const cy = initCyto(context, renderData.events);
    const graph = createGraph(context);
    const updateExpansionBadges = initExpansionBadges(context);
    context.updateExpansionBadges = updateExpansionBadges;
    const updateToolbox = initToolbox(context);
    let updateGraphStats = null;
    let updateAnalysis = null;
    let updateCrud = null;
    let updateSelectionControls = null;
    let updateProgressiveLoading = null;
    let updateManagedExpansion = null;
    let updateConnectedDrag = null;
    let updateToolbarLayout = null;
    context.refreshGraphUi = (latestSelected = null) => {
        syncSelectionState(context, cy, latestSelected);
        updateInfopanel(context);
        updateExpansionBadges();
        updateGraphStats?.();
        updateToolbox();
        updateAnalysis?.();
        updateCrud?.();
        updateSelectionControls?.();
        updateProgressiveLoading?.();
        updateManagedExpansion?.();
        updateConnectedDrag?.();
        updateToolbarLayout?.();
        context.updateEditTools?.();
        context.updateViewportTools?.();
    };
    const handleFullscreenChange = () => {
        context.getElementById(CONTAINER_ID)?.scrollIntoView();
    };

    cy.json({ elements: renderData.elements });
    updateGraphStats = initGraphStats(context);
    context.updateGraphStats = updateGraphStats;
    initNodeActions(context);
    initToolbar(context);
    initViewbar(context);
    updateSelectionControls = initSelectionControls(context);
    context.updateSelectionControls = updateSelectionControls;
    updateConnectedDrag = initConnectedDragLoader(context);
    updateConnectedDrag();
    initSearch(context);
    updateToolbarLayout = initToolbarLayoutLoader(context);
    updateToolbarLayout();
    updateAnalysis = initAnalysis(context);
    updateCrud = initCrud(context);
    updateProgressiveLoading = initProgressiveLoading(context);
    updateManagedExpansion = initExpansionControls(context);
    const updateEditTools = initEditTools(context);
    const updateViewportTools = initViewportTools(context);
    context.updateEditTools = updateEditTools;
    context.updateViewportTools = updateViewportTools;

    state.subscribe("selection", () => updateInfopanel(context));
    state.subscribe("selectionDetailsVisible", () => updateInfopanel(context));
    updateInfopanel(context);
    state.subscribe("selection", graph.updateHighlight);
    state.subscribe("layout", graph.updateLayout);
    state.subscribe("style", graph.updateStyle);
    document.addEventListener("fullscreenchange", handleFullscreenChange);

    return {
        context,
        cy,
        elements: JSON.stringify(renderData.elements),
        appliedCommandIds: new Set(),
        handleFullscreenChange,
        layout: null,
        syncRequested: false,
        state,
        style: null,
        updateExpansionBadges,
        updateAnalysis,
        updateCrud,
        updateEditTools,
        updateGraphStats,
        updateSelectionControls,
        updateProgressiveLoading,
        updateManagedExpansion,
        updateConnectedDrag,
        updateToolbarLayout,
        updateToolbox,
        updateViewportTools,
        resizeFrameId: null,
        resizeObserver: null,
        resizeObserverCallback: null,
    };
}

function requestElementSync(instance, reason) {
    if (instance.syncRequested) {
        return;
    }
    instance.syncRequested = true;
    instance.context.setStreamlitValue({
        action: SYNC_REQUEST_ACTION,
        data: { reason },
        timestamp: Date.now(),
    });
}

function prepareContainer(container, height) {
    container.style.height = height;
    container.style.position = "relative";
    container.style.boxSizing = "border-box";
    if (container.dataset.ready !== "true") {
        container.dataset.ready = "false";
    }

    const cyLayer = container.querySelector("#cy");
    cyLayer.style.position = "absolute";
    cyLayer.style.top = "var(--graph-stage-top, 0px)";
    cyLayer.style.right = "0";
    cyLayer.style.bottom = "0";
    cyLayer.style.left = "0";
    cyLayer.style.height = "auto";
    cyLayer.style.width = "100%";
}

function scheduleResize(instance, layout) {
    instance.layout = JSON.stringify(layout);
    suppressLayoutPositionEvent(instance.context);
    if (instance.resizeFrameId !== null) {
        cancelAnimationFrame(instance.resizeFrameId);
    }
    instance.resizeFrameId = requestAnimationFrame(() => {
        instance.resizeFrameId = null;
        if (instance.cy.destroyed()) {
            return;
        }
        instance.cy.resize();
        instance.updateSelectionControls();
        runLayout(instance.context, instance.cy, layout);
        instance.updateExpansionBadges();
        instance.updateGraphStats();
    });
}

function observeContainerResize(instance, container) {
    if (typeof ResizeObserver !== "function" || instance.resizeObserver) {
        return;
    }

    const topbar = container.querySelector(".graph-topbar");
    const expansionBar = container.querySelector(".managed-expansion-bar");
    const resize = () => {
        if (instance.cy.destroyed()) {
            return;
        }
        // Keep details below wrapping controls without changing the viewport.
        const bounds = container.getBoundingClientRect();
        const top = (topbar?.getBoundingClientRect().bottom || bounds.top) + 8;
        container.style.setProperty("--infopanel-top", `${top - bounds.top}px`);
        const graphStageTop = instance.context.options.toolbar?.sticky
            ? Math.max(0, top - bounds.top)
            : 0;
        container.style.setProperty("--graph-stage-top", `${graphStageTop}px`);
        if (instance.context.options.expansion) {
            const bottom = Math.max(
                52,
                bounds.bottom -
                    (expansionBar?.getBoundingClientRect().top ||
                        bounds.bottom) +
                    8
            );
            container.style.setProperty("--infopanel-bottom", `${bottom}px`);
            container.style.setProperty(
                "--infopanel-space",
                `${Math.max(0, bounds.bottom - top - bottom - 6)}px`
            );
        }
        instance.cy.resize();
        instance.updateExpansionBadges();
        instance.updateGraphStats();
    };
    const debouncedResize = debounce(resize, CONTAINER_RESIZE_DEBOUNCE_MS);

    instance.resizeObserver = new ResizeObserver(debouncedResize);
    instance.resizeObserverCallback = debouncedResize;
    instance.resizeObserver.observe(container);
    if (topbar) instance.resizeObserver.observe(topbar);
    if (expansionBar) instance.resizeObserver.observe(expansionBar);
}

function cleanupInstance(component, instance, { allowEmpty = true } = {}) {
    rememberCyElements(component, instance.cy, { allowEmpty });
    if (instance.resizeFrameId !== null) {
        cancelAnimationFrame(instance.resizeFrameId);
        instance.resizeFrameId = null;
    }
    instance.resizeObserver?.disconnect();
    instance.resizeObserver = null;
    instance.resizeObserverCallback?.cancel?.();
    instance.resizeObserverCallback = null;
    instance.context.cleanup?.();
    document.removeEventListener(
        "fullscreenchange",
        instance.handleFullscreenChange
    );
    if (!instance.cy.destroyed()) {
        instance.cy.destroy();
    }
    COMPONENT_INSTANCES.delete(component.parentElement);
}

function renderGraph(component) {
    const renderData = normalizeRenderData(component.data);
    if (!renderData.hasElements) {
        renderData.elements =
            getPersistedElements(component) || renderData.elements;
    }

    const themeBase = getThemeBase(component.parentElement);
    const container =
        component.parentElement.getElementById?.(CONTAINER_ID) ||
        component.parentElement.querySelector(`#${CONTAINER_ID}`);

    prepareContainer(container, renderData.height);
    container.dataset.elementsSync = renderData.hasElements
        ? "elements"
        : "commands";

    let instance = COMPONENT_INSTANCES.get(component.parentElement);
    if (!instance) {
        instance = initializeInstance(component, renderData);
        COMPONENT_INSTANCES.set(component.parentElement, instance);
        observeContainerResize(instance, container);
        scheduleResize(instance, renderData.layout);
    } else {
        updateComponentContext(instance.context, component);
        instance.context.options = renderData.options;
        syncSelectionDetailsPreference(instance.context);
        syncGraphOptions(instance.context, instance.cy);
        syncCustomEventListeners(
            instance.context,
            instance.cy,
            renderData.events
        );
        updateSearchVisibility(instance.context);
        instance.updateToolbox();
        instance.updateAnalysis();
        instance.updateCrud();
        instance.updateSelectionControls();
        instance.updateProgressiveLoading();
        instance.updateEditTools();
        instance.updateViewportTools();
        instance.updateConnectedDrag();
        instance.updateToolbarLayout();
    }

    const newElements = JSON.stringify(renderData.elements);
    const newStyle =
        JSON.stringify(renderData.style) +
        themeBase +
        renderData.options.performanceProfile;
    const newLayout = JSON.stringify(renderData.layout);

    if (!renderData.hasElements && instance.cy.elements().length === 0) {
        requestElementSync(instance, "missing_initial_elements");
        return () =>
            cleanupInstance(component, instance, { allowEmpty: false });
    }

    if (renderData.hasElements && newElements !== instance.elements) {
        instance.elements = newElements;
        instance.syncRequested = false;
        const lastExpanded = instance.state.getState("lastExpanded");
        reconcileElements(renderData.elements, lastExpanded, instance);
        const selection = instance.state.getState("selection");
        if (selection.selected?.some((element) => !element.inside())) {
            syncSelectionState(
                instance.context,
                instance.cy,
                selection.lastSelected
            );
        }
        updateInfopanel(instance.context);
        instance.updateExpansionBadges();
        instance.updateGraphStats();
        instance.updateToolbox();
        instance.updateAnalysis();
        instance.updateCrud();
        instance.updateSelectionControls();
        instance.updateProgressiveLoading();
        instance.updateEditTools();
        instance.updateViewportTools();
        instance.updateConnectedDrag();
    }
    instance.state.updateState("lastExpanded", false);

    const selectionBeforeCommands = instance.cy
        .elements(":selected")
        .map((element) => element.id());
    const commandResult = applyGraphCommands(
        instance,
        renderData.graphCommands,
        renderData.layout
    );
    if (renderData.options.expansion && renderData.graphCommands.length) {
        instance.context.setStateValue?.(
            "command_receipts",
            renderData.graphCommands
                .map((command) => String(command.command_id))
                .filter((id) => instance.appliedCommandIds.has(id))
        );
    }
    if (commandResult.changed) {
        syncSelectionState(
            instance.context,
            instance.cy,
            instance.state.getState("selection").lastSelected
        );
        updateInfopanel(instance.context);
        instance.updateExpansionBadges();
        instance.updateGraphStats();
        instance.updateToolbox();
        instance.updateAnalysis();
        instance.updateCrud();
        instance.updateSelectionControls();
        instance.updateProgressiveLoading();
        instance.updateEditTools();
        instance.updateViewportTools();
        if (
            renderData.options.expansion &&
            renderData.options.returnSelection &&
            selectionBeforeCommands.some((id) =>
                instance.cy.getElementById(id).empty()
            )
        ) {
            instance.context.setImmediateStreamlitValue({
                action: "selection",
                data: getSelectionPayload(
                    instance.cy,
                    instance.state.getState("selection").lastSelected
                ),
                timestamp: Date.now(),
            });
        }
    }

    if (newStyle !== instance.style) {
        instance.style = newStyle;
        instance.state.updateState("style", {
            custom_style: renderData.style,
            theme: themeBase,
        });
    }

    if (newLayout !== instance.layout) {
        instance.layout = newLayout;
        instance.state.updateState("layout", renderData.layout);
    }

    rememberCyElements(component, instance.cy);
    instance.updateManagedExpansion();
    instance.updateConnectedDrag();
    instance.updateExpansionBadges();

    return () => cleanupInstance(component, instance);
}

export default renderGraph;
