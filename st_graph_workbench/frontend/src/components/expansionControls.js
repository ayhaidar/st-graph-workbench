import cytoscape from "cytoscape";
import { createRequestId } from "../utils/helpers.js";

function button(label, operation, context, extra = {}) {
    const element = document.createElement("button");
    element.type = "button";
    element.textContent = label;
    element.className = "graph-context-menu__item";
    element.dataset.operation = operation;
    element.addEventListener("click", () => {
        context.emitExpansion(operation, extra);
        context.expansionMenu.hidden = true;
    });
    return element;
}

export function analysisGraph(context) {
    if (context.analysisScope !== "loaded" || !context.options.expansion) {
        return context.getCyInstance();
    }
    const graph = loadedGraph(context);
    graph.elements().unselect();
    context
        .getCyInstance()
        .nodes(":selected:visible")
        .forEach((node) => graph.getElementById(node.id()).select());
    return graph;
}

export function loadedGraph(context) {
    const config = context.options.expansion;
    const revision = `${config.controller_id}:${config.view_revision}`;
    if (context.loadedAnalysisRevision !== revision) {
        context.loadedAnalysisCy?.destroy();
        context.loadedAnalysisCy = cytoscape({
            headless: true,
            elements: config.loaded,
        });
        context.loadedAnalysisCy.scratch("analysisScope", "loaded");
        context.loadedAnalysisRevision = revision;
    }
    return context.loadedAnalysisCy;
}

export default function initExpansionControls(context) {
    const container = context.getElementById("container");
    const menu = document.createElement("div");
    menu.className = "graph-context-menu managed-expansion-menu";
    menu.id = "managedExpansionMenu";
    menu.setAttribute("role", "menu");
    menu.hidden = true;
    container.appendChild(menu);
    context.expansionMenu = menu;
    const bar = document.createElement("div");
    bar.className = "managed-expansion-bar";
    bar.id = "managedExpansionBar";
    container.appendChild(bar);
    const launch = document.createElement("button");
    launch.type = "button";
    launch.title = "Explore connections";
    launch.setAttribute("aria-label", launch.title);
    const icon = context
        .getElementById("nodeActionsExpand")
        ?.querySelector("svg");
    if (icon) launch.appendChild(icon.cloneNode(true));
    else launch.textContent = "+";
    bar.appendChild(launch);
    const status = document.createElement("span");
    status.setAttribute("role", "status");
    bar.appendChild(status);
    const dialog = document.createElement("dialog");
    dialog.id = "expansionDialog";
    dialog.className = "expansion-dialog";
    dialog.setAttribute("aria-label", "Explore connections");
    dialog.innerHTML = `<form method="dialog">
        <h3>Explore connections</h3>
        <label>Direction<select name="direction"><option value="both">Both</option><option value="outgoing">Outgoing</option><option value="incoming">Incoming</option></select></label>
        <label>Relationship types<input name="relationships" placeholder="All types" /></label>
        <label>Exact-match attributes<textarea name="attributes" rows="2">{}</textarea></label>
        <label>Time field<input name="time_field" value="observed_at" /></label>
        <div class="expansion-time-range">
        <label>Page size<input name="page_size" type="number" min="1" required /></label>
        <label>Maximum depth<input name="max_depth" type="number" min="1" required /></label>
        <label>Additional node limit<input name="max_nodes" type="number" min="1" required /></label>
        <label>Additional edge limit<input name="max_edges" type="number" min="1" required /></label>
        </div>
        <div class="expansion-time-range"><label>From<input name="time_from" type="datetime-local" /></label><label>To<input name="time_to" type="datetime-local" /></label></div>
        <p class="expansion-error" role="alert"></p>
        <div class="expansion-dialog-actions"></div>
        <h4>Open and cached branches</h4><div class="expansion-branch-list"></div>
        <button type="submit">Close</button>
    </form>`;
    container.appendChild(dialog);
    dialog.querySelectorAll("label").forEach((label) => {
        label
            .querySelector("input, select, textarea")
            ?.setAttribute("aria-label", label.firstChild.textContent.trim());
    });
    const selected = () =>
        context
            .getCyInstance()
            .nodes(":selected:visible")
            .map((node) => node.id());
    context.emitExpansion = (operation, extra = {}) => {
        context.setImmediateStreamlitValue({
            action: "expansion",
            data: {
                operation,
                node_ids: selected(),
                request_id: createRequestId(),
                controller_id: context.options.expansion.controller_id,
                ...extra,
            },
            timestamp: Date.now(),
        });
    };
    const openDialog = () => {
        context.getElementById("graphContextMenu").hidden = true;
        menu.hidden = true;
        if (!dialog.open) dialog.showModal();
    };
    launch.addEventListener("click", openDialog);
    const actions = dialog.querySelector(".expansion-dialog-actions");
    const query = () => {
        const form = dialog.querySelector("form");
        const attributes = JSON.parse(form.elements.attributes.value);
        if (
            !attributes ||
            typeof attributes !== "object" ||
            Array.isArray(attributes)
        )
            throw new Error("Attributes must be a JSON object.");
        const result = {
            direction: form.elements.direction.value,
            relationships: form.elements.relationships.value
                .split(",")
                .map((s) => s.trim())
                .filter(Boolean),
            attributes,
        };
        for (const field of ["time_field", "time_from", "time_to"]) {
            if (form.elements[field].value)
                result[field] = form.elements[field].value;
        }
        return result;
    };
    for (const [label, operation] of [
        ["Expand connections", "expand"],
        ["Load more", "load_more"],
        ["Expand all within scope", "expand_all"],
        ["Collapse selected", "collapse"],
        ["Collapse all", "collapse_all"],
        ["Cancel loading", "cancel"],
        ["Retry loading", "retry"],
    ]) {
        const item = document.createElement("button");
        item.type = "button";
        item.textContent = label;
        item.dataset.operation = operation;
        item.addEventListener("click", () => {
            try {
                dialog.querySelector(".expansion-error").textContent = "";
                const form = dialog.querySelector("form");
                if (!form.reportValidity()) return;
                const limits = Object.fromEntries(
                    ["page_size", "max_depth", "max_nodes", "max_edges"].map(
                        (name) => [name, Number(form.elements[name].value)]
                    )
                );
                context.emitExpansion(operation, { query: query(), limits });
                dialog.close();
            } catch (error) {
                dialog.querySelector(".expansion-error").textContent =
                    error.message;
            }
        });
        actions.appendChild(item);
    }
    const analysisScope = document.createElement("select");
    analysisScope.title = "Analysis scope";
    analysisScope.setAttribute("aria-label", "Analysis scope");
    for (const [value, label] of [
        ["visible", "Displayed graph"],
        ["loaded", "Loaded records"],
        ["source", "Source dataset"],
    ]) {
        analysisScope.add(new Option(label, value));
    }
    analysisScope.addEventListener("change", () => {
        context.analysisScope = analysisScope.value;
    });
    bar.appendChild(analysisScope);
    context.showExpansionMenu = (node, position) => {
        const cy = context.getCyInstance();
        if (!node.selected()) {
            cy.elements(":selected").unselect();
            node.select();
        }
        menu.replaceChildren();
        const rows = selected()
            .map((id) => context.options.expansion.nodes[id])
            .filter(Boolean);
        for (const [label, operation, enabled] of [
            [
                "Expand connections",
                "expand",
                rows.some((row) => row.can_expand),
            ],
            ["Load more", "load_more", rows.some((row) => row.can_load_more)],
            [
                "Collapse connections",
                "collapse",
                rows.some((row) => row.can_collapse),
            ],
            ["Keep visible", "protect", rows.some((row) => !row.protected)],
            ["Allow collapse", "unprotect", rows.some((row) => row.protected)],
        ]) {
            const item = button(label, operation, context);
            item.setAttribute("role", "menuitem");
            item.disabled = !enabled;
            menu.appendChild(item);
        }
        const explore = document.createElement("button");
        explore.type = "button";
        explore.textContent = "Explore connections...";
        explore.className = "graph-context-menu__item";
        explore.addEventListener("click", openDialog);
        menu.appendChild(explore);
        menu.hidden = false;
        menu.style.left = `${Math.max(4, Math.min(position.x + 8, container.clientWidth - menu.offsetWidth - 8))}px`;
        menu.style.top = `${Math.max(4, Math.min(position.y + 8, container.clientHeight - menu.offsetHeight - 8))}px`;
        menu.querySelector("button:not(:disabled)")?.focus();
    };
    const hide = (event) => {
        if (event.type !== "tap" || event.target === context.getCyInstance())
            menu.hidden = true;
    };
    context.getCyInstance().on("tap pan zoom drag", hide);
    container.addEventListener("keydown", (event) => {
        if (event.key === "Escape") menu.hidden = true;
    });
    const update = () => {
        const config = context.options.expansion;
        container.dataset.managedExpansion = Boolean(config);
        bar.hidden = !config;
        if (!config) {
            menu.hidden = true;
            dialog.close();
            return;
        }
        const selectedRows = selected()
            .map((id) => config.nodes[id])
            .filter(Boolean);
        if (!dialog.open) {
            for (const [name, value] of Object.entries(config.limits))
                dialog.querySelector("form").elements[name].value = value;
        }
        for (const [operation, field] of [
            ["expand", "can_expand"],
            ["load_more", "can_load_more"],
            ["collapse", "can_collapse"],
        ]) {
            const item = menu.querySelector(`[data-operation="${operation}"]`);
            if (item) item.disabled = !selectedRows.some((row) => row[field]);
        }
        analysisScope.querySelector('[value="source"]').disabled =
            !config.source_analysis;
        const failures = Object.values(config.nodes).filter((row) => row.error);
        status.textContent = failures.length
            ? failures[0].error
            : config.bulk
              ? `${config.bulk.status}: ${config.bulk.batches} batches`
              : "";
        if (config.error) status.textContent = config.error;
        const bulkToken = config.bulk
            ? `${config.bulk.id}:${config.bulk.batches}:${config.view_revision}`
            : "";
        if (
            config.bulk?.status === "running" &&
            context.bulkToken !== bulkToken
        ) {
            context.bulkToken = bulkToken;
            clearTimeout(context.bulkTimer);
            context.bulkTimer = setTimeout(() => {
                if (
                    !context.isDestroyed &&
                    context.options.expansion?.bulk?.status === "running"
                )
                    context.emitExpansion("continue");
            }, 200);
        }
        context.updateManagedSearch?.();
        const analysis = config.analysis_result;
        const analysisToken = JSON.stringify(analysis);
        if (analysis && context.sourceAnalysisToken !== analysisToken) {
            context.sourceAnalysisToken = analysisToken;
            const matches = new Set([
                ...(analysis.node_ids || []),
                ...(analysis.edge_ids || []),
                ...(analysis.node_id ? [analysis.node_id] : []),
                ...(analysis.components || []).flatMap((group) => [
                    ...group.node_ids,
                    ...group.edge_ids,
                ]),
            ]);
            const cy = context.getCyInstance();
            cy.elements().removeClass("analysis-result");
            cy.elements(":visible")
                .filter((element) => matches.has(element.id()))
                .addClass("analysis-result");
        }
        const list = dialog.querySelector(".expansion-branch-list");
        list.replaceChildren();
        for (const branch of config.branches) {
            const row = document.createElement("div");
            const text = document.createElement("span");
            const filters = [
                JSON.stringify(branch.query.attributes),
                branch.query.time_from,
                branch.query.time_to,
            ]
                .filter((value) => value && value !== "{}")
                .join(" | ");
            text.textContent = `${branch.node_id} | ${branch.query.direction} | ${branch.query.relationships.join(", ") || "All types"} | ${branch.active ? "Open" : branch.opened ? "Suspended" : "Cached"}${filters ? ` | ${filters}` : ""}`;
            row.appendChild(text);
            row.appendChild(
                button(
                    branch.opened ? "Collapse branch" : "Restore branch",
                    branch.opened ? "collapse" : "expand",
                    context,
                    {
                        branch_id: branch.branch_id,
                        node_ids: branch.opened ? [] : [branch.node_id],
                        query: branch.query,
                    }
                )
            );
            list.appendChild(row);
        }
    };
    context.addCleanup(() => {
        clearTimeout(context.bulkTimer);
        menu.remove();
        bar.remove();
        dialog.remove();
        context.loadedAnalysisCy?.destroy();
    });
    update();
    return update;
}
