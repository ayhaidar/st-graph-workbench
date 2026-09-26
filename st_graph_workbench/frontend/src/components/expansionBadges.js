import { getExpansionBadge } from "../utils/expansion.js";

const BADGE_LAYER_ID = "expansionBadges";

function getBadgeLayer(context) {
    return context.getElementById(BADGE_LAYER_ID);
}

function updateBadgeLayerVisibility(context) {
    const layer = getBadgeLayer(context);
    if (!layer) {
        return;
    }
    layer.dataset.visible = context.state.getState("expansionBadgesVisible");
}

function getNodeBadgePosition(node) {
    const box = node.renderedBoundingBox({
        includeLabels: false,
        includeOverlays: false,
    });
    return {
        x: box.x2,
        y: box.y1,
    };
}

function getBadgeElement(layer, badgeElements, nodeId) {
    let badge = badgeElements.get(nodeId);
    if (!badge || !badge.isConnected) {
        badge = document.createElement("div");
        badge.className = "expansion-badge";
        badge.dataset.nodeId = nodeId;
        badgeElements.set(nodeId, badge);
    }
    if (badge.parentElement !== layer) {
        layer.appendChild(badge);
    }
    return badge;
}

function removeStaleBadges(badgeElements, activeNodeIds) {
    badgeElements.forEach((badge, nodeId) => {
        if (!activeNodeIds.has(nodeId)) {
            badge.remove();
            badgeElements.delete(nodeId);
        }
    });
}

function syncExpansionBadges(context, badgeElements, cy, animationFrameState) {
    animationFrameState.current = null;
    const layer = getBadgeLayer(context);
    if (!cy || cy.destroyed?.() || !layer) {
        return;
    }

    const activeNodeIds = new Set();
    cy.nodes(":visible").forEach((node) => {
        const managed = context.options.expansion?.nodes[node.id()];
        let expansionBadge = getExpansionBadge(node.data());
        if (context.options.expansion) {
            expansionBadge = null;
            if (
                managed?.can_expand ||
                managed?.can_load_more ||
                managed?.can_collapse
            ) {
                const collapse = managed.can_collapse && !managed.can_load_more;
                const nodes = collapse
                    ? managed.collapse_nodes
                    : managed.next_nodes;
                const edges = collapse
                    ? managed.collapse_edges
                    : managed.next_edges;
                if (nodes || edges || nodes === null) {
                    expansionBadge = {
                        state: collapse ? "expanded" : "collapsed",
                        label: `${collapse ? "-" : "+"}${nodes ?? "?"}n/${edges ?? "?"}e`,
                    };
                }
            }
        }
        if (!expansionBadge) {
            return;
        }

        const nodeId = node.id();
        const badge = getBadgeElement(layer, badgeElements, nodeId);
        const position = getNodeBadgePosition(node);

        activeNodeIds.add(nodeId);
        badge.dataset.state = expansionBadge.state;
        badge.textContent = expansionBadge.label;
        badge.style.left = `${position.x}px`;
        badge.style.top = `${position.y}px`;
    });

    removeStaleBadges(badgeElements, activeNodeIds);
}

function createBadgeUpdater(context, badgeElements, cy) {
    const animationFrameState = { current: null };
    function updateExpansionBadges() {
        if (animationFrameState.current) {
            return;
        }
        animationFrameState.current = requestAnimationFrame(() =>
            syncExpansionBadges(context, badgeElements, cy, animationFrameState)
        );
    }

    updateExpansionBadges.cancel = function () {
        if (animationFrameState.current) {
            cancelAnimationFrame(animationFrameState.current);
            animationFrameState.current = null;
        }
        badgeElements.forEach((badge) => badge.remove());
        badgeElements.clear();
    };

    return updateExpansionBadges;
}

function initExpansionBadges(context) {
    const cy = context.getCyInstance();
    const badgeElements = new Map();
    const updateExpansionBadges = createBadgeUpdater(
        context,
        badgeElements,
        cy
    );
    const layer = getBadgeLayer(context);
    if (layer) {
        layer.innerHTML = "";
    }

    cy.on(
        "add remove data position render layoutstop pan zoom resize",
        updateExpansionBadges
    );
    context.state.subscribe("expansionBadgesVisible", () =>
        updateBadgeLayerVisibility(context)
    );
    context.addCleanup?.(() => updateExpansionBadges.cancel?.());
    updateBadgeLayerVisibility(context);
    updateExpansionBadges();
    return updateExpansionBadges;
}

export default initExpansionBadges;
