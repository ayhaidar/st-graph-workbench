import { setButtonState } from "../utils/dom.js";
import { analysisGraph } from "./expansionControls.js";

const IDS = {
    group: "analysisControls",
    shortestPath: "analysisShortestPath",
    bfs: "analysisBfs",
    dfs: "analysisDfs",
    components: "analysisComponents",
    degree: "analysisDegree",
};

const ACTION_TO_ID = {
    shortest_path: IDS.shortestPath,
    bfs: IDS.bfs,
    dfs: IDS.dfs,
    connected_components: IDS.components,
    degree: IDS.degree,
};

function ids(collection) {
    return collection.map((element) => element.id()).sort();
}

function selectedVisibleNodes(cy) {
    return cy.scratch("analysisScope") === "loaded"
        ? cy.nodes(":selected")
        : cy.nodes(":selected").filter(":visible");
}

function visibleElements(cy) {
    return cy.scratch("analysisScope") === "loaded"
        ? cy.elements()
        : cy.elements(":visible");
}

function highlight(cy, collection) {
    cy.elements().removeClass("analysis-result");
    collection.addClass("analysis-result");
}

function emitAnalysis(context, data) {
    const graph = analysisGraph(context);
    const renderer = context.getCyInstance();
    const elements = visibleElements(graph);
    const resultIds = [
        ...(data.node_id ? [data.node_id] : []),
        ...(data.node_ids || []),
        ...(data.edge_ids || []),
        ...(data.components || []).flatMap((component) => [
            ...component.node_ids,
            ...component.edge_ids,
        ]),
    ];
    highlight(
        renderer,
        renderer
            .elements()
            .filter(
                (element) =>
                    resultIds.includes(element.id()) && element.visible()
            )
    );
    data = {
        ...data,
        scope: context.analysisScope || "visible",
        source_dataset_id: context.options.expansion?.source_id ?? null,
        source_version: context.options.expansion?.source_version ?? null,
        view_revision: context.options.expansion?.view_revision ?? null,
        node_count: elements.nodes().length,
        edge_count: elements.edges().length,
        complete: true,
        source_complete: false,
        completeness:
            "Complete for the chosen scope; source coverage is not implied.",
        collapsed_result_ids: resultIds.filter((id) =>
            renderer.getElementById(id).empty()
        ),
    };
    context.setImmediateStreamlitValue({
        action: "analysis",
        data: data,
        timestamp: Date.now(),
    });
}

function runShortestPath(context) {
    const cy = analysisGraph(context);
    const selected = selectedVisibleNodes(cy);
    if (selected.length !== 2) {
        return;
    }

    const source = selected.first();
    const target = selected.last();
    const dijkstra = visibleElements(cy).dijkstra({
        root: source,
        directed: false,
    });
    const path = dijkstra.pathTo(target);
    highlight(cy, path);
    emitAnalysis(context, {
        analysis: "shortest_path",
        source_id: source.id(),
        target_id: target.id(),
        distance: dijkstra.distanceTo(target),
        node_ids: ids(path.nodes()),
        edge_ids: ids(path.edges()),
    });
}

function runTraversal(context, kind) {
    const cy = analysisGraph(context);
    const selected = selectedVisibleNodes(cy);
    if (selected.length !== 1) {
        return;
    }

    const root = selected.first();
    const visitedNodeIds = [];
    const visitedEdgeIds = [];
    const options = {
        roots: root,
        directed: false,
        visit: function (node, edge) {
            visitedNodeIds.push(node.id());
            if (edge) {
                visitedEdgeIds.push(edge.id());
            }
        },
    };
    const result =
        kind === "bfs"
            ? visibleElements(cy).bfs(options)
            : visibleElements(cy).dfs(options);
    highlight(cy, result.path);
    emitAnalysis(context, {
        analysis: kind,
        root_id: root.id(),
        node_ids: visitedNodeIds,
        edge_ids: visitedEdgeIds,
    });
}

function runConnectedComponents(context) {
    const cy = analysisGraph(context);
    const components = visibleElements(cy).components();
    const largest = components.reduce((largestComponent, component) => {
        return component.nodes().length > largestComponent.nodes().length
            ? component
            : largestComponent;
    }, cy.collection());
    highlight(cy, largest);
    emitAnalysis(context, {
        analysis: "connected_components",
        components: components.map((component) => ({
            node_ids: ids(component.nodes()),
            edge_ids: ids(component.edges()),
        })),
    });
}

function runDegree(context) {
    const cy = analysisGraph(context);
    const selected = selectedVisibleNodes(cy);
    if (selected.length !== 1) {
        return;
    }

    const node = selected.first();
    const edges = node
        .connectedEdges()
        .intersection(visibleElements(cy).edges());
    highlight(cy, node.union(node.connectedEdges()));
    emitAnalysis(context, {
        analysis: "degree",
        node_id: node.id(),
        degree: edges.length + edges.filter((edge) => edge.isLoop()).length,
        indegree: edges.filter((edge) => edge.target().id() === node.id())
            .length,
        outdegree: edges.filter((edge) => edge.source().id() === node.id())
            .length,
        edge_ids: ids(edges),
    });
}

function updateAnalysisControls(context, activeActions) {
    const cy = context.getCyInstance();
    const group = context.getElementById(IDS.group);
    const selectedCount = selectedVisibleNodes(cy).length;

    if (group) {
        group.hidden = activeActions.size === 0;
    }

    Object.entries(ACTION_TO_ID).forEach(([action, id]) => {
        const button = context.getElementById(id);
        if (!button) {
            return;
        }
        button.hidden = !activeActions.has(action);
    });

    setButtonState(context.getElementById(IDS.shortestPath), {
        enabled: activeActions.has("shortest_path") && selectedCount === 2,
    });
    setButtonState(context.getElementById(IDS.bfs), {
        enabled: activeActions.has("bfs") && selectedCount === 1,
    });
    setButtonState(context.getElementById(IDS.dfs), {
        enabled: activeActions.has("dfs") && selectedCount === 1,
    });
    setButtonState(context.getElementById(IDS.degree), {
        enabled: activeActions.has("degree") && selectedCount === 1,
    });
    setButtonState(context.getElementById(IDS.components), {
        enabled: activeActions.has("connected_components"),
    });
}

function refreshActiveActions(context, activeActions) {
    activeActions.clear();
    (context.options.analysisActions || []).forEach((action) => {
        activeActions.add(action);
    });
}

function runIfActionEnabled(context, activeActions, action, runner) {
    refreshActiveActions(context, activeActions);
    if (!activeActions.has(action)) {
        return;
    }
    if (
        context.analysisScope === "source" &&
        context.options.expansion?.source_analysis
    ) {
        context.emitExpansion("analyze", { analysis: action });
        return;
    }
    runner();
}

function initAnalysis(context) {
    const activeActions = new Set();
    const group = context.getElementById(IDS.group);
    if (!group) {
        return () => {};
    }

    context
        .getElementById(IDS.shortestPath)
        ?.addEventListener("click", () =>
            runIfActionEnabled(context, activeActions, "shortest_path", () =>
                runShortestPath(context)
            )
        );
    context
        .getElementById(IDS.bfs)
        ?.addEventListener("click", () =>
            runIfActionEnabled(context, activeActions, "bfs", () =>
                runTraversal(context, "bfs")
            )
        );
    context
        .getElementById(IDS.dfs)
        ?.addEventListener("click", () =>
            runIfActionEnabled(context, activeActions, "dfs", () =>
                runTraversal(context, "dfs")
            )
        );
    context
        .getElementById(IDS.components)
        ?.addEventListener("click", () =>
            runIfActionEnabled(
                context,
                activeActions,
                "connected_components",
                () => runConnectedComponents(context)
            )
        );
    context
        .getElementById(IDS.degree)
        ?.addEventListener("click", () =>
            runIfActionEnabled(context, activeActions, "degree", () =>
                runDegree(context)
            )
        );

    const update = () => {
        refreshActiveActions(context, activeActions);
        updateAnalysisControls(context, activeActions);
    };
    context.state.subscribe("selection", update);
    context.getCyInstance().on("select unselect", update);
    update();
    return update;
}

export default initAnalysis;
