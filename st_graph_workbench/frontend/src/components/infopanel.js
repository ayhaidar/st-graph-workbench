import { getExpansionSummary } from "../utils/expansion.js";

// Constants / Configurations
const INFOPANEL_ID = "infopanel";
const LABEL_ID = "infopanelLabel";
const PROPS_ID = "infopanelProps";
const NODEACTIONS_ID = "nodeActions";

// Infopanel children updates
function _updateLabel(context, color, label, icon) {
    const label_div = context.getElementById(LABEL_ID);
    if (!label_div) {
        return;
    }
    const name = label_div.querySelector(".infopanel__name");
    const iconDiv = label_div.querySelector(".infopanel__icon");
    if (!name || !iconDiv) {
        return;
    }
    name.textContent = label;
    name.style.borderColor = color;
    iconDiv.style.backgroundColor = color;
    if (icon && icon != "none") {
        iconDiv.style.backgroundImage = `url(${icon})`;
    } else {
        iconDiv.style.backgroundImage = "";
    }
}

function modeLabel(mode) {
    if (mode === "multiple") {
        return "Multiple";
    }
    if (mode === "box") {
        return "Box";
    }
    return "Single";
}

function countLabel(count, singular, plural) {
    return `${count} ${count === 1 ? singular : plural}`;
}

function selectionCountLabel(selected) {
    const nodeCount = selected?.nodes().length || 0;
    const edgeCount = selected?.edges().length || 0;
    const total = nodeCount + edgeCount;

    if (total === 0) {
        return "0 selected";
    }

    if (nodeCount > 0 && edgeCount > 0) {
        return `${countLabel(nodeCount, "node", "nodes")}, ${countLabel(
            edgeCount,
            "edge",
            "edges"
        )}`;
    }

    if (nodeCount > 0) {
        return `${countLabel(nodeCount, "node", "nodes")} selected`;
    }

    return `${countLabel(edgeCount, "edge", "edges")} selected`;
}

function activeElementName(element) {
    const data = element.data();
    return data["name"] || data["id"] || element.id();
}

function getSelectionRows(context, selection, activeElement) {
    if (!activeElement) {
        return [];
    }

    const selected = selection?.selected;
    const rows = [
        [
            "Selection mode",
            modeLabel(context.options.selectionMode || "single"),
        ],
        ["Selected", selectionCountLabel(selected)],
    ];

    if ((selected?.length || 0) > 1) {
        rows.push(["Showing", activeElementName(activeElement)]);
    }

    return rows;
}

function valueText(value) {
    if (value === undefined) {
        return "";
    }
    if (
        value === null ||
        ["string", "number", "boolean"].includes(typeof value)
    ) {
        return String(value);
    }
    try {
        return JSON.stringify(value);
    } catch {
        return String(value);
    }
}

function createPropertyRow(documentRef, key, value) {
    const row = documentRef.createElement("div");
    const keyElement = documentRef.createElement("p");
    const valueElement = documentRef.createElement("p");

    row.className = "infopanel__prop";
    keyElement.className = "infopanel__key";
    valueElement.className = "infopanel__val";
    keyElement.textContent = String(key);
    valueElement.textContent = valueText(value);
    row.append(keyElement, valueElement);
    return row;
}

function _updateProps(context, data, selection, activeElement) {
    const props = context.getElementById(PROPS_ID);
    if (!props) {
        return;
    }
    const selectionRows = getSelectionRows(context, selection, activeElement);
    const expansionRows = getExpansionSummary(data);
    const dataRows = Object.entries(data)
        .filter((item) => {
            return !["label", "expansion"].includes(item[0]);
        })
        .map(([key, value]) => {
            return [key, value];
        });
    const documentRef = props.ownerDocument || document;
    props.replaceChildren(
        ...[...selectionRows, ...expansionRows, ...dataRows].map(
            ([key, value]) => createPropertyRow(documentRef, key, value)
        )
    );
}

function getActiveElement(selection) {
    const lastSelected = selection?.lastSelected;
    if (
        lastSelected &&
        !lastSelected.empty?.() &&
        lastSelected.inside?.() &&
        lastSelected.selected?.()
    ) {
        return lastSelected.first();
    }

    const selected = selection?.selected;
    if (selected?.length === 1) {
        return selected.first();
    }

    return null;
}

// infopanel update
function updateInfopanel(context) {
    const infopanel = context.getElementById(INFOPANEL_ID);
    const nodeActions = context.getElementById(NODEACTIONS_ID);
    const selection = context.state.getState("selection");
    const activeElement = getActiveElement(selection);
    infopanel.hidden = !context.state.getState("selectionDetailsVisible");
    let color, data, label, expanded, icon;
    if (activeElement) {
        color = activeElement.style().backgroundColor;
        data = activeElement.data();
        label =
            data["label"] || activeElement.group().slice(0, -1).toUpperCase();
        expanded = true;
        icon = activeElement.style()["background-image"];
    } else {
        color = "hsla(0, 0%, 0%, 0)";
        data = {};
        label = "";
        expanded = false;
        icon = null;
    }
    infopanel.setAttribute("data-expanded", expanded);
    nodeActions.setAttribute("data-expanded", expanded);
    _updateLabel(context, color, label, icon);
    _updateProps(context, data, selection, activeElement);
}

export default updateInfopanel;
