import { setButtonState } from "../utils/dom.js";

const IDS = {
    group: "editControls",
    addNode: "editAddNode",
    connectSelected: "editConnectSelected",
    deleteSelected: "editDeleteSelected",
    lockSelected: "editLockSelected",
    unlockSelected: "editUnlockSelected",
    makeUngrabbable: "editMakeUngrabbable",
    makeGrabbable: "editMakeGrabbable",
    snapToGrid: "editSnapToGrid",
    undo: "editUndo",
    redo: "editRedo",
};

const ACTION_TO_ID = {
    add_node: IDS.addNode,
    connect_selected: IDS.connectSelected,
    delete_selected: IDS.deleteSelected,
    lock_selected: IDS.lockSelected,
    unlock_selected: IDS.unlockSelected,
    make_ungrabbable: IDS.makeUngrabbable,
    make_grabbable: IDS.makeGrabbable,
    snap_to_grid: IDS.snapToGrid,
    undo: IDS.undo,
    redo: IDS.redo,
};

const TITLES = {
    add_node: "Add Browser Node",
    connect_selected: "Connect Two Selected Nodes",
    delete_selected: "Delete Selected",
    lock_selected: "Lock Selected Nodes",
    unlock_selected: "Unlock Selected Nodes",
    make_ungrabbable: "Make Selected Nodes Fixed",
    make_grabbable: "Make Selected Nodes Draggable",
    snap_to_grid: "Snap Nodes to Grid",
    undo: "Undo Browser Edit",
    redo: "Redo Browser Edit",
};

const DISABLED_TITLES = {
    connect_selected: "Select exactly two nodes to connect",
    delete_selected: "Select nodes or edges to delete",
    lock_selected: "Select nodes to lock",
    unlock_selected: "Select nodes to unlock",
    make_ungrabbable: "Select nodes to make fixed",
    make_grabbable: "Select nodes to make draggable",
    snap_to_grid: "No visible nodes to snap",
    undo: "No browser edit to undo",
    redo: "No browser edit to redo",
};

const GRID_SIZE = 40;
const SELECTION_SUPPRESSION_MS = 350;
const POSITION_SUPPRESSION_MS = 900;
function asJsons(collection) {
    return collection.jsons ? collection.jsons() : [];
}

function ids(collection) {
    return collection.map((element) => element.id()).sort();
}

function selectedVisible(cy) {
    return cy.elements(":selected").filter(":visible");
}

function graphCounts(cy) {
    return {
        visible_nodes: cy.nodes(":visible").length,
        hidden_nodes: cy.nodes(":hidden").length,
        total_nodes: cy.nodes().length,
        visible_edges: cy.edges(":visible").length,
        hidden_edges: cy.edges(":hidden").length,
        total_edges: cy.edges().length,
    };
}

function normalizeElements(elements) {
    if (Array.isArray(elements)) {
        return elements;
    }
    return [...(elements?.nodes || []), ...(elements?.edges || [])];
}

function sortElements(elements) {
    return [
        ...elements.filter((element) => element.group !== "edges"),
        ...elements.filter((element) => element.group === "edges"),
    ];
}

function maxHistory(context) {
    const profile = context.options.performanceProfile;
    if (profile === "dense") {
        return 8;
    }
    if (profile === "large") {
        return 16;
    }
    return 40;
}

function snapshot(cy) {
    return {
        elements: cy.elements().jsons(),
        pan: cy.pan(),
        zoom: cy.zoom(),
    };
}

function restoreSnapshot(cy, snap) {
    cy.batch(() => {
        cy.elements().remove();
        cy.add(sortElements(normalizeElements(snap.elements)));
    });
    cy.viewport({ pan: snap.pan, zoom: snap.zoom });
}

function createHistory(context) {
    return {
        undoStack: [],
        redoStack: [],
        nextId: 1,
        push(cy) {
            this.undoStack.push(snapshot(cy));
            const limit = maxHistory(context);
            if (this.undoStack.length > limit) {
                this.undoStack.shift();
            }
            this.redoStack = [];
        },
        undo(cy) {
            if (this.undoStack.length === 0) {
                return null;
            }
            this.redoStack.push(snapshot(cy));
            const previous = this.undoStack.pop();
            restoreSnapshot(cy, previous);
            return previous;
        },
        redo(cy) {
            if (this.redoStack.length === 0) {
                return null;
            }
            this.undoStack.push(snapshot(cy));
            const next = this.redoStack.pop();
            restoreSnapshot(cy, next);
            return next;
        },
    };
}

function uniqueElementId(cy, history, prefix) {
    let id = `${prefix}-${history.nextId}`;
    history.nextId += 1;
    while (cy.getElementById(id).length > 0) {
        id = `${prefix}-${history.nextId}`;
        history.nextId += 1;
    }
    return id;
}

function selectedNodeIds(cy) {
    return ids(cy.nodes(":selected"));
}

function selectedEdgeIds(cy) {
    return ids(cy.edges(":selected"));
}

function emitEdit(context, operation, data = {}) {
    const cy = context.getCyInstance();
    suppressPositionEvents(context);
    context.setImmediateStreamlitValue({
        action: "edit",
        data: {
            operation,
            selected_node_ids: selectedNodeIds(cy),
            selected_edge_ids: selectedEdgeIds(cy),
            graph_counts: graphCounts(cy),
            ...data,
        },
        timestamp: Date.now(),
    });
}

function suppressSelectionEvents(context) {
    context.suppressSelectionEmitUntil = Date.now() + SELECTION_SUPPRESSION_MS;
}

function suppressPositionEvents(context) {
    context.suppressPositionEmitUntil = Date.now() + POSITION_SUPPRESSION_MS;
}

function refresh(context, latestSelected = null) {
    context.refreshGraphUi?.(latestSelected);
}

function addNode(context, history) {
    const cy = context.getCyInstance();
    const extent = cy.extent();
    const id = uniqueElementId(cy, history, "node");
    const node = {
        group: "nodes",
        data: {
            id,
            label: "NODE",
            name: id,
        },
        position: {
            x: (extent.x1 + extent.x2) / 2,
            y: (extent.y1 + extent.y2) / 2,
        },
    };

    suppressSelectionEvents(context);
    history.push(cy);
    let added;
    cy.batch(() => {
        cy.elements().unselect();
        added = cy.add(node);
        added.select();
    });
    refresh(context, added);
    emitEdit(context, "add_node", {
        added_elements: asJsons(added),
    });
}

function connectSelected(context, history) {
    const cy = context.getCyInstance();
    const selected = cy.nodes(":selected").filter(":visible");
    if (selected.length !== 2) {
        return;
    }

    suppressSelectionEvents(context);
    const source = selected.first().id();
    const target = selected.last().id();
    const id = uniqueElementId(cy, history, `edge-${source}-${target}`);
    const edge = {
        group: "edges",
        data: {
            id,
            label: "RELATED",
            source,
            target,
        },
    };

    history.push(cy);
    const added = cy.add(edge);
    refresh(context);
    emitEdit(context, "connect_selected", {
        added_elements: asJsons(added),
        source_id: source,
        target_id: target,
    });
}

function deleteSelected(context, history) {
    const cy = context.getCyInstance();
    const selected = selectedVisible(cy);
    if (selected.length === 0) {
        return;
    }

    const incidentEdges = selected.nodes().connectedEdges();
    const toRemove = selected.union(incidentEdges);
    const deletedNodeIds = ids(toRemove.nodes());
    const deletedEdgeIds = ids(toRemove.edges());

    suppressSelectionEvents(context);
    history.push(cy);
    toRemove.remove();
    refresh(context);
    emitEdit(context, "delete_selected", {
        deleted_node_ids: deletedNodeIds,
        deleted_edge_ids: deletedEdgeIds,
        remove_incident_edges: true,
    });
}

function setNodeLocked(context, history, locked) {
    const cy = context.getCyInstance();
    const nodes = cy.nodes(":selected").filter(":visible");
    if (nodes.length === 0) {
        return;
    }

    suppressSelectionEvents(context);
    history.push(cy);
    if (locked) {
        nodes.lock();
    } else {
        nodes.unlock();
    }
    refresh(context);
    emitEdit(context, locked ? "lock_selected" : "unlock_selected", {
        updated_elements: asJsons(nodes),
    });
}

function setNodeGrabbable(context, history, grabbable) {
    const cy = context.getCyInstance();
    const nodes = cy.nodes(":selected").filter(":visible");
    if (nodes.length === 0) {
        return;
    }

    suppressSelectionEvents(context);
    history.push(cy);
    if (grabbable) {
        nodes.grabify();
    } else {
        nodes.ungrabify();
    }
    refresh(context);
    emitEdit(context, grabbable ? "make_grabbable" : "make_ungrabbable", {
        updated_elements: asJsons(nodes),
    });
}

function snapToGrid(context, history) {
    const cy = context.getCyInstance();
    const selectedNodes = cy.nodes(":selected").filter(":visible");
    const nodes =
        selectedNodes.length > 0 ? selectedNodes : cy.nodes(":visible");
    if (nodes.length === 0) {
        return;
    }

    suppressSelectionEvents(context);
    history.push(cy);
    nodes.positions((node) => {
        const position = node.position();
        return {
            x: Math.round(position.x / GRID_SIZE) * GRID_SIZE,
            y: Math.round(position.y / GRID_SIZE) * GRID_SIZE,
        };
    });
    refresh(context);
    emitEdit(context, "snap_to_grid", {
        positions: nodes.map((node) => ({
            id: node.id(),
            position: node.position(),
        })),
    });
}

function undo(context, history) {
    const cy = context.getCyInstance();
    suppressSelectionEvents(context);
    const restored = history.undo(cy);
    if (!restored) {
        return;
    }
    refresh(context);
    emitEdit(context, "undo", {
        elements: cy.json().elements,
        restored_counts: graphCounts(cy),
    });
}

function redo(context, history) {
    const cy = context.getCyInstance();
    suppressSelectionEvents(context);
    const restored = history.redo(cy);
    if (!restored) {
        return;
    }
    refresh(context);
    emitEdit(context, "redo", {
        elements: cy.json().elements,
        restored_counts: graphCounts(cy),
    });
}

function canRun(action, cy, history) {
    const selected = selectedVisible(cy);
    const selectedNodes = selected.nodes();

    if (action === "add_node") {
        return true;
    }
    if (action === "connect_selected") {
        return selectedNodes.length === 2;
    }
    if (action === "delete_selected") {
        return selected.length > 0;
    }
    if (
        action === "lock_selected" ||
        action === "unlock_selected" ||
        action === "make_ungrabbable" ||
        action === "make_grabbable"
    ) {
        return selectedNodes.length > 0;
    }
    if (action === "snap_to_grid") {
        return cy.nodes(":visible").length > 0;
    }
    if (action === "undo") {
        return history.undoStack.length > 0;
    }
    if (action === "redo") {
        return history.redoStack.length > 0;
    }
    return false;
}

function updateEditControls(context, activeActions, history) {
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
        const enabled = isActive && canRun(action, cy, history);
        button.hidden = !isActive;
        setButtonState(button, {
            enabled,
            title: enabled
                ? TITLES[action]
                : DISABLED_TITLES[action] || TITLES[action],
        });
    });
}

function bindAction(context, activeActions, history, action, callback) {
    const button = context.getElementById(ACTION_TO_ID[action]);
    button?.addEventListener("click", () => {
        if (!activeActions.has(action)) {
            return;
        }
        callback(context, history);
        updateEditControls(context, activeActions, history);
    });
}

function initEditTools(context) {
    const activeActions = new Set(context.options.editActions || []);
    const history = createHistory(context);

    bindAction(context, activeActions, history, "add_node", addNode);
    bindAction(
        context,
        activeActions,
        history,
        "connect_selected",
        connectSelected
    );
    bindAction(
        context,
        activeActions,
        history,
        "delete_selected",
        deleteSelected
    );
    bindAction(context, activeActions, history, "lock_selected", (ctx, hist) =>
        setNodeLocked(ctx, hist, true)
    );
    bindAction(
        context,
        activeActions,
        history,
        "unlock_selected",
        (ctx, hist) => setNodeLocked(ctx, hist, false)
    );
    bindAction(
        context,
        activeActions,
        history,
        "make_ungrabbable",
        (ctx, hist) => setNodeGrabbable(ctx, hist, false)
    );
    bindAction(context, activeActions, history, "make_grabbable", (ctx, hist) =>
        setNodeGrabbable(ctx, hist, true)
    );
    bindAction(context, activeActions, history, "snap_to_grid", snapToGrid);
    bindAction(context, activeActions, history, "undo", undo);
    bindAction(context, activeActions, history, "redo", redo);

    const update = () => {
        activeActions.clear();
        (context.options.editActions || []).forEach((action) =>
            activeActions.add(action)
        );
        updateEditControls(context, activeActions, history);
    };

    context.state.subscribe("selection", update);
    context.getCyInstance().on("select unselect add remove position", update);
    update();
    return update;
}

export default initEditTools;
