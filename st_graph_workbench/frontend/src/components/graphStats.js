const IDS = {
    button: "graphStatsButton",
    buttonNodes: "graphStatsButtonNodes",
    buttonEdges: "graphStatsButtonEdges",
    dialog: "graphStatsDialog",
    close: "graphStatsClose",
    shownNodes: "graphStatsShownNodes",
    hiddenNodes: "graphStatsHiddenNodes",
    totalNodes: "graphStatsTotalNodes",
    expandedNodes: "graphStatsExpandedNodes",
    notExpandedNodes: "graphStatsNotExpandedNodes",
    shownEdges: "graphStatsShownEdges",
    hiddenEdges: "graphStatsHiddenEdges",
    totalEdges: "graphStatsTotalEdges",
};

function hasPositiveCount(value) {
    const count = Number(value);
    return Number.isFinite(count) && count > 0;
}

function countExpansionStates(cy) {
    let expandedNodes = 0;
    let notExpandedNodes = 0;

    cy.nodes(":visible").forEach((node) => {
        const expansion = node.data("expansion");
        if (!expansion || typeof expansion !== "object") {
            return;
        }

        if (expansion.state === "expanded") {
            expandedNodes += 1;
            return;
        }

        if (hasPositiveCount(expansion.next_count)) {
            notExpandedNodes += 1;
        }
    });

    return {
        expandedNodes,
        notExpandedNodes,
    };
}

function countGraph(cy) {
    const totalNodes = cy.nodes().length;
    const shownNodes = cy.nodes(":visible").length;
    const totalEdges = cy.edges().length;
    const shownEdges = cy.edges(":visible").length;
    const expansionCounts = countExpansionStates(cy);

    return {
        shownNodes,
        hiddenNodes: Math.max(totalNodes - shownNodes, 0),
        totalNodes,
        ...expansionCounts,
        shownEdges,
        hiddenEdges: Math.max(totalEdges - shownEdges, 0),
        totalEdges,
    };
}

function setText(context, id, value) {
    const element = context.getElementById(id);
    if (element) {
        element.textContent = String(value);
    }
}

function updateGraphStats(context) {
    const cy = context.getCyInstance();
    if (!cy) {
        return;
    }

    const counts = countGraph(cy);
    setText(context, IDS.buttonNodes, counts.shownNodes);
    setText(context, IDS.buttonEdges, counts.shownEdges);
    setText(context, IDS.shownNodes, counts.shownNodes);
    setText(context, IDS.hiddenNodes, counts.hiddenNodes);
    setText(context, IDS.totalNodes, counts.totalNodes);
    setText(context, IDS.expandedNodes, counts.expandedNodes);
    setText(context, IDS.notExpandedNodes, counts.notExpandedNodes);
    setText(context, IDS.shownEdges, counts.shownEdges);
    setText(context, IDS.hiddenEdges, counts.hiddenEdges);
    setText(context, IDS.totalEdges, counts.totalEdges);
}

function initGraphStats(context) {
    const button = context.getElementById(IDS.button);
    const dialog = context.getElementById(IDS.dialog);
    const close = context.getElementById(IDS.close);

    context.updateGraphStats = () => updateGraphStats(context);

    button?.addEventListener("click", () => {
        updateGraphStats(context);
        if (dialog) {
            dialog.hidden = !dialog.hidden;
        }
    });

    close?.addEventListener("click", () => {
        if (dialog) {
            dialog.hidden = true;
        }
    });

    context
        .getCyInstance()
        ?.on("add remove data", () => updateGraphStats(context));
    updateGraphStats(context);
    return context.updateGraphStats;
}

export default initGraphStats;
