import { cytoscape, runLayout } from "../utils/layouts.js";
import { debounce } from "../utils/helpers";
import { getPositionsPayload, getSelectionPayload } from "../utils/payloads.js";
import { getStyles } from "../utils/styles";
import initBoxSelection from "./boxSelection.js";

// Constants & configurations
const CY_ID = "cy";
const SELECT_DEBOUNCE = 100;
const POSITION_DEBOUNCE = 250;
const DRAG_SELECTION_SUPPRESS_MS = 350;
const CUSTOM_EVENT_DUPLICATE_SUPPRESSION_MS = 120;

function getSelectionType(mode) {
    return mode === "multiple" || mode === "box" ? "additive" : "single";
}

function finiteNumber(value) {
    if (value === undefined || value === null || value === "") {
        return undefined;
    }
    const numberValue = Number(value);
    return Number.isFinite(numberValue) ? numberValue : undefined;
}

function getInitOptions(context, selectionMode) {
    const performanceProfile = context.options.performanceProfile || "default";
    const viewportOptions = context.options.viewportOptions || {};
    const minZoom = finiteNumber(viewportOptions.minZoom);
    const maxZoom = finiteNumber(viewportOptions.maxZoom);
    const wheelSensitivity = finiteNumber(viewportOptions.wheelSensitivity);
    const options = {
        container: context.getElementById(CY_ID),
        selectionType: getSelectionType(selectionMode),
        boxSelectionEnabled: selectionMode === "box",
    };

    if (minZoom !== undefined) {
        options.minZoom = minZoom;
    }
    if (maxZoom !== undefined) {
        options.maxZoom = maxZoom;
    }
    if (wheelSensitivity !== undefined) {
        options.wheelSensitivity = wheelSensitivity;
    }

    if (performanceProfile === "large" || performanceProfile === "dense") {
        options.hideLabelsOnViewport = true;
        options.textureOnViewport = true;
        options.motionBlur = false;
    }
    if (performanceProfile === "dense") {
        options.pixelRatio = 1;
    }

    return options;
}

function syncGraphOptions(context, cy) {
    const selectionMode = context.options.selectionMode || "single";
    const nextSelectionType = getSelectionType(selectionMode);
    const nextBoxSelectionEnabled =
        context.isBoxSelectionInteractionActive?.() ?? selectionMode === "box";
    const viewportOptions = context.options.viewportOptions || {};
    const minZoom =
        finiteNumber(viewportOptions.minZoom) ?? context.defaultMinZoom;
    const maxZoom =
        finiteNumber(viewportOptions.maxZoom) ?? context.defaultMaxZoom;

    if (cy.selectionType() !== nextSelectionType) {
        cy.selectionType(nextSelectionType);
    }
    if (cy.boxSelectionEnabled() !== nextBoxSelectionEnabled) {
        cy.boxSelectionEnabled(nextBoxSelectionEnabled);
    }
    if (minZoom !== undefined && cy.minZoom() !== minZoom) {
        cy.minZoom(minZoom);
    }
    if (maxZoom !== undefined && cy.maxZoom() !== maxZoom) {
        cy.maxZoom(maxZoom);
    }
    context.syncBoxSelectionInteraction?.();
}

function emitSelection(context, cy, lastSelected) {
    if (!context.options.returnSelection) {
        return;
    }
    if (Date.now() < (context.suppressSelectionEmitUntil || 0)) {
        return;
    }

    context.debouncedSetValue({
        action: "selection",
        data: getSelectionPayload(cy, lastSelected),
        timestamp: Date.now(),
    });
}

function emitPositions(
    context,
    cy,
    { respectSuppression = true, movement = null } = {}
) {
    if (!context.options.returnPositions) {
        return;
    }
    if (
        respectSuppression &&
        Date.now() < (context.suppressPositionEmitUntil || 0)
    ) {
        return;
    }

    context.debouncedSetValue({
        action: "positions",
        data: getPositionsPayload(cy, movement),
        timestamp: Date.now(),
    });
}

function customEventTypeGroup(eventType) {
    return eventType === "click" || eventType === "tap" ? "pointer" : eventType;
}

function emitCustomEvent(context, listener, event) {
    const now = Date.now();
    const targetId = event.target.id();
    const targetGroup = event.target.group();
    const duplicateKey = [
        listener.name,
        targetId,
        targetGroup,
        customEventTypeGroup(event.type),
    ].join(":");
    const previous = context.lastCustomEvent || {};
    if (
        previous.key === duplicateKey &&
        now - previous.timestamp < CUSTOM_EVENT_DUPLICATE_SUPPRESSION_MS
    ) {
        return;
    }

    context.lastCustomEvent = { key: duplicateKey, timestamp: now };
    context.setStreamlitValue({
        action: listener.name,
        data: {
            type: event.type,
            target_id: targetId,
            target_group: targetGroup,
        },
        timestamp: now,
    });
}

function customEventSignature(listeners = []) {
    return JSON.stringify(
        listeners.map((listener) => ({
            event_type: listener.event_type,
            name: listener.name,
            selector: listener.selector,
        }))
    );
}

function clearCustomEventListeners(context, cy) {
    (context.customEventBindings || []).forEach((binding) => {
        cy.off(binding.event_type, binding.selector, binding.handler);
    });
    context.customEventBindings = [];
}

function syncCustomEventListeners(context, cy, listeners = []) {
    const signature = customEventSignature(listeners);
    if (context.customEventSignature === signature) {
        return;
    }

    clearCustomEventListeners(context, cy);
    context.customEventSignature = signature;

    listeners.forEach((listener) => {
        const handler = (event) => emitCustomEvent(context, listener, event);
        cy.on(listener.event_type, listener.selector, handler);
        context.customEventBindings.push({
            event_type: listener.event_type,
            selector: listener.selector,
            handler,
        });
    });
}

function suppressLayoutPositionEvent(context) {
    context.suppressedLayoutPositionEvents =
        (context.suppressedLayoutPositionEvents || 0) + 1;
}

function consumeSuppressedLayoutPositionEvent(context) {
    const pending = context.suppressedLayoutPositionEvents || 0;
    if (pending <= 0) {
        return false;
    }

    context.suppressedLayoutPositionEvents = pending - 1;
    return true;
}

function isActiveElement(element) {
    return Boolean(
        element &&
            !element.empty?.() &&
            element.inside?.() &&
            element.selected?.()
    );
}

// Event handlers
function syncSelectionState(context, cy, latestSelected) {
    const selected = cy.$(":selected");
    let lastSelected = latestSelected;

    if (!isActiveElement(lastSelected)) {
        const currentSelection = context.state.getState("selection");
        lastSelected = currentSelection.lastSelected;
    }

    if (!isActiveElement(lastSelected)) {
        lastSelected = selected.length === 1 ? selected.first() : null;
    }

    if (selected.length === 0) {
        lastSelected = null;
    }

    const selection = { selected, lastSelected };
    context.state.updateState("selection", selection);
    emitSelection(context, cy, selection.lastSelected);
    context.getElementById("container")?.focus();
}

// Initailize cytoscape (only runs once)
function initCyto(context, listeners) {
    const selectionMode = context.options.selectionMode || "single";
    const cy = cytoscape(getInitOptions(context, selectionMode));
    context.setCyInstance(cy);
    context.defaultMinZoom = cy.minZoom();
    context.defaultMaxZoom = cy.maxZoom();
    let latestSelected = null;
    const syncSelection = debounce(
        (cyInstance) => syncSelectionState(context, cyInstance, latestSelected),
        SELECT_DEBOUNCE
    );
    cy.on("select unselect", (e) => {
        if (e.type === "select") {
            latestSelected = e.target;
        } else if (latestSelected?.same(e.target)) {
            latestSelected = null;
        }
        syncSelection(e.cy);
    });
    cy.on("drag", "node", () => {
        context.suppressSelectionEmitUntil =
            Date.now() + DRAG_SELECTION_SUPPRESS_MS;
    });
    syncCustomEventListeners(context, cy, listeners);
    initBoxSelection(context, cy);
    context.addCleanup?.(() => clearCustomEventListeners(context, cy));
    const emitDragPositions = debounce(
        () =>
            emitPositions(context, cy, {
                respectSuppression: false,
                movement: context.consumeDragMovement?.() || null,
            }),
        POSITION_DEBOUNCE
    );
    const emitLayoutPositions = debounce(() => {
        if (!consumeSuppressedLayoutPositionEvent(context)) {
            emitPositions(context, cy);
        }
    }, POSITION_DEBOUNCE);
    cy.on("dragfree", emitDragPositions);
    cy.on("layoutstop", emitLayoutPositions);
    return cy;
}

// Callbacks for state changes
function createGraph(context) {
    return {
        updateHighlight: function () {
            const cy = context.getCyInstance();
            const el = context.state.getState("selection").lastSelected;
            cy.$(".highlight").removeClass("highlight");
            if (!el?.inside?.()) {
                return;
            }
            const g = el?.group();
            if (g == "nodes") {
                el.connectedEdges().addClass("highlight");
            } else if (g == "edges") {
                el.connectedNodes().addClass("highlight");
            }
        },
        updateLayout: function () {
            const cy = context.getCyInstance();
            runLayout(context, cy, context.state.getState("layout"));
        },
        updateStyle: function () {
            const cy = context.getCyInstance();
            const { theme, custom_style } = context.state.getState("style");
            const style = getStyles(
                theme,
                custom_style,
                context.options.performanceProfile
            );
            context
                .getElementById("container")
                ?.setAttribute("data-theme", theme);
            cy.style(style);
        },
    };
}

export default initCyto;
export {
    createGraph,
    suppressLayoutPositionEvent,
    syncCustomEventListeners,
    syncGraphOptions,
    syncSelectionState,
};
