function ids(collection) {
    return collection.map((element) => element.id()).sort();
}

function elementPayload(element) {
    if (!element || element.empty?.()) {
        return null;
    }

    const first = element.first();
    if (!first || first.empty?.() || first.inside?.() === false) {
        return null;
    }

    return {
        id: first.id(),
        group: first.group(),
        data: first.data(),
    };
}

function elementPayloads(collection) {
    return collection
        .map((element) => elementPayload(element))
        .filter((element) => element !== null)
        .sort((left, right) => {
            if (left.group !== right.group) {
                return left.group.localeCompare(right.group);
            }
            return left.id.localeCompare(right.id);
        });
}

function relatedElementContext(collection) {
    const nodes = collection.nodes();
    const edges = collection.edges();
    const connectedEdges = nodes.connectedEdges().union(edges);
    const connectedNodes = nodes
        .connectedNodes()
        .union(edges.connectedNodes())
        .difference(nodes);
    const connectedElements = connectedNodes
        .union(connectedEdges)
        .difference(collection);

    return {
        nodes,
        edges,
        connectedNodes,
        connectedEdges,
        connectedElements,
    };
}

function getSelectionPayload(cy, lastSelected) {
    const selected = cy.elements(":selected");
    const context = relatedElementContext(selected);

    return {
        selected_node_ids: ids(context.nodes),
        selected_edge_ids: ids(context.edges),
        last_selected: elementPayload(lastSelected),
        connected_node_ids: ids(context.connectedNodes),
        connected_edge_ids: ids(context.connectedEdges),
        selected_elements: elementPayloads(selected),
        connected_elements: elementPayloads(context.connectedElements),
    };
}

function getSearchPayload(cy, { mode, query, matches }) {
    const safeMatches = matches || cy.collection();
    const context = relatedElementContext(safeMatches);

    return {
        operation: "search",
        mode: mode,
        query: query,
        match_count: safeMatches.length,
        matched_node_ids: ids(context.nodes),
        matched_edge_ids: ids(context.edges),
        connected_node_ids: ids(context.connectedNodes),
        connected_edge_ids: ids(context.connectedEdges),
        matched_elements: elementPayloads(safeMatches),
        connected_elements: elementPayloads(context.connectedElements),
        visible_node_ids: ids(cy.nodes(":visible")),
        visible_edge_ids: ids(cy.edges(":visible")),
    };
}

function getCrudPayload(cy, operation, lastSelected) {
    const selected = cy.elements(":selected");
    const context = relatedElementContext(selected);
    const extent = cy.extent();

    return {
        operation: operation,
        selected_node_ids: ids(context.nodes),
        selected_edge_ids: ids(context.edges),
        last_selected: elementPayload(lastSelected),
        connected_node_ids: ids(context.connectedNodes),
        connected_edge_ids: ids(context.connectedEdges),
        selected_elements: elementPayloads(selected),
        connected_elements: elementPayloads(context.connectedElements),
        suggested_position: {
            x: (extent.x1 + extent.x2) / 2,
            y: (extent.y1 + extent.y2) / 2,
        },
    };
}

function getPositionsPayload(cy, movement = null) {
    const payload = {
        positions: cy.nodes().map((node) => ({
            id: node.id(),
            position: node.position(),
        })),
    };
    if (movement) {
        payload.movement = movement;
    }
    return payload;
}

export {
    getCrudPayload,
    getPositionsPayload,
    getSearchPayload,
    getSelectionPayload,
};
