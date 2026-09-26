import { setButtonState } from "../utils/dom.js";
import { createRequestId } from "../utils/helpers.js";

const IDS = {
    group: "progressiveLoading",
    status: "progressiveLoadingStatus",
    button: "progressiveLoadingButton",
};

function normalizedConfig(context) {
    const config = context.options.progressiveLoading;
    if (!config || typeof config !== "object") {
        return null;
    }

    return {
        pageSize: Number(config.page_size) || 100,
        loadedCount: Number(config.loaded_count) || 0,
        totalCount:
            config.total_count === null ? null : Number(config.total_count),
        hasMore: config.has_more !== false,
        cursor: config.cursor ?? null,
        acknowledgedRequestId: config.acknowledged_request_id ?? null,
    };
}

function configSignature(config) {
    // An acknowledgment for an older request must not complete the current one.
    return JSON.stringify([
        config.pageSize,
        config.loadedCount,
        config.totalCount,
        config.hasMore,
        config.cursor,
    ]);
}

function progressText(config) {
    if (config.totalCount === null) {
        return `${config.loadedCount.toLocaleString()} loaded`;
    }
    return `${config.loadedCount.toLocaleString()} / ${config.totalCount.toLocaleString()}`;
}

function initProgressiveLoading(context) {
    const group = context.getElementById(IDS.group);
    const status = context.getElementById(IDS.status);
    const button = context.getElementById(IDS.button);
    let pendingRequest = null;

    if (!group || !status || !button) {
        return () => {};
    }

    const update = () => {
        const config = normalizedConfig(context);
        group.hidden = config === null;
        if (!config) {
            pendingRequest = null;
            return;
        }

        const signature = configSignature(config);
        if (
            pendingRequest &&
            (signature !== pendingRequest.signature ||
                config.acknowledgedRequestId === pendingRequest.id)
        ) {
            pendingRequest = null;
        }
        const pending = pendingRequest !== null;
        status.textContent = progressText(config);
        setButtonState(button, {
            enabled: config.hasMore && !pending,
            title: pending
                ? "Loading next batch"
                : config.hasMore
                  ? `Load up to ${config.pageSize.toLocaleString()} more records`
                  : "All records loaded",
        });
        button.dataset.pending = String(pending);
    };

    const onClick = () => {
        const config = normalizedConfig(context);
        if (!config || !config.hasMore || pendingRequest !== null) {
            return;
        }

        const requestId = createRequestId();
        pendingRequest = { id: requestId, signature: configSignature(config) };
        update();
        const cy = context.getCyInstance();
        const remainingCount =
            config.totalCount === null
                ? null
                : Math.max(config.totalCount - config.loadedCount, 0);
        context.setImmediateStreamlitValue({
            action: "load_more",
            data: {
                request_id: requestId,
                cursor: config.cursor,
                page_size: config.pageSize,
                loaded_count: config.loadedCount,
                total_count: config.totalCount,
                remaining_count: remainingCount,
                current_node_count: cy?.nodes().length || 0,
                current_edge_count: cy?.edges().length || 0,
            },
            timestamp: Date.now(),
        });
    };

    button.addEventListener("click", onClick);
    context.addCleanup(() => button.removeEventListener("click", onClick));
    update();
    return update;
}

export default initProgressiveLoading;
