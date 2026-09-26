import { runLayout } from "../utils/layouts.js";

function asArray(value) {
    if (!value) {
        return [];
    }
    return Array.isArray(value) ? value : [value];
}

function elementId(element) {
    if (element?.data?.id === undefined) {
        return null;
    }
    return String(element.data.id);
}

function commandElements(command) {
    return [...asArray(command.nodes), ...asArray(command.edges)];
}

function setElementsPayload(command) {
    const elements = command.elements || { nodes: [], edges: [] };
    return [...asArray(elements.nodes), ...asArray(elements.edges)];
}

function sortElements(elements) {
    return [
        ...elements.filter((element) => element.group !== "edges"),
        ...elements.filter((element) => element.group === "edges"),
    ];
}

function edgeEndpointsChanged(currentElement, nextData) {
    if (!currentElement.isEdge()) {
        return false;
    }
    return (
        nextData.source !== undefined &&
        nextData.target !== undefined &&
        (String(nextData.source) !== String(currentElement.data("source")) ||
            String(nextData.target) !== String(currentElement.data("target")))
    );
}

function mergeElementData(currentElement, incomingData, replace) {
    if (replace) {
        return { ...incomingData };
    }
    return { ...currentElement.data(), ...incomingData };
}

function updateExistingElement(currentElement, element, replace) {
    const nextData = mergeElementData(
        currentElement,
        element.data || {},
        replace
    );

    if (edgeEndpointsChanged(currentElement, nextData)) {
        const currentJson = currentElement.json();
        currentElement.remove();
        return {
            ...currentJson,
            ...element,
            data: nextData,
        };
    }

    const nextJson = { data: nextData };
    if (element.position && currentElement.isNode()) {
        nextJson.position = element.position;
    }
    currentElement.json(nextJson);
    return null;
}

function applyAddElements(cy, command) {
    const incoming = commandElements(command);
    const missing = incoming.filter((element) => {
        const id = elementId(element);
        return id !== null && cy.getElementById(id).length === 0;
    });
    if (missing.length === 0) {
        return false;
    }
    cy.add(sortElements(missing));
    return true;
}

function applyUpsertElements(cy, command) {
    const incoming = commandElements(command);
    const replace = command.replace !== false;
    const toAdd = [];
    let changed = false;

    incoming.forEach((element) => {
        const id = elementId(element);
        if (id === null) {
            return;
        }
        const currentElement = cy.getElementById(id);
        if (currentElement.length === 0) {
            toAdd.push(element);
            changed = true;
            return;
        }

        const replacement = updateExistingElement(
            currentElement,
            element,
            replace
        );
        if (replacement) {
            toAdd.push(replacement);
        }
        changed = true;
    });

    if (toAdd.length > 0) {
        cy.add(sortElements(toAdd));
    }
    return changed;
}

function applyUpdateData(cy, command) {
    const id = String(command.element_id ?? "");
    if (!id) {
        return false;
    }

    const currentElement = cy.getElementById(id);
    if (currentElement.length === 0) {
        return false;
    }

    const replace = command.merge === false;
    const replacement = updateExistingElement(
        currentElement,
        { data: command.data || {} },
        replace
    );
    if (replacement) {
        cy.add(sortElements([replacement]));
    }
    return true;
}

function applyDeleteElements(cy, command) {
    const nodeIds = new Set(asArray(command.node_ids).map(String));
    const edgeIds = new Set(asArray(command.edge_ids).map(String));
    let toRemove = cy.collection();

    nodeIds.forEach((id) => {
        toRemove = toRemove.union(cy.getElementById(id));
    });
    edgeIds.forEach((id) => {
        toRemove = toRemove.union(cy.getElementById(id));
    });

    if (command.remove_incident_edges !== false && nodeIds.size > 0) {
        toRemove = toRemove.union(
            cy.edges().filter((edge) => {
                return (
                    nodeIds.has(edge.source().id()) ||
                    nodeIds.has(edge.target().id())
                );
            })
        );
    }

    if (toRemove.length === 0) {
        return false;
    }
    toRemove.remove();
    return true;
}

function applySetElements(cy, command) {
    cy.elements().remove();
    const elements = setElementsPayload(command);
    if (elements.length > 0) {
        cy.add(sortElements(elements));
    }
    return true;
}

function commandId(command) {
    const id = command?.command_id;
    if (id === undefined || id === null || id === "") {
        return null;
    }
    return String(id);
}

function hasCommandField(command, field) {
    return Object.prototype.hasOwnProperty.call(command, field);
}

function finiteNumber(value) {
    const numberValue = Number(value);
    return Number.isFinite(numberValue) ? numberValue : null;
}

function nonnegativeNumber(value, fallback) {
    const numberValue = finiteNumber(value);
    return numberValue !== null && numberValue >= 0 ? numberValue : fallback;
}

function zoomBoundValue(value, fallback) {
    if (value === null) {
        return Number.isFinite(fallback) ? fallback : null;
    }
    return finiteNumber(value);
}

function queueViewportAction(context, cy, command, renderLayout, postActions) {
    const duration = nonnegativeNumber(command.duration, 180);
    if (command.operation === "fit") {
        postActions.push(() => {
            cy.animate({
                fit: { padding: nonnegativeNumber(command.padding, 30) },
                duration,
            });
        });
        return;
    }
    if (command.operation === "center") {
        postActions.push(() => {
            cy.animate({ center: {}, duration });
        });
        return;
    }
    if (command.operation === "zoom") {
        postActions.push(() => {
            const level = Number(command.level ?? command.zoom);
            const renderedPosition = command.renderedPosition;
            const zoom = Number.isFinite(level)
                ? { level, renderedPosition }
                : undefined;
            if (zoom) {
                cy.animate({ zoom, duration });
            }
        });
        return;
    }
    if (command.operation === "pan") {
        postActions.push(() => {
            if (command.pan) {
                cy.animate({ pan: command.pan, duration });
            }
        });
        return;
    }
    if (command.operation === "set_viewport") {
        postActions.push(() => {
            const viewport = {};
            const viewportDuration = nonnegativeNumber(command.duration, 0);
            if (hasCommandField(command, "zoom") && command.zoom !== null) {
                const zoom = finiteNumber(command.zoom);
                if (zoom !== null) {
                    viewport.zoom = zoom;
                }
            }
            if (command.pan) {
                viewport.pan = command.pan;
            }
            if (!viewport.pan && viewport.zoom === undefined) {
                return;
            }
            if (viewportDuration > 0) {
                const animation = { duration: viewportDuration };
                if (viewport.pan) {
                    animation.pan = viewport.pan;
                }
                if (viewport.zoom !== undefined) {
                    animation.zoom = { level: viewport.zoom };
                }
                cy.animate(animation);
            } else {
                cy.viewport(viewport);
            }
        });
        return;
    }
    if (command.operation === "set_zoom_bounds") {
        postActions.push(() => {
            if (hasCommandField(command, "min_zoom")) {
                const minZoom = zoomBoundValue(
                    command.min_zoom,
                    context.defaultMinZoom
                );
                if (minZoom !== null) {
                    cy.minZoom(minZoom);
                }
            }
            if (hasCommandField(command, "max_zoom")) {
                const maxZoom = zoomBoundValue(
                    command.max_zoom,
                    context.defaultMaxZoom
                );
                if (maxZoom !== null) {
                    cy.maxZoom(maxZoom);
                }
            }
        });
        return;
    }
    if (command.operation === "run_layout") {
        postActions.push(() => {
            runLayout(context, cy, command.layout || renderLayout);
        });
    }
}

function applyCommand(context, cy, command, renderLayout, postActions) {
    if (command.operation === "add_elements") {
        return applyAddElements(cy, command);
    }
    if (command.operation === "upsert_elements") {
        return applyUpsertElements(cy, command);
    }
    if (command.operation === "update_data") {
        return applyUpdateData(cy, command);
    }
    if (command.operation === "delete_elements") {
        return applyDeleteElements(cy, command);
    }
    if (command.operation === "clear") {
        const hadElements = cy.elements().length > 0;
        cy.elements().remove();
        return hadElements;
    }
    if (command.operation === "set_elements") {
        return applySetElements(cy, command);
    }

    queueViewportAction(context, cy, command, renderLayout, postActions);
    return false;
}

function applyGraphCommands(instance, commands, renderLayout) {
    const cy = instance.cy;
    const appliedCommandIds = instance.appliedCommandIds;
    const postActions = [];
    let changed = false;

    const pendingCommands = asArray(commands).filter((command) => {
        const id = commandId(command);
        return id !== null && !appliedCommandIds.has(id);
    });

    if (pendingCommands.length === 0) {
        return { changed: false };
    }

    cy.batch(() => {
        pendingCommands.forEach((command) => {
            const id = commandId(command);
            try {
                changed =
                    applyCommand(
                        instance.context,
                        cy,
                        command,
                        renderLayout,
                        postActions
                    ) || changed;
                appliedCommandIds.add(id);
            } catch (error) {
                appliedCommandIds.add(id);
                console.error("Failed to apply graph command", command, error);
            }
        });
    });

    postActions.forEach((action) => action());
    return { changed };
}

export default applyGraphCommands;
