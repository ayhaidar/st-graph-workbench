const IDS = {
    container: "container",
    topbar: "graphTopbar",
    collapse: "toolbarCollapse",
    searchToggle: "toolbarSearchToggle",
    searchPanel: "searchPanel",
    searchInput: "graphSearchInput",
    status: "toolbarModeStatus",
};
const COMPACT_BREAKPOINT = 760;
const MANAGED_COMPACT_BREAKPOINT = 900;

function normalizedConfig(context) {
    const config = context.options.toolbar || {};
    return {
        mode: config.mode || "adaptive",
        position: config.position || "top",
        collapsible: config.collapsible !== false,
        sticky: config.sticky !== false,
    };
}

function configSignature(config) {
    return JSON.stringify([
        config.mode,
        config.position,
        config.collapsible,
        config.sticky,
    ]);
}

function baseMode(config, width, managedExpansion) {
    if (config.mode === "adaptive" || config.mode === "minimized") {
        const breakpoint = managedExpansion
            ? MANAGED_COMPACT_BREAKPOINT
            : COMPACT_BREAKPOINT;
        return width < breakpoint ? "compact" : "expanded";
    }
    return config.mode;
}

function closeMenus(topbar) {
    topbar.querySelectorAll("details[open]").forEach((menu) => {
        menu.open = false;
    });
}

function initToolbarLayout(context) {
    const container = context.getElementById(IDS.container);
    const topbar = context.getElementById(IDS.topbar);
    const collapse = context.getElementById(IDS.collapse);
    const searchToggle = context.getElementById(IDS.searchToggle);
    const searchPanel = context.getElementById(IDS.searchPanel);
    const searchInput = context.getElementById(IDS.searchInput);
    const status = context.getElementById(IDS.status);
    let resizeObserver = null;
    let syncingOption = false;
    let resizeFrame = null;
    let initialStageChecked = false;
    let initialLayoutListening = false;

    if (!container || !topbar || !collapse || !searchToggle || !searchPanel) {
        return () => {};
    }

    const checkInitialStage = () => {
        const cy = context.getCyInstance();
        if (
            initialStageChecked ||
            context.isDestroyed ||
            !cy ||
            cy.destroyed() ||
            container.dataset.ready !== "true"
        ) {
            return;
        }
        initialStageChecked = true;
        cy.off("layoutstop", scheduleInitialStageCheck);
        const nodes = cy.nodes(":visible");
        if (nodes.length === 0) return;
        const bounds = nodes.renderedBoundingBox({
            includeLabels: true,
            includeOverlays: false,
        });
        const clipped =
            bounds.x1 < 0 ||
            bounds.y1 < 0 ||
            bounds.x2 > cy.width() ||
            bounds.y2 > cy.height();
        if (clipped) cy.fit(nodes, 30);
        context.updateExpansionBadges?.();
    };

    function scheduleInitialStageCheck() {
        requestAnimationFrame(checkInitialStage);
    }

    const scheduleGraphResize = () => {
        if (resizeFrame !== null) cancelAnimationFrame(resizeFrame);
        resizeFrame = requestAnimationFrame(() => {
            resizeFrame = null;
            const config = normalizedConfig(context);
            const containerBounds = container.getBoundingClientRect();
            const topbarBounds = topbar.getBoundingClientRect();
            const graphStageTop = config.sticky
                ? Math.max(0, topbarBounds.bottom - containerBounds.top + 8)
                : 0;
            container.style.setProperty(
                "--graph-stage-top",
                `${graphStageTop}px`
            );
            const cy = context.getCyInstance();
            if (cy && !cy.destroyed()) {
                cy.resize();
                if (!initialStageChecked) {
                    if (!initialLayoutListening) {
                        initialLayoutListening = true;
                        cy.on("layoutstop", scheduleInitialStageCheck);
                    }
                    scheduleInitialStageCheck();
                }
            }
            context.updateExpansionBadges?.();
        });
    };

    const syncPythonOption = (config) => {
        const signature = configSignature(config);
        if (context.state.getState("toolbarOption") === signature) return;
        syncingOption = true;
        context.state.updateState("toolbarOption", signature);
        context.state.updateState(
            "toolbarMinimized",
            config.mode === "minimized"
        );
        context.state.updateState("toolbarSearchExpanded", false);
        syncingOption = false;
    };

    const update = () => {
        if (context.isDestroyed) return;
        const config = normalizedConfig(context);
        syncPythonOption(config);
        if (syncingOption) return;

        const minimized = context.state.getState("toolbarMinimized");
        const effectiveMode = minimized
            ? "minimized"
            : baseMode(
                  config,
                  container.clientWidth,
                  container.dataset.managedExpansion === "true"
              );
        const searchExpanded = Boolean(
            effectiveMode === "compact" &&
                context.options.search &&
                context.state.getState("toolbarSearchExpanded")
        );

        container.dataset.toolbarMode = config.mode;
        container.dataset.toolbarEffectiveMode = effectiveMode;
        container.dataset.toolbarPosition = config.position;
        container.dataset.toolbarSticky = String(config.sticky);
        container.dataset.toolbarSearchExpanded = String(searchExpanded);
        searchPanel.dataset.toolbarSearchExpanded = String(searchExpanded);

        collapse.hidden = !config.collapsible;
        collapse.setAttribute(
            "aria-expanded",
            String(effectiveMode !== "minimized")
        );
        const collapseLabel =
            effectiveMode === "minimized"
                ? "Restore toolbar"
                : "Minimize toolbar";
        collapse.title = collapseLabel;
        collapse.setAttribute("aria-label", collapseLabel);

        searchToggle.hidden =
            !context.options.search || effectiveMode !== "compact";
        searchToggle.setAttribute("aria-expanded", String(searchExpanded));
        const searchLabel = searchExpanded
            ? "Close search controls"
            : "Open search controls";
        searchToggle.title = searchLabel;
        searchToggle.setAttribute("aria-label", searchLabel);

        if (effectiveMode === "minimized") closeMenus(topbar);
        if (status) status.textContent = `Graph toolbar ${effectiveMode}`;
        scheduleGraphResize();
    };

    const toggleCollapsed = () => {
        const minimized = context.state.getState("toolbarMinimized");
        context.state.updateState("toolbarMinimized", !minimized);
        collapse.focus();
    };
    const toggleSearch = () => {
        const expanded = context.state.getState("toolbarSearchExpanded");
        context.state.updateState("toolbarSearchExpanded", !expanded);
        if (!expanded) requestAnimationFrame(() => searchInput?.focus());
    };

    collapse.addEventListener("click", toggleCollapsed);
    searchToggle.addEventListener("click", toggleSearch);
    context.state.subscribe("toolbarMinimized", update);
    context.state.subscribe("toolbarSearchExpanded", update);
    context.state.subscribe("toolbarOption", update);
    if (typeof ResizeObserver === "function") {
        resizeObserver = new ResizeObserver(update);
        resizeObserver.observe(container);
    }
    context.addCleanup?.(() => {
        collapse.removeEventListener("click", toggleCollapsed);
        searchToggle.removeEventListener("click", toggleSearch);
        resizeObserver?.disconnect();
        const cy = context.getCyInstance();
        if (cy && !cy.destroyed()) {
            cy.off("layoutstop", scheduleInitialStageCheck);
        }
        if (resizeFrame !== null) cancelAnimationFrame(resizeFrame);
    });
    update();
    return update;
}

export default initToolbarLayout;
