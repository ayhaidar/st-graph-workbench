import { getCrudPayload } from "../utils/payloads.js";
import { setButtonState } from "../utils/dom.js";

const IDS = {
    group: "crudControls",
    createNode: "crudCreateNode",
    createEdge: "crudCreateEdge",
    readSelected: "crudReadSelected",
    updateSelected: "crudUpdateSelected",
    deleteSelected: "crudDeleteSelected",
    requestNodeData: "crudRequestNodeData",
};

const ACTION_TO_ID = {
    create_node: IDS.createNode,
    create_edge: IDS.createEdge,
    read_selected: IDS.readSelected,
    update_selected: IDS.updateSelected,
    delete_selected: IDS.deleteSelected,
    request_node_data: IDS.requestNodeData,
};

const BUTTON_TITLES = {
    create_node: "Add Node",
    create_edge: "Add Edge",
    read_selected: "Read Selected",
    update_selected: "Update Selected",
    delete_selected: "Delete Selected",
    request_node_data: "Load Related Data",
};

const DISABLED_TITLES = {
    create_edge: "Select at least one node to add an edge",
    read_selected: "Select elements to read",
    update_selected: "Select one element to update",
    delete_selected: "Select elements to delete",
    request_node_data: "Select one node to load related data",
};

function selectedVisibleElements(cy) {
    return cy.elements(":selected").filter(":visible");
}

function canRun(action, selected) {
    const selectedNodes = selected.nodes();
    const selectedCount = selected.length;

    if (action === "create_node") {
        return true;
    }
    if (action === "create_edge") {
        return selectedNodes.length > 0;
    }
    if (action === "read_selected" || action === "delete_selected") {
        return selectedCount > 0;
    }
    if (action === "update_selected") {
        return selectedCount === 1;
    }
    if (action === "request_node_data") {
        return selectedNodes.length === 1 && selectedCount === 1;
    }
    return false;
}

function updateCrudControls(context, activeActions) {
    const cy = context.getCyInstance();
    const group = context.getElementById(IDS.group);
    const selected = selectedVisibleElements(cy);

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
        const enabled = isActive && canRun(action, selected);
        button.hidden = !isActive;
        setButtonState(button, {
            enabled: enabled,
            title: enabled
                ? BUTTON_TITLES[action]
                : DISABLED_TITLES[action] || BUTTON_TITLES[action],
        });
    });
}

function refreshActiveActions(context, activeActions) {
    activeActions.clear();
    (context.options.crudActions || []).forEach((action) => {
        activeActions.add(action);
    });
}

function emitCrud(context, operation) {
    const cy = context.getCyInstance();
    const lastSelected = context.state.getState("selection").lastSelected;
    context.setImmediateStreamlitValue({
        action: "crud",
        data: getCrudPayload(cy, operation, lastSelected),
        timestamp: Date.now(),
    });
}

function initCrud(context) {
    const activeActions = new Set();
    const group = context.getElementById(IDS.group);
    if (!group) {
        return () => {};
    }

    Object.entries(ACTION_TO_ID).forEach(([action, id]) => {
        context.getElementById(id)?.addEventListener("click", () => {
            refreshActiveActions(context, activeActions);
            if (!activeActions.has(action)) {
                return;
            }
            emitCrud(context, action);
        });
    });

    const update = () => {
        refreshActiveActions(context, activeActions);
        updateCrudControls(context, activeActions);
    };
    context.state.subscribe("selection", update);
    context.getCyInstance().on("select unselect", update);
    update();
    return update;
}

export default initCrud;
