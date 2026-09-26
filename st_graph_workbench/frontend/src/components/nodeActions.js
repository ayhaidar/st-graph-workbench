import { getExpansionAction } from "../utils/expansion.js";
import { runLayout } from "../utils/layouts.js";

// Configs
const IDS = {
    remove: "nodeActionsRemove",
    expand: "nodeActionsExpand",
    neighbors: "nodeActionsNeighbors",
    incoming: "nodeActionsIncoming",
    outgoing: "nodeActionsOutgoing",
    contextMenu: "graphContextMenu",
    contextMenuExpand: "graphContextMenuExpand",
};
const DOUBLE_TAP_MS = 500;
const EXPAND_DUPLICATE_SUPPRESSION_MS = 350;
const POSITION_SUPPRESSION_MS = 1400;
const REMOVE_SELECTION_SUPPRESSION_MS = 350;
const expandLayout = {
    name: "fcose",
    animationDuration: 500,
    randomize: false,
    fit: false,
    nodeDimensionsIncludeLabels: true,
    uniformNodeDimensions: true,
    numIter: 50,
    tile: false,
};

function getContextMenu(context) {
    return context.getElementById(IDS.contextMenu);
}

function getContextMenuExpandButton(context) {
    return context.getElementById(IDS.contextMenuExpand);
}

function hideContextMenu(context) {
    const menu = getContextMenu(context);
    if (!menu) {
        return;
    }
    menu.hidden = true;
    delete menu.dataset.nodeId;
}

function placeContextMenu(context, renderedPosition) {
    const menu = getContextMenu(context);
    const container = context.getElementById("container");
    const cyLayer = context.getElementById("cy");
    if (!menu || !container || !cyLayer || !renderedPosition) {
        return;
    }

    menu.hidden = false;
    const margin = 8;
    const maxLeft = Math.max(
        margin,
        container.clientWidth - menu.offsetWidth - margin
    );
    const maxTop = Math.max(
        margin,
        container.clientHeight - menu.offsetHeight - margin
    );
    const left = Math.min(
        Math.max(renderedPosition.x + margin, margin),
        maxLeft
    );
    const top = Math.min(
        Math.max(renderedPosition.y + cyLayer.offsetTop + margin, margin),
        maxTop
    );
    menu.style.left = `${left}px`;
    menu.style.top = `${top}px`;
}

function emitExpand(context, node) {
    if (!node || node.empty?.()) {
        return;
    }
    if (!getExpansionAction(node.data())) {
        return;
    }

    const now = Date.now();
    const previous = context.lastExpandEmit || {};
    if (
        previous.nodeId === node.id() &&
        now - previous.timestamp < EXPAND_DUPLICATE_SUPPRESSION_MS
    ) {
        return;
    }

    context.lastExpandEmit = { nodeId: node.id(), timestamp: now };
    context.suppressPositionEmitUntil = now + POSITION_SUPPRESSION_MS;
    context.setImmediateStreamlitValue({
        action: "expand",
        data: { node_ids: [node.id()] },
        timestamp: now,
    });
    context.state.updateState("lastExpanded", node);
}

function hasNodeAction(context, action) {
    return (context.options.nodeActions || []).includes(action);
}

function runIfNodeActionEnabled(context, action, runner) {
    if (!hasNodeAction(context, action)) {
        return;
    }
    runner();
}

function showContextMenu(context, node, renderedPosition) {
    const menu = getContextMenu(context);
    const expand = getContextMenuExpandButton(context);
    const expansionAction = getExpansionAction(node.data());
    if (!menu || !expand || !hasNodeAction(context, "expand")) {
        return;
    }

    menu.dataset.nodeId = node.id();
    expand.textContent = expansionAction?.label || "No expansion available";
    expand.disabled = !expansionAction;
    expand.setAttribute("aria-disabled", String(!expansionAction));
    expand.setAttribute("title", expand.textContent);
    placeContextMenu(context, renderedPosition);
    expand.focus();
}

function animateNeighbors(parent, neighbors, context) {
    const pos = parent.position();
    const layout = {
        ...expandLayout,
        fixedNodeConstraint: [
            {
                nodeId: parent.id(),
                position: pos,
            },
        ],
    };
    neighbors.position(pos);
    neighbors.addClass("highlight");
    parent.connectedEdges().addClass("highlight");
    runLayout(context, context.getCyInstance(), layout);
}

function selectedNodes(context) {
    return context.getCyInstance().nodes(":selected");
}

function selectedVisibleNodes(context) {
    return selectedNodes(context).filter(":visible");
}

function firstSelectedNode(context) {
    const visibleNodes = selectedVisibleNodes(context);
    if (visibleNodes?.length > 0) {
        return visibleNodes.first();
    }

    const nodes = selectedNodes(context);
    if (nodes?.length > 0) {
        return nodes.first();
    }

    return null;
}

function _handleRemove(context) {
    const nodes = selectedNodes(context);
    if (nodes?.length > 0) {
        const nodeIds = nodes.map((n) => {
            return n.id();
        });
        const now = Date.now();
        context.suppressSelectionEmitUntil =
            now + REMOVE_SELECTION_SUPPRESSION_MS;
        context.setImmediateStreamlitValue({
            action: "remove",
            data: {
                node_ids: nodeIds,
            },
            timestamp: now,
        });
        nodes.remove();
        context.updateGraphStats?.();
        context.updateSelectionControls?.();
        nodes.unselect();
        context.state.updateState("lastExpanded", false);
    }
}

function _handleExpand(context, targetNode = null) {
    if (!hasNodeAction(context, "expand")) {
        return;
    }

    let node = targetNode?.filter?.("node");

    if (!node || node.group() != "nodes") {
        node = firstSelectedNode(context);
    }

    if (!node || node.group() != "nodes") {
        node = context.state.getState("selection").lastSelected?.filter("node");
    }

    if (node?.group() == "nodes") {
        emitExpand(context, node);
    }
}

function _handleNodeTap(context, node) {
    if (!node || node.empty?.() || !hasNodeAction(context, "expand")) {
        return;
    }

    const now = Date.now();
    const previous = context.lastNodeTap || {};
    context.lastNodeTap = { nodeId: node.id(), timestamp: now };

    if (
        previous.nodeId === node.id() &&
        now - previous.timestamp <= DOUBLE_TAP_MS
    ) {
        emitExpand(context, node);
    }
}

function emitVisibility(context, operation) {
    const cy = context.getCyInstance();
    context.setImmediateStreamlitValue({
        action: "visibility",
        data: {
            operation: operation,
            visible_node_ids: cy.nodes(":visible").map((node) => node.id()),
            visible_edge_ids: cy.edges(":visible").map((edge) => edge.id()),
        },
        timestamp: Date.now(),
    });
}

function _handleNeighborhood(context, operation) {
    const cy = context.getCyInstance();
    const nodes = selectedVisibleNodes(context);
    if (!nodes || nodes.length === 0) {
        return;
    }

    let visible;
    if (operation === "show_incoming") {
        visible = nodes.union(nodes.incomers());
    } else if (operation === "show_outgoing") {
        visible = nodes.union(nodes.outgoers());
    } else {
        visible = nodes.union(nodes.neighborhood());
    }

    cy.elements().hide();
    visible.show();
    context.updateGraphStats?.();
    context.updateSelectionControls?.();
    emitVisibility(context, operation);
}

function initNodeActions(context) {
    const nodeActionsHandlers = {
        remove: () =>
            runIfNodeActionEnabled(context, "remove", () =>
                _handleRemove(context)
            ),
        expand: () => _handleExpand(context),
        show_neighbors: () =>
            runIfNodeActionEnabled(context, "show_neighbors", () =>
                _handleNeighborhood(context, "show_neighbors")
            ),
        show_incoming: () =>
            runIfNodeActionEnabled(context, "show_incoming", () =>
                _handleNeighborhood(context, "show_incoming")
            ),
        show_outgoing: () =>
            runIfNodeActionEnabled(context, "show_outgoing", () =>
                _handleNeighborhood(context, "show_outgoing")
            ),
    };

    const remove = context.getElementById(IDS.remove);
    remove?.addEventListener("click", nodeActionsHandlers.remove);

    const container = context.getElementById("container");
    container?.addEventListener("keydown", (e) => {
        if (["Delete", "Backspace"].includes(e.key)) {
            nodeActionsHandlers.remove();
        }
        if (e.key === "Escape") {
            hideContextMenu(context);
        }
    });
    container?.setAttribute("tabindex", "0");

    const expand = context.getElementById(IDS.expand);
    expand?.addEventListener("click", nodeActionsHandlers.expand);
    const contextMenuExpand = getContextMenuExpandButton(context);
    contextMenuExpand?.addEventListener("click", () => {
        runIfNodeActionEnabled(context, "expand", () => {
            const nodeId = getContextMenu(context)?.dataset.nodeId;
            const node = nodeId
                ? context.getCyInstance().getElementById(nodeId)
                : null;
            if (node && getExpansionAction(node.data())) {
                hideContextMenu(context);
                emitExpand(context, node);
            }
        });
    });
    context.getElementById("cy")?.addEventListener("contextmenu", (e) => {
        if (hasNodeAction(context, "expand") || context.options.expansion) {
            e.preventDefault();
        }
    });
    context.getCyInstance().on("tap", "node", (event) => {
        _handleNodeTap(context, event.target);
    });
    context.getCyInstance().on("dblclick dbltap", "node", (event) => {
        _handleExpand(context, event.target);
    });
    context.getCyInstance().on("cxttap", "node", (event) => {
        if (context.options.expansion) {
            event.originalEvent?.preventDefault?.();
            context.showExpansionMenu(
                event.target,
                event.renderedPosition || event.target.renderedPosition()
            );
            return;
        }
        runIfNodeActionEnabled(context, "expand", () => {
            event.originalEvent?.preventDefault?.();
            const node = event.target;
            const cy = context.getCyInstance();
            cy.elements(":selected").unselect();
            node.select();
            context.refreshGraphUi?.(node);
            showContextMenu(
                context,
                node,
                event.renderedPosition || node.renderedPosition()
            );
        });
    });
    context.getCyInstance().on("tap drag pan zoom", (event) => {
        if (event.type === "tap" && event.target !== context.getCyInstance()) {
            return;
        }
        hideContextMenu(context);
    });

    const neighbors = context.getElementById(IDS.neighbors);
    neighbors?.addEventListener("click", nodeActionsHandlers.show_neighbors);

    const incoming = context.getElementById(IDS.incoming);
    incoming?.addEventListener("click", nodeActionsHandlers.show_incoming);

    const outgoing = context.getElementById(IDS.outgoing);
    outgoing?.addEventListener("click", nodeActionsHandlers.show_outgoing);
}

export { animateNeighbors };
export default initNodeActions;
