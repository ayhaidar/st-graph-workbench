import { getSearchPayload } from "../utils/payloads.js";
import { loadedGraph } from "./expansionControls.js";

const IDS = {
    panel: "searchPanel",
    mode: "graphSearchMode",
    input: "graphSearchInput",
    apply: "graphSearchApply",
    clear: "graphSearchClear",
    status: "graphSearchStatus",
};

const SEARCH_MATCH_CLASS = "search-match";
const SEARCH_CONTEXT_CLASS = "search-context";
const SEARCH_FIT_PADDING = 80;
const SEARCH_ANIMATION_DURATION = 220;
const SEARCH_SELECTION_SUPPRESS_MS = 250;

function dataText(data) {
    return Object.values(data || {})
        .map((value) => {
            if (value && typeof value === "object") {
                return JSON.stringify(value);
            }
            return String(value);
        })
        .join(" ")
        .toLowerCase();
}

function parsePropertyQuery(query) {
    const separator = query.includes("=") ? "=" : ":";
    const parts = query.split(separator);
    if (parts.length < 2) {
        return null;
    }
    const key = parts.shift().trim();
    const value = parts.join(separator).trim();
    if (!key || !value) {
        return null;
    }
    return { key, value };
}

function searchClassSelector(className) {
    return `.${className}`;
}

function setStatus(context, message, state = "idle") {
    const status = context.getElementById(IDS.status);
    if (!status) {
        return;
    }
    status.textContent = message;
    status.dataset.state = state;
}

function matchCountText(count) {
    if (count === 0) {
        return "0 matches";
    }
    return count === 1 ? "1 match" : `${count} matches`;
}

function clearSearchMarks(cy) {
    cy.$(searchClassSelector(SEARCH_MATCH_CLASS)).removeClass(
        SEARCH_MATCH_CLASS
    );
    cy.$(searchClassSelector(SEARCH_CONTEXT_CLASS)).removeClass(
        SEARCH_CONTEXT_CLASS
    );
}

function getContextElements(matches) {
    return matches
        .nodes()
        .connectedEdges()
        .union(matches.edges().connectedNodes());
}

function getFocusElements(matches) {
    const matchedNodes = matches.nodes();
    if (!matchedNodes.empty()) {
        return matchedNodes;
    }

    return matches.edges().union(matches.edges().connectedNodes());
}

function focusMatches(cy, matches) {
    if (!matches || matches.empty()) {
        return;
    }

    const focus = getFocusElements(matches).filter(":visible");
    if (focus.empty()) {
        return;
    }

    if (focus.length === 1) {
        const currentZoom = cy.zoom();
        const maxZoom = cy.maxZoom();
        const targetZoom = Math.min(Math.max(currentZoom, 1.6), maxZoom || 1.6);
        const position = focus.position();
        const center = {
            x: cy.width() / 2,
            y: cy.height() / 2,
        };
        const targetPan = {
            x: center.x - position.x * targetZoom,
            y: center.y - position.y * targetZoom,
        };
        cy.animate(
            {
                pan: targetPan,
                zoom: { level: targetZoom },
            },
            { duration: SEARCH_ANIMATION_DURATION }
        );
        return;
    }

    cy.animate(
        {
            fit: { eles: focus, padding: SEARCH_FIT_PADDING },
        },
        { duration: SEARCH_ANIMATION_DURATION }
    );
}

function emitSearch(context, mode, query, matches) {
    const cy = context.getCyInstance();
    context.setImmediateStreamlitValue({
        action: "search",
        data: {
            ...getSearchPayload(cy, { mode, query, matches }),
            scope: context.searchScope || "visible",
            source_dataset_id: context.options.expansion?.source_id ?? null,
            source_version: context.options.expansion?.source_version ?? null,
            view_revision: context.options.expansion?.view_revision ?? null,
            node_count: matches.nodes().length,
            edge_count: matches.edges().length,
            collapsed_result_ids: matches
                .filter((element) => cy.getElementById(element.id()).empty())
                .map((element) => element.id()),
        },
        timestamp: Date.now(),
    });
}

function setInvalid(input, message) {
    input.dataset.invalid = "true";
    input.title = message;
}

function clearInvalid(input) {
    input.dataset.invalid = "false";
    input.title = "Search graph";
}

function getMatches(cy, mode, query, input) {
    const normalizedQuery = query.toLowerCase();
    clearInvalid(input);

    if (mode === "selector") {
        try {
            return cy.$(query);
        } catch {
            setInvalid(input, "Invalid Cytoscape selector");
            return cy.collection();
        }
    }

    if (mode === "node-label") {
        return cy.nodes().filter((node) => {
            return String(node.data("label") || "")
                .toLowerCase()
                .includes(normalizedQuery);
        });
    }

    if (mode === "edge-label") {
        return cy.edges().filter((edge) => {
            return String(edge.data("label") || "")
                .toLowerCase()
                .includes(normalizedQuery);
        });
    }

    if (mode === "property") {
        const parsed = parsePropertyQuery(query);
        if (!parsed) {
            setInvalid(input, "Use key:value or key=value");
            return cy.collection();
        }
        return cy.elements().filter((element) => {
            return String(element.data(parsed.key) ?? "") === parsed.value;
        });
    }

    return cy.elements().filter((element) => {
        return dataText(element.data()).includes(normalizedQuery);
    });
}

function applySearch(context) {
    const cy = context.getCyInstance();
    const mode = context.getElementById(IDS.mode);
    const input = context.getElementById(IDS.input);
    const query = input.value.trim();

    clearSearchMarks(cy);

    if (
        context.searchScope === "source" &&
        context.options.expansion?.source_search
    ) {
        context.emitExpansion("search", { text: query });
        return;
    }

    if (!query) {
        context.searchMatchIds = [];
        context.updateManagedSearch?.();
        context.suppressSelectionEmitUntil =
            Date.now() + SEARCH_SELECTION_SUPPRESS_MS;
        cy.$(":selected").unselect();
        clearInvalid(input);
        setStatus(context, "", "idle");
        emitSearch(context, mode.value, query, cy.collection());
        return;
    }

    const source =
        context.searchScope === "loaded" && context.options.expansion
            ? loadedGraph(context)
            : cy;
    let matches = getMatches(source, mode.value, query, input);
    if (context.options.expansion && source === cy)
        matches = matches.filter(":visible");
    const rendered = cy
        .elements()
        .filter((element) =>
            matches.some((match) => match.id() === element.id())
        );
    const contextElements = getContextElements(rendered).difference(rendered);
    context.searchMatchIds = matches.map((element) => element.id());
    context.updateManagedSearch?.();

    context.suppressSelectionEmitUntil =
        Date.now() + SEARCH_SELECTION_SUPPRESS_MS;
    cy.$(":selected").unselect();
    rendered.select();
    rendered.addClass(SEARCH_MATCH_CLASS);
    contextElements.addClass(SEARCH_CONTEXT_CLASS);
    setStatus(context, matchCountText(matches.length), "matched");
    focusMatches(cy, rendered);
    emitSearch(context, mode.value, query, matches);
}

function clearSearch(context) {
    const cy = context.getCyInstance();
    const input = context.getElementById(IDS.input);
    const searchMatches = cy.$(searchClassSelector(SEARCH_MATCH_CLASS));
    input.value = "";
    context.searchMatchIds = [];
    context.sourceSearchCleared = true;
    context.updateManagedSearch?.();
    clearInvalid(input);
    context.suppressSelectionEmitUntil =
        Date.now() + SEARCH_SELECTION_SUPPRESS_MS;
    searchMatches.unselect();
    clearSearchMarks(cy);
    setStatus(context, "", "idle");
    emitSearch(context, "clear", "", cy.collection());
}

function initSearch(context) {
    const panel = context.getElementById(IDS.panel);
    const input = context.getElementById(IDS.input);
    const apply = context.getElementById(IDS.apply);
    const clear = context.getElementById(IDS.clear);

    if (!panel) {
        return;
    }
    panel.hidden = !context.options.search;
    const scope = document.createElement("select");
    scope.id = "graphSearchScope";
    scope.className = "search-panel__select";
    scope.setAttribute("aria-label", "Search scope");
    for (const [value, label] of [
        ["visible", "Displayed"],
        ["loaded", "Loaded"],
        ["source", "Source"],
    ])
        scope.add(new Option(label, value));
    scope.addEventListener("change", () => {
        context.searchScope = scope.value;
        context.searchMatchIds = [];
        context.updateManagedSearch();
    });
    panel.appendChild(scope);
    const results = document.createElement("select");
    results.id = "graphSearchResults";
    results.className = "search-panel__select";
    results.setAttribute("aria-label", "Search results to reveal");
    panel.appendChild(results);
    const reveal = document.createElement("button");
    reveal.type = "button";
    reveal.id = "graphSearchReveal";
    reveal.textContent = "Reveal";
    reveal.className = "search-panel__button";
    reveal.addEventListener("click", () => {
        if (results.value) {
            context.pendingSearchReveal = results.value;
            context.emitExpansion("reveal", {
                node_ids: [results.value],
                scope: scope.value,
            });
        }
    });
    panel.appendChild(reveal);
    context.updateManagedSearch = () => {
        scope.hidden = !context.options.expansion;
        scope.querySelector('[value="source"]').disabled =
            !context.options.expansion?.source_search;
        const sourceResult = context.options.expansion?.search_result;
        if (context.lastSourceSearchResult !== sourceResult) {
            context.sourceSearchCleared = false;
            context.lastSourceSearchResult = sourceResult;
        }
        const values =
            scope.value === "source"
                ? context.sourceSearchCleared
                    ? []
                    : sourceResult?.node_ids || []
                : context.searchMatchIds || [];
        const previous = results.value;
        results.replaceChildren(...values.map((id) => new Option(id, id)));
        if (values.includes(previous)) results.value = previous;
        results.hidden = reveal.hidden =
            !context.options.expansion ||
            !values.length ||
            scope.value === "visible";
        const target = context
            .getCyInstance()
            .getElementById(context.pendingSearchReveal || "");
        if (target.nonempty() && target.visible()) {
            context.pendingSearchReveal = null;
            target.addClass(SEARCH_MATCH_CLASS);
            focusMatches(context.getCyInstance(), target);
        }
    };
    context.updateManagedSearch();

    apply?.addEventListener("click", () => applySearch(context));
    clear?.addEventListener("click", () => clearSearch(context));
    input?.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            applySearch(context);
        }
    });
}

function updateSearchVisibility(context) {
    const panel = context.getElementById(IDS.panel);
    if (panel) {
        panel.hidden = !context.options.search;
    }
}

export { updateSearchVisibility };
export default initSearch;
