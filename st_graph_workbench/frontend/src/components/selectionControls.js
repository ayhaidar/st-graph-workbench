import { setButtonState } from "../utils/dom.js";

const IDS = {
    selectAll: "selectionSelectAll",
    clear: "selectionClear",
    focus: "selectionFocus",
    hideUnselected: "selectionHideUnselected",
    restore: "selectionRestore",
    infopanelClear: "infopanelClear",
    details: "selectionShowDetails",
};

function emitVisibility(context, action, data) {
    context.setImmediateStreamlitValue({
        action: action,
        data: data,
        timestamp: Date.now(),
    });
}

function selectedVisibleElements(cy) {
    return cy.elements(":selected").filter(":visible");
}

function currentNodeActions(context) {
    return new Set(context.options.nodeActions || []);
}

function updateVisibilityControls(context) {
    const cy = context.getCyInstance();
    const activeActions = currentNodeActions(context);
    const hideUnselected = context.getElementById(IDS.hideUnselected);
    const restore = context.getElementById(IDS.restore);
    const selectedCount = selectedVisibleElements(cy).length;
    const hiddenCount =
        cy.elements(":hidden").length +
        (context.options.expansion?.hidden_count || 0);

    if (hideUnselected) {
        const isActive = activeActions.has("hide_unselected");
        hideUnselected.hidden = !isActive;
        setButtonState(hideUnselected, {
            enabled: isActive && selectedCount > 0,
            title:
                selectedCount > 0
                    ? "Hide Unselected"
                    : "Select elements to hide unselected",
        });
    }

    if (restore) {
        const isActive = activeActions.has("restore_hidden");
        restore.hidden = !isActive;
        setButtonState(restore, {
            enabled: isActive && hiddenCount > 0,
            title:
                hiddenCount > 0
                    ? "Restore Hidden"
                    : "No hidden elements to restore",
        });
    }
}

function canRunNodeAction(context, action) {
    return currentNodeActions(context).has(action);
}

function initSelectionControls(context) {
    const cy = context.getCyInstance();
    const selectAll = context.getElementById(IDS.selectAll);
    const clear = context.getElementById(IDS.clear);
    const focus = context.getElementById(IDS.focus);
    const hideUnselected = context.getElementById(IDS.hideUnselected);
    const restore = context.getElementById(IDS.restore);
    const infopanelClear = context.getElementById(IDS.infopanelClear);
    const details = context.getElementById(IDS.details);
    const menu = context.getElementById("selectionControls");

    selectAll?.addEventListener("click", () => {
        cy.elements(":visible").select();
    });
    const clearSelection = () => {
        // Explicit clearing also resets analysis decoration, not search matches.
        cy.elements(".analysis-result").removeClass("analysis-result");
        cy.elements(":selected").unselect();
    };
    clear?.addEventListener("click", clearSelection);
    details?.addEventListener("change", () => {
        context.state.updateState("selectionDetailsVisible", details.checked);
    });
    infopanelClear?.addEventListener("click", () => {
        clearSelection();
        context
            .getElementById("selectionControls")
            ?.querySelector("summary")
            ?.focus({ preventScroll: true });
    });
    focus?.addEventListener("click", () => {
        const selected = selectedVisibleElements(cy);
        if (selected.length > 0) {
            cy.animate({
                fit: { eles: selected, padding: 40 },
                duration: 180,
            });
        }
    });
    hideUnselected?.addEventListener("click", () => {
        if (!canRunNodeAction(context, "hide_unselected")) {
            return;
        }
        const selected = selectedVisibleElements(cy);
        if (selected.length === 0) {
            return;
        }
        const keep = selected
            .union(selected.nodes().connectedEdges())
            .union(selected.edges().connectedNodes());
        cy.elements().not(keep).hide();
        context.updateGraphStats?.();
        emitVisibility(context, "visibility", {
            operation: "hide_unselected",
            visible_node_ids: cy.nodes(":visible").map((node) => node.id()),
            visible_edge_ids: cy.edges(":visible").map((edge) => edge.id()),
        });
        updateVisibilityControls(context);
    });
    restore?.addEventListener("click", () => {
        if (!canRunNodeAction(context, "restore_hidden")) {
            return;
        }
        cy.elements().show();
        context.updateGraphStats?.();
        emitVisibility(context, "visibility", {
            operation: "restore_hidden",
            visible_node_ids: cy.nodes(":visible").map((node) => node.id()),
            visible_edge_ids: cy.edges(":visible").map((edge) => edge.id()),
        });
        updateVisibilityControls(context);
    });

    const update = () => {
        if (details) {
            details.checked = context.state.getState("selectionDetailsVisible");
        }
        updateVisibilityControls(context);
        if (menu?.open) {
            // The labelled preference is wider than the old icon-only menu.
            const content = menu.querySelector(".toolbox__menu-content");
            const bounds = context
                .getElementById("container")
                .getBoundingClientRect();
            const anchor = menu.getBoundingClientRect().left;
            const left = Math.max(
                bounds.left + 8,
                Math.min(anchor, bounds.right - content.offsetWidth - 8)
            );
            content.style.left = `${left - anchor}px`;
        }
    };
    menu?.addEventListener("toggle", update);
    context.state.subscribe("selection", update);
    context.state.subscribe("selectionDetailsVisible", update);
    cy.on("select unselect hide show add remove", update);
    update();
    return update;
}

export default initSelectionControls;
