import { setButtonState } from "../utils/dom.js";

const IDS = {
    group: "viewportControls",
    toggleZoom: "viewportToggleZoom",
    togglePan: "viewportTogglePan",
    save: "viewportSave",
    restore: "viewportRestore",
    reset: "viewportReset",
};

const ACTION_TO_ID = {
    toggle_zoom: IDS.toggleZoom,
    toggle_pan: IDS.togglePan,
    save_viewport: IDS.save,
    restore_viewport: IDS.restore,
    reset_viewport: IDS.reset,
};

const TITLES = {
    toggle_zoom: "Disable User Zoom",
    toggle_pan: "Disable User Pan",
    save_viewport: "Save Current View",
    restore_viewport: "Restore Saved View",
    reset_viewport: "Reset View",
};

const DISABLED_TITLES = {
    restore_viewport: "Save a view before restoring it",
};

function emitViewport(context, operation, data = {}) {
    const cy = context.getCyInstance();
    context.setImmediateStreamlitValue({
        action: "viewport",
        data: {
            operation,
            pan: cy.pan(),
            zoom: cy.zoom(),
            ...data,
        },
        timestamp: Date.now(),
    });
}

function canRun(action, savedViewport) {
    if (action === "restore_viewport") {
        return Boolean(savedViewport);
    }
    return true;
}

function updateViewportControls(context, activeActions, state) {
    const cy = context.getCyInstance();
    const group = context.getElementById(IDS.group);

    if (!group) {
        return;
    }

    group.hidden = activeActions.size === 0;
    Object.entries(ACTION_TO_ID).forEach(([action, id]) => {
        const button = context.getElementById(id);
        if (!button) {
            return;
        }
        const isActive = activeActions.has(action);
        const enabled = isActive && canRun(action, state.savedViewport);
        button.hidden = !isActive;

        if (action === "toggle_zoom") {
            const zoomEnabled = cy.userZoomingEnabled();
            setButtonState(button, {
                enabled,
                title: zoomEnabled ? "Disable User Zoom" : "Enable User Zoom",
                pressed: zoomEnabled,
            });
            return;
        }

        if (action === "toggle_pan") {
            const panEnabled = cy.userPanningEnabled();
            setButtonState(button, {
                enabled,
                title: panEnabled ? "Disable User Pan" : "Enable User Pan",
                pressed: panEnabled,
            });
            return;
        }

        setButtonState(button, {
            enabled,
            title: enabled
                ? TITLES[action]
                : DISABLED_TITLES[action] || TITLES[action],
        });
    });
}

function bindAction(context, activeActions, state, action, callback) {
    const button = context.getElementById(ACTION_TO_ID[action]);
    button?.addEventListener("click", () => {
        if (!activeActions.has(action)) {
            return;
        }
        callback(context, state);
        updateViewportControls(context, activeActions, state);
    });
}

function toggleZoom(context) {
    const cy = context.getCyInstance();
    cy.userZoomingEnabled(!cy.userZoomingEnabled());
}

function togglePan(context) {
    const cy = context.getCyInstance();
    cy.userPanningEnabled(!cy.userPanningEnabled());
}

function saveViewport(context, state) {
    const cy = context.getCyInstance();
    const pan = cy.pan();
    state.savedViewport = {
        pan: {
            x: pan.x,
            y: pan.y,
        },
        zoom: cy.zoom(),
    };
    emitViewport(context, "save_viewport", {
        saved_viewport: state.savedViewport,
    });
}

function restoreViewport(context, state) {
    const cy = context.getCyInstance();
    if (!state.savedViewport) {
        return;
    }
    cy.animate({
        pan: state.savedViewport.pan,
        zoom: { level: state.savedViewport.zoom },
        duration: 180,
    });
    emitViewport(context, "restore_viewport", {
        restored_viewport: state.savedViewport,
    });
}

function resetViewport(context) {
    const cy = context.getCyInstance();
    cy.reset();
    emitViewport(context, "reset_viewport");
}

function initViewportTools(context) {
    const activeActions = new Set(context.options.viewportActions || []);
    const state = {
        savedViewport: null,
    };

    bindAction(context, activeActions, state, "toggle_zoom", toggleZoom);
    bindAction(context, activeActions, state, "toggle_pan", togglePan);
    bindAction(context, activeActions, state, "save_viewport", saveViewport);
    bindAction(
        context,
        activeActions,
        state,
        "restore_viewport",
        restoreViewport
    );
    bindAction(context, activeActions, state, "reset_viewport", resetViewport);

    const update = () => {
        activeActions.clear();
        (context.options.viewportActions || []).forEach((action) =>
            activeActions.add(action)
        );
        updateViewportControls(context, activeActions, state);
    };

    context.getCyInstance().on("zoom pan", update);
    update();
    return update;
}

export default initViewportTools;
