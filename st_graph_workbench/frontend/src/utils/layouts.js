import cytoscape from "cytoscape";

const EXTENSION_LOADERS = {
    fcose: () => import("cytoscape-fcose"),
    cola: () => import("cytoscape-cola"),
    dagre: () => import("cytoscape-dagre"),
};

const REGISTERED_LAYOUTS = new Set();
const LAYOUT_READY_FALLBACK_MS = 5000;

function nextLayoutRunToken(context) {
    if (!context) {
        return 0;
    }
    context.layoutRunToken = (context.layoutRunToken || 0) + 1;
    return context.layoutRunToken;
}

function isCurrentLayoutRun(context, token) {
    return !context || context.layoutRunToken === token;
}

function getLayoutName(layout) {
    if (typeof layout === "string") {
        return layout;
    }
    return layout?.name || "";
}

function getLayoutOptions(layout) {
    return typeof layout === "string" ? { name: layout } : layout;
}

async function ensureLayoutExtension(layout) {
    const name = getLayoutName(layout);
    const loadExtension = EXTENSION_LOADERS[name];
    if (!loadExtension || REGISTERED_LAYOUTS.has(name)) {
        return;
    }

    const module = await loadExtension();
    cytoscape.use(module.default || module);
    REGISTERED_LAYOUTS.add(name);
}

function emitLayoutError(context, layout, error) {
    const message = error?.message || String(error);
    console.error("Failed to run graph layout", layout, error);
    context?.setStreamlitValue?.({
        action: "layout_error",
        data: {
            layout: getLayoutName(layout),
            message,
        },
        timestamp: Date.now(),
    });
}

function setGraphReady(context, ready) {
    if (context?.isDestroyed) {
        return;
    }
    context
        ?.getElementById?.("container")
        ?.setAttribute("data-ready", String(ready));
}

function markReadyAfterLayout(context, cy, token) {
    let readyTimeout = null;
    let removeCleanup = null;
    const cleanupReadyWait = () => {
        if (readyTimeout !== null) {
            clearTimeout(readyTimeout);
            readyTimeout = null;
        }
        if (!cy.destroyed?.()) {
            cy.off("layoutstop", markReady);
        }
        removeCleanup?.();
        removeCleanup = null;
    };
    const markReady = () => {
        cleanupReadyWait();
        if (!isCurrentLayoutRun(context, token)) {
            return;
        }
        setGraphReady(context, true);
    };

    cy.one("layoutstop", markReady);
    readyTimeout = setTimeout(markReady, LAYOUT_READY_FALLBACK_MS);
    removeCleanup = context?.addCleanup?.(cleanupReadyWait) || null;
}

function runLayout(context, cy, layout) {
    const token = nextLayoutRunToken(context);
    setGraphReady(context, false);
    ensureLayoutExtension(layout)
        .then(() => {
            if (context?.isDestroyed || !isCurrentLayoutRun(context, token)) {
                return;
            }
            if (!cy || cy.destroyed?.()) {
                setGraphReady(context, true);
                return;
            }
            markReadyAfterLayout(context, cy, token);
            cy.layout(getLayoutOptions(layout)).run();
        })
        .catch((error) => {
            if (context?.isDestroyed || !isCurrentLayoutRun(context, token)) {
                return;
            }
            setGraphReady(context, true);
            emitLayoutError(context, layout, error);
        });
}

export { cytoscape, runLayout };
