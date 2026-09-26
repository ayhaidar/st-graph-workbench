function debounce(func, wait) {
    let timeout;
    const debounced = function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
    debounced.cancel = function () {
        clearTimeout(timeout);
    };
    return debounced;
}

function createRequestId() {
    // Unlike randomUUID, getRandomValues also works on non-localhost HTTP origins.
    return Array.from(crypto.getRandomValues(new Uint32Array(4)), (value) =>
        value.toString(16).padStart(8, "0")
    ).join("");
}

const IMMEDIATE_EVENT_SUPPRESSION_MS = 500;
const REQUEST_QUEUES = new Map();

function updateComponentContext(
    context,
    { parentElement, setTriggerValue, setStateValue, data }
) {
    context.parentElement = parentElement || document;
    context.setTriggerValue = setTriggerValue;
    context.setStateValue = setStateValue;
    context.requestKey = data?.componentKey;
    const queue = REQUEST_QUEUES.get(context.requestKey) || [];
    const received = new Set(data?.receivedRequestIds || []);
    const remaining = queue.filter(
        (event) => !received.has(event.data.request_id)
    );
    if (remaining.length !== queue.length) {
        REQUEST_QUEUES.set(context.requestKey, remaining);
        setStateValue?.("requests", remaining);
    }
}

function createComponentContext(component, state) {
    const context = {
        cleanupCallbacks: new Set(),
        cy: null,
        isDestroyed: false,
        lastEventTimestamp: 0,
        options: {},
        parentElement: document,
        setTriggerValue: null,
        state: state,
    };

    context.getElementById = function (id) {
        if (context.parentElement.getElementById) {
            return context.parentElement.getElementById(id);
        }
        return context.parentElement.querySelector(`#${id}`);
    };

    context.setCyInstance = function (cy) {
        context.cy = cy;
    };

    context.addCleanup = function (callback) {
        if (typeof callback !== "function") {
            return () => {};
        }
        context.cleanupCallbacks.add(callback);
        return () => context.cleanupCallbacks.delete(callback);
    };

    context.cleanup = function () {
        if (context.isDestroyed) {
            return;
        }
        context.isDestroyed = true;
        context.debouncedSetValue?.cancel?.();
        context.cleanupCallbacks.forEach((callback) => {
            try {
                callback();
            } catch (error) {
                console.error("Failed to clean up graph component", error);
            }
        });
        context.cleanupCallbacks.clear();
        context.setTriggerValue = null;
    };

    context.getCyInstance = function () {
        if (!context.cy || context.cy.destroyed()) {
            console.error("Cytoscape instance not found.");
            return null;
        }
        return context.cy;
    };

    context.nextEventTimestamp = function (timestamp = Date.now()) {
        const numericTimestamp = Number(timestamp);
        const requestedTimestamp = Number.isFinite(numericTimestamp)
            ? numericTimestamp
            : Date.now();
        const eventTimestamp = Math.max(
            requestedTimestamp,
            context.lastEventTimestamp + 1
        );
        context.lastEventTimestamp = eventTimestamp;
        return eventTimestamp;
    };

    context.setStreamlitValue = function ({ action, data, timestamp } = {}) {
        if (context.isDestroyed) {
            return;
        }
        if (!context.setTriggerValue) {
            console.error("Streamlit v2 trigger bridge not configured.");
            return;
        }
        const event = {
            action: action,
            data: data,
            timestamp: context.nextEventTimestamp(timestamp),
        };
        if (
            ["expansion", "load_more"].includes(action) &&
            context.requestKey &&
            context.setStateValue
        ) {
            const queue = REQUEST_QUEUES.get(context.requestKey) || [];
            if (
                !queue.some((item) => item.data.request_id === data.request_id)
            ) {
                queue.push(event);
            }
            REQUEST_QUEUES.set(context.requestKey, queue);
            context.setStateValue("requests", [...queue]);
        } else {
            context.setTriggerValue("event", event);
        }
    };

    context.debouncedSetValue = debounce(context.setStreamlitValue, 100);
    context.setImmediateStreamlitValue = function (event = {}) {
        const now = Date.now();
        context.suppressSelectionEmitUntil = Math.max(
            context.suppressSelectionEmitUntil || 0,
            now + IMMEDIATE_EVENT_SUPPRESSION_MS
        );
        context.suppressPositionEmitUntil = Math.max(
            context.suppressPositionEmitUntil || 0,
            now + IMMEDIATE_EVENT_SUPPRESSION_MS
        );
        context.debouncedSetValue.cancel?.();
        context.setStreamlitValue(event);
    };
    updateComponentContext(context, component);
    return context;
}

export {
    createComponentContext,
    createRequestId,
    debounce,
    updateComponentContext,
};
