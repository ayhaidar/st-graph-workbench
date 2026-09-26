const CY_ID = "cy";
const CONTAINER_ID = "container";
const CONTROLS_ID = "canvasModeControls";
const PAN_BUTTON_ID = "canvasModePan";
const BOX_BUTTON_ID = "canvasModeBox";
const MIN_BOX_SIZE = 6;
const PAN_MODE = "pan";
const BOX_MODE = "box";

function isBoxSelectionMode(context) {
    return context.options.selectionMode === "box";
}

function pointerPoint(event, element) {
    const bounds = element.getBoundingClientRect();
    return {
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
    };
}

function selectionRect(start, end) {
    return {
        x1: Math.min(start.x, end.x),
        y1: Math.min(start.y, end.y),
        x2: Math.max(start.x, end.x),
        y2: Math.max(start.y, end.y),
    };
}

function rectWidth(rect) {
    return rect.x2 - rect.x1;
}

function rectHeight(rect) {
    return rect.y2 - rect.y1;
}

function nodeContainsPoint(node, point) {
    const bounds = node.renderedBoundingBox();
    return (
        point.x >= bounds.x1 &&
        point.x <= bounds.x2 &&
        point.y >= bounds.y1 &&
        point.y <= bounds.y2
    );
}

function nodesInRect(cy, rect) {
    return cy.nodes(":visible").filter((node) => {
        const position = node.renderedPosition();
        return (
            position.x >= rect.x1 &&
            position.x <= rect.x2 &&
            position.y >= rect.y1 &&
            position.y <= rect.y2
        );
    });
}

function updateBoxElement(boxElement, rect) {
    boxElement.hidden = false;
    boxElement.style.left = `${rect.x1}px`;
    boxElement.style.top = `${rect.y1}px`;
    boxElement.style.width = `${rectWidth(rect)}px`;
    boxElement.style.height = `${rectHeight(rect)}px`;
}

function hideBoxElement(boxElement) {
    boxElement.hidden = true;
    boxElement.style.left = "0px";
    boxElement.style.top = "0px";
    boxElement.style.width = "0px";
    boxElement.style.height = "0px";
}

function createBoxElement(context) {
    const container = context.getElementById(CONTAINER_ID);
    const boxElement = container.ownerDocument.createElement("div");
    boxElement.className = "box-selection-rect";
    boxElement.hidden = true;
    container.appendChild(boxElement);
    return boxElement;
}

function stopPointerEvent(event) {
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation?.();
}

function initBoxSelection(context, cy) {
    const cyLayer = context.getElementById(CY_ID);
    const container = context.getElementById(CONTAINER_ID);
    const controls = context.getElementById(CONTROLS_ID);
    const panButton = context.getElementById(PAN_BUTTON_ID);
    const boxButton = context.getElementById(BOX_BUTTON_ID);
    const boxElement = createBoxElement(context);
    let interactionMode = BOX_MODE;
    let dragState = null;

    const cleanupDrag = () => {
        const ownerDocument = cyLayer.ownerDocument;
        ownerDocument.removeEventListener("pointermove", onPointerMove, true);
        ownerDocument.removeEventListener("pointerup", onPointerUp, true);
        ownerDocument.removeEventListener(
            "pointercancel",
            onPointerCancel,
            true
        );
        hideBoxElement(boxElement);
        dragState = null;
    };

    const isBoxInteractionActive = () =>
        isBoxSelectionMode(context) && interactionMode === BOX_MODE;

    const applyInteractionMode = () => {
        const supportsBoxSelection = isBoxSelectionMode(context);
        const boxSelectionActive = isBoxInteractionActive();
        controls.hidden = !supportsBoxSelection;
        panButton.setAttribute(
            "aria-pressed",
            String(supportsBoxSelection && !boxSelectionActive)
        );
        boxButton.setAttribute("aria-pressed", String(boxSelectionActive));
        container.dataset.canvasMode = supportsBoxSelection
            ? interactionMode
            : "default";
        if (cy.boxSelectionEnabled() !== boxSelectionActive) {
            cy.boxSelectionEnabled(boxSelectionActive);
        }
    };

    const setInteractionMode = (nextMode) => {
        if (nextMode !== PAN_MODE && nextMode !== BOX_MODE) {
            return;
        }
        cleanupDrag();
        interactionMode = nextMode;
        applyInteractionMode();
        container.focus();
    };

    const onPanClick = () => setInteractionMode(PAN_MODE);
    const onBoxClick = () => setInteractionMode(BOX_MODE);

    const onPointerMove = (event) => {
        if (!dragState) {
            return;
        }
        const current = pointerPoint(event, cyLayer);
        const rect = selectionRect(dragState.start, current);
        dragState.latest = current;
        if (
            rectWidth(rect) >= MIN_BOX_SIZE ||
            rectHeight(rect) >= MIN_BOX_SIZE
        ) {
            dragState.dragging = true;
            updateBoxElement(boxElement, rect);
        }
        stopPointerEvent(event);
    };

    const onPointerUp = (event) => {
        if (!dragState) {
            return;
        }
        const rect = selectionRect(
            dragState.start,
            dragState.latest || pointerPoint(event, cyLayer)
        );
        const shouldSelect =
            dragState.dragging &&
            (rectWidth(rect) >= MIN_BOX_SIZE ||
                rectHeight(rect) >= MIN_BOX_SIZE);
        const additive = event.shiftKey || event.ctrlKey || event.metaKey;
        cleanupDrag();
        if (shouldSelect) {
            const selectedNodes = nodesInRect(cy, rect);
            if (!additive) {
                cy.elements(":selected").unselect();
            }
            selectedNodes.select();
            context.refreshGraphUi?.(
                selectedNodes.length > 0 ? selectedNodes.last() : null
            );
        } else if (!additive) {
            const selectedElements = cy.elements(":selected");
            if (selectedElements.length > 0) {
                selectedElements.unselect();
                context.refreshGraphUi?.(null);
            }
        }
        stopPointerEvent(event);
    };

    const onPointerCancel = (event) => {
        if (!dragState) {
            return;
        }
        cleanupDrag();
        stopPointerEvent(event);
    };

    const onPointerDown = (event) => {
        if (
            !isBoxInteractionActive() ||
            event.button !== 0 ||
            event.isPrimary === false
        ) {
            return;
        }
        const start = pointerPoint(event, cyLayer);
        if (
            cy.nodes(":visible").some((node) => nodeContainsPoint(node, start))
        ) {
            return;
        }

        dragState = {
            dragging: false,
            latest: start,
            start,
        };
        cyLayer.ownerDocument.addEventListener(
            "pointermove",
            onPointerMove,
            true
        );
        cyLayer.ownerDocument.addEventListener("pointerup", onPointerUp, true);
        cyLayer.ownerDocument.addEventListener(
            "pointercancel",
            onPointerCancel,
            true
        );
        stopPointerEvent(event);
    };

    context.isBoxSelectionInteractionActive = isBoxInteractionActive;
    context.syncBoxSelectionInteraction = applyInteractionMode;
    panButton.addEventListener("click", onPanClick);
    boxButton.addEventListener("click", onBoxClick);
    cyLayer.addEventListener("pointerdown", onPointerDown, true);
    applyInteractionMode();
    context.addCleanup?.(() => {
        cleanupDrag();
        panButton.removeEventListener("click", onPanClick);
        boxButton.removeEventListener("click", onBoxClick);
        cyLayer.removeEventListener("pointerdown", onPointerDown, true);
        boxElement.remove();
        if (
            context.isBoxSelectionInteractionActive === isBoxInteractionActive
        ) {
            delete context.isBoxSelectionInteractionActive;
        }
        if (context.syncBoxSelectionInteraction === applyInteractionMode) {
            delete context.syncBoxSelectionInteraction;
        }
    });
}

export default initBoxSelection;
