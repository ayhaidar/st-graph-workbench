import { cytoscape } from "../utils/layouts.js";

const IDS = {
    controls: "connectedDragControls",
    enabled: "connectedDragEnabled",
    depth: "connectedDragDepth",
    status: "connectedDragStatus",
};

let automoveLoader = null;

function ensureAutomove() {
    if (!automoveLoader) {
        automoveLoader = import("cytoscape-automove").then((module) => {
            cytoscape.use(module.default || module);
        });
    }
    return automoveLoader;
}

function normalizedConfig(context) {
    const config = context.options.connectedDrag;
    return {
        configured: Boolean(config),
        enabled: config?.enabled === true,
        depth: Number(config?.depth) || 1,
        maxDepth: Number(config?.max_depth) || 3,
        maxNodes: Number(config?.max_nodes) || 100,
    };
}

function optionSignature(config) {
    return config.configured
        ? JSON.stringify({
              enabled: config.enabled,
              depth: config.depth,
              maxDepth: config.maxDepth,
              maxNodes: config.maxNodes,
          })
        : null;
}

function syncConnectedDragPreference(context) {
    const config = normalizedConfig(context);
    const signature = optionSignature(config);
    if (context.state.getState("connectedDragOption") === signature) {
        return;
    }

    context.state.updateState("connectedDragOption", signature);
    context.state.updateState("connectedDragEnabled", config.enabled);
    context.state.updateState(
        "connectedDragDepth",
        Math.min(config.depth, config.maxDepth)
    );
}

function visibleHopNeighbors(cy, anchor, depth) {
    let visited = anchor.collection();
    let frontier = anchor.collection();

    for (let hop = 0; hop < depth && frontier.length > 0; hop += 1) {
        const visibleEdges = frontier.connectedEdges(":visible");
        const next = visibleEdges
            .connectedNodes(":visible")
            .difference(visited);
        visited = visited.union(next);
        frontier = next;
    }

    return visited.difference(anchor).nodes();
}

function nativeDragNodes(cy, anchor) {
    let nodes = anchor.selected()
        ? cy
              .nodes(":selected")
              .filter((node) => node.grabbable() && !node.locked())
        : anchor.collection();
    const descendants = nodes.descendants();
    nodes = nodes.union(descendants);
    return nodes.nodes();
}

function eligibleFollowers(cy, anchor, depth, nativeNodes) {
    return visibleHopNeighbors(cy, anchor, depth)
        .difference(nativeNodes)
        .filter((node) => node.grabbable() && !node.locked());
}

function movementPayload(gesture) {
    const connectedIds =
        gesture.status === "applied"
            ? gesture.followers.map((node) => node.id()).sort()
            : [];
    const movedIds = [
        ...gesture.nativeNodes.map((node) => node.id()),
        ...connectedIds,
    ];

    return {
        operation: gesture.status === "disabled" ? "drag" : "connected_drag",
        status: gesture.status,
        anchor_node_id: gesture.anchor.id(),
        moved_node_ids: [...new Set(movedIds)].sort(),
        connected_node_ids: connectedIds,
        depth: gesture.depth,
        candidate_count: gesture.candidateCount,
        max_nodes: gesture.maxNodes,
    };
}

function initConnectedDrag(context) {
    const cy = context.getCyInstance();
    const controls = context.getElementById(IDS.controls);
    const enabled = context.getElementById(IDS.enabled);
    const depth = context.getElementById(IDS.depth);
    const status = context.getElementById(IDS.status);
    let activeRule = null;
    let activeGesture = null;
    let extensionReady = false;
    let extensionError = false;
    let layoutRunning = false;
    let restingStatus = "";

    const setStatus = (message, remember = false) => {
        if (remember) {
            restingStatus = message;
        }
        if (status) {
            status.textContent = message;
            status.hidden = !message;
        }
    };

    const destroyRule = () => {
        activeRule?.destroy?.();
        activeRule = null;
    };

    const cancelGesture = () => {
        destroyRule();
        activeGesture = null;
    };

    const update = () => {
        const config = normalizedConfig(context);
        syncConnectedDragPreference(context);
        const isEnabled = context.state.getState("connectedDragEnabled");
        const selectedDepth = Math.min(
            Number(context.state.getState("connectedDragDepth")) || 1,
            config.maxDepth
        );

        if (controls) controls.hidden = !config.configured;
        if (enabled) {
            enabled.checked = isEnabled;
            enabled.disabled = extensionError || !extensionReady;
        }
        if (depth) {
            [...depth.options].forEach((option) => {
                option.hidden = Number(option.value) > config.maxDepth;
                option.disabled = Number(option.value) > config.maxDepth;
            });
            depth.value = String(selectedDepth);
            depth.disabled = !isEnabled || extensionError || !extensionReady;
        }

        if (!config.configured) {
            cancelGesture();
            restingStatus = "";
            setStatus("");
            return;
        }
        if (!extensionReady && !extensionError) {
            setStatus("Loading connected dragging...");
        } else if (extensionError) {
            setStatus(
                "Connected dragging could not be loaded; normal dragging remains available."
            );
        } else if (!activeGesture) {
            setStatus(restingStatus);
        }
    };

    const loadExtension = () => {
        if (
            !normalizedConfig(context).configured ||
            extensionReady ||
            extensionError
        ) {
            return;
        }
        ensureAutomove()
            .then(() => {
                if (context.isDestroyed) return;
                extensionReady = true;
                update();
            })
            .catch((error) => {
                console.error("Failed to load connected dragging", error);
                if (context.isDestroyed) return;
                extensionError = true;
                update();
            });
    };

    const onGrab = (event) => {
        destroyRule();
        const anchor = event.target;
        const config = normalizedConfig(context);
        const selectedDepth = Math.min(
            Number(context.state.getState("connectedDragDepth")) || 1,
            config.maxDepth
        );
        const nativeNodes = nativeDragNodes(cy, anchor);
        const baseGesture = {
            anchor,
            candidateCount: 0,
            depth: selectedDepth,
            didDrag: false,
            followers: cy.collection(),
            maxNodes: config.maxNodes,
            nativeNodes,
            status: "disabled",
        };

        if (
            !config.configured ||
            !context.state.getState("connectedDragEnabled") ||
            !extensionReady
        ) {
            activeGesture = baseGesture;
            return;
        }
        if (layoutRunning) {
            activeGesture = { ...baseGesture, status: "layout_running" };
            setStatus(
                "Connected dragging is paused while the layout is running.",
                true
            );
            return;
        }

        const followers = eligibleFollowers(
            cy,
            anchor,
            selectedDepth,
            nativeNodes
        );
        if (followers.length > config.maxNodes) {
            activeGesture = {
                ...baseGesture,
                candidateCount: followers.length,
                status: "limit_exceeded",
            };
            setStatus(
                `${followers.length} connected nodes exceed the ${config.maxNodes} node limit. ` +
                    "Reduce the depth or raise the application limit.",
                true
            );
            return;
        }

        activeGesture = {
            ...baseGesture,
            candidateCount: followers.length,
            followers,
            status: "applied",
        };
        if (followers.length > 0) {
            activeRule = cy.automove({
                nodesMatching: followers,
                reposition: "drag",
                dragWith: anchor,
            });
        }
        setStatus(
            `Moving ${followers.length} connected node${followers.length === 1 ? "" : "s"} ` +
                `within ${selectedDepth} hop${selectedDepth === 1 ? "" : "s"}.`
        );
    };

    const onDrag = () => {
        if (activeGesture) {
            activeGesture.didDrag = true;
        }
    };

    const onFree = () => {
        destroyRule();
        if (activeGesture?.didDrag) {
            context.pendingDragMovement = movementPayload(activeGesture);
            if (activeGesture.status === "applied") {
                setStatus(
                    `Moved ${activeGesture.followers.length} connected node${
                        activeGesture.followers.length === 1 ? "" : "s"
                    } with ${activeGesture.anchor.id()}.`,
                    true
                );
            } else if (activeGesture.status === "disabled") {
                restingStatus = "";
                setStatus("");
            }
        }
        activeGesture = null;
    };

    const onLayoutStart = () => {
        layoutRunning = true;
        destroyRule();
        if (activeGesture) {
            activeGesture = {
                ...activeGesture,
                followers: cy.collection(),
                status: "layout_running",
            };
            setStatus(
                "Connected dragging is paused while the layout is running.",
                true
            );
        }
    };
    const onLayoutStop = () => {
        layoutRunning = false;
        update();
    };
    const onEnabledChange = () => {
        cancelGesture();
        restingStatus = "";
        context.state.updateState("connectedDragEnabled", enabled.checked);
    };
    const onDepthChange = () => {
        cancelGesture();
        restingStatus = "";
        context.state.updateState("connectedDragDepth", Number(depth.value));
    };

    enabled?.addEventListener("change", onEnabledChange);
    depth?.addEventListener("change", onDepthChange);
    cy.on("grabon", "node", onGrab);
    cy.on("drag", "node", onDrag);
    cy.on("freeon", "node", onFree);
    cy.on("layoutstart", onLayoutStart);
    cy.on("layoutstop", onLayoutStop);
    context.state.subscribe("connectedDragEnabled", update);
    context.state.subscribe("connectedDragDepth", update);
    context.consumeDragMovement = () => {
        const movement = context.pendingDragMovement || null;
        context.pendingDragMovement = null;
        return movement;
    };

    syncConnectedDragPreference(context);
    loadExtension();
    update();

    context.addCleanup?.(() => {
        cancelGesture();
        enabled?.removeEventListener("change", onEnabledChange);
        depth?.removeEventListener("change", onDepthChange);
        cy.off("grabon", "node", onGrab);
        cy.off("drag", "node", onDrag);
        cy.off("freeon", "node", onFree);
        cy.off("layoutstart", onLayoutStart);
        cy.off("layoutstop", onLayoutStop);
        delete context.consumeDragMovement;
        context.pendingDragMovement = null;
    });

    return () => {
        syncConnectedDragPreference(context);
        loadExtension();
        update();
    };
}

export { syncConnectedDragPreference };
export default initConnectedDrag;
