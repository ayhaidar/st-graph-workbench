import { getExpansionAction } from "../utils/expansion.js";
import { setButtonState } from "../utils/dom.js";

const IDS = {
    toolbox: "toolbox",
    nodeActions: "nodeActions",
    explore: "exploreControls",
    remove: "nodeActionsRemove",
    expand: "nodeActionsExpand",
    neighbors: "nodeActionsNeighbors",
    incoming: "nodeActionsIncoming",
    outgoing: "nodeActionsOutgoing",
    badges: "expansionBadgeToggle",
    selectionStatus: "selectionStatus",
    selectionStatusMode: "selectionStatusMode",
    selectionStatusCount: "selectionStatusCount",
};
const NODE_ACTION_BUTTONS = ["remove", "expand"];
const EXPLORE_ACTION_BUTTONS = [
    "show_neighbors",
    "show_incoming",
    "show_outgoing",
];

function getButton(context, id) {
    return context.getElementById(id);
}

function getSelectedNodes(context) {
    return context.getCyInstance()?.nodes(":selected");
}

function getSingleSelectedNode(context) {
    const selectedNodes = getSelectedNodes(context);
    if (selectedNodes?.length === 1) {
        return selectedNodes.first();
    }
    return null;
}

function modeLabel(mode) {
    if (mode === "multiple") {
        return "Multiple";
    }
    if (mode === "box") {
        return "Box";
    }
    return "Single";
}

function countLabel(count, singular, plural) {
    return `${count} ${count === 1 ? singular : plural}`;
}

function selectionCountLabel(selected) {
    const nodeCount = selected?.nodes().length || 0;
    const edgeCount = selected?.edges().length || 0;
    const total = nodeCount + edgeCount;

    if (total === 0) {
        return "0 selected";
    }

    if (nodeCount > 0 && edgeCount > 0) {
        return `${countLabel(nodeCount, "node", "nodes")}, ${countLabel(
            edgeCount,
            "edge",
            "edges"
        )}`;
    }

    if (nodeCount > 0) {
        return `${countLabel(nodeCount, "node", "nodes")} selected`;
    }

    return `${countLabel(edgeCount, "edge", "edges")} selected`;
}

function updateSelectionStatus(context) {
    const status = context.getElementById(IDS.selectionStatus);
    const mode = context.getElementById(IDS.selectionStatusMode);
    const count = context.getElementById(IDS.selectionStatusCount);
    const selected = context.state.getState("selection").selected;
    const totalSelected = selected?.length || 0;

    if (!status || !mode || !count) {
        return;
    }

    const selectionMode = context.options.selectionMode || "single";
    const label = selectionCountLabel(selected);
    mode.innerText = modeLabel(selectionMode);
    count.innerText = label;
    status.dataset.mode = selectionMode;
    status.dataset.hasSelection = String(totalSelected > 0);
    status.setAttribute(
        "title",
        `${modeLabel(selectionMode)} selection: ${label}`
    );
}

function updateNodeActionButtons(context, activeNodeActions) {
    const remove = getButton(context, IDS.remove);
    const expand = getButton(context, IDS.expand);
    const neighbors = getButton(context, IDS.neighbors);
    const incoming = getButton(context, IDS.incoming);
    const outgoing = getButton(context, IDS.outgoing);
    const nodeActions = context.getElementById(IDS.nodeActions);
    const explore = context.getElementById(IDS.explore);
    const selectedNodes = getSelectedNodes(context);
    const selectedNode = getSingleSelectedNode(context);

    if (
        !remove ||
        !expand ||
        !neighbors ||
        !incoming ||
        !outgoing ||
        !nodeActions ||
        !explore
    ) {
        return;
    }

    nodeActions.hidden = !NODE_ACTION_BUTTONS.some((action) =>
        activeNodeActions.has(action)
    );
    explore.hidden = !EXPLORE_ACTION_BUTTONS.some((action) =>
        activeNodeActions.has(action)
    );
    remove.hidden = !activeNodeActions.has("remove");
    expand.hidden = !activeNodeActions.has("expand");
    neighbors.hidden = !activeNodeActions.has("show_neighbors");
    incoming.hidden = !activeNodeActions.has("show_incoming");
    outgoing.hidden = !activeNodeActions.has("show_outgoing");

    setButtonState(remove, {
        enabled: activeNodeActions.has("remove") && selectedNodes?.length > 0,
        title:
            selectedNodes?.length > 0
                ? "Remove Nodes"
                : "Select nodes to remove",
    });

    const expansionAction = selectedNode
        ? getExpansionAction(selectedNode.data())
        : null;
    const isExpanded = expansionAction?.state === "expanded";
    const expandTitle = expansionAction
        ? expansionAction.label.replace("node", "Node")
        : "No expansion available";
    expand.dataset.mode = isExpanded ? "expanded" : "collapsed";
    setButtonState(expand, {
        enabled: activeNodeActions.has("expand") && Boolean(expansionAction),
        title: selectedNode
            ? expandTitle
            : "Select a node to expand or collapse",
    });

    [
        [neighbors, "show_neighbors", "Show Neighbors"],
        [incoming, "show_incoming", "Show Incoming"],
        [outgoing, "show_outgoing", "Show Outgoing"],
    ].forEach(([button, action, title]) => {
        setButtonState(button, {
            enabled: activeNodeActions.has(action) && selectedNodes?.length > 0,
            title: selectedNodes?.length > 0 ? title : "Select nodes first",
        });
    });
}

function updateBadgeToggle(context) {
    const badgeToggle = getButton(context, IDS.badges);
    if (!badgeToggle) {
        return;
    }

    const isVisible = context.state.getState("expansionBadgesVisible");
    const title = isVisible ? "Hide Expansion Counts" : "Show Expansion Counts";
    badgeToggle.classList.toggle("is-active", isVisible);
    badgeToggle.setAttribute("aria-pressed", String(isVisible));
    badgeToggle.setAttribute("title", title);
    badgeToggle.setAttribute("aria-label", title);
}

function currentNodeActions(context) {
    return new Set(context.options.nodeActions || []);
}

function initMenuAutoClose(context) {
    const toolbox = context.getElementById(IDS.toolbox);
    if (!toolbox) {
        return;
    }

    const closeClickedMenu = (event) => {
        const button = event.target?.closest?.("button.toolbox__button");
        if (!button || button.disabled) {
            return;
        }

        const menu = button.closest("details.toolbox__menu");
        if (!menu) {
            return;
        }

        menu.open = false;
    };

    toolbox.addEventListener("click", closeClickedMenu);
    context.addCleanup?.(() => {
        toolbox.removeEventListener("click", closeClickedMenu);
    });
}

function initToolbox(context) {
    const badgeToggle = getButton(context, IDS.badges);
    const cy = context.getCyInstance();
    const updateToolbox = () => {
        updateNodeActionButtons(context, currentNodeActions(context));
        updateBadgeToggle(context);
        updateSelectionStatus(context);
    };

    if (badgeToggle) {
        badgeToggle.addEventListener("click", () => {
            context.state.updateState(
                "expansionBadgesVisible",
                !context.state.getState("expansionBadgesVisible")
            );
        });
    }

    initMenuAutoClose(context);
    cy?.on("select unselect", updateToolbox);
    context.state.subscribe("selection", updateToolbox);
    context.state.subscribe("expansionBadgesVisible", updateToolbox);
    updateToolbox();
    return updateToolbox;
}

export default initToolbox;
