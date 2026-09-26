import { debounce } from "../utils/helpers";
import { getPositionsPayload } from "../utils/payloads.js";
import { runLayout } from "../utils/layouts.js";

// Constants / Configurations
const IDS = {
    fullscreen: "toolbarFullscreen",
    refresh: "toolbarRefresh",
    exportVisible: "toolbarExport",
    exportFull: "toolbarExportFull",
    exportSelected: "toolbarExportSelected",
    exportPng: "toolbarExportPng",
    exportJpg: "toolbarExportJpg",
    exportPositions: "toolbarExportPositions",
};
const DELAYS = {
    default: 150,
    fullscreen: 100,
    refresh: 200,
    export: 250,
};

function downloadText(filename, text, type = "application/json") {
    const blob = new Blob([text], { type: type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

function downloadJson(filename, data) {
    downloadText(filename, JSON.stringify(data, null, 2));
}

function downloadDataUrl(filename, url) {
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function selectedSubgraph(cy) {
    const selected = cy.elements(":selected");
    return selected
        .union(selected.nodes().connectedEdges())
        .union(selected.edges().connectedNodes())
        .jsons();
}

function createClickHandlers(context) {
    return {
        fullscreen: debounce(() => {
            if (document.fullscreenElement) {
                document.exitFullscreen();
            } else {
                context.getElementById("container").requestFullscreen();
            }
        }, DELAYS.fullscreen),

        refresh: debounce(() => {
            const cy = context.getCyInstance();
            runLayout(context, cy, context.state.getState("layout"));
        }, DELAYS.refresh),

        export: debounce(() => {
            const cy = context.getCyInstance();
            downloadJson("graph-visible.json", cy.elements(":visible").jsons());
        }, DELAYS.export),

        exportFull: debounce(() => {
            const cy = context.getCyInstance();
            downloadJson("graph-full.json", cy.json().elements);
        }, DELAYS.export),

        exportSelected: debounce(() => {
            const cy = context.getCyInstance();
            downloadJson("graph-selected.json", selectedSubgraph(cy));
        }, DELAYS.export),

        exportPng: debounce(() => {
            const cy = context.getCyInstance();
            downloadDataUrl("graph.png", cy.png({ full: true, scale: 2 }));
        }, DELAYS.export),

        exportJpg: debounce(() => {
            const cy = context.getCyInstance();
            downloadDataUrl(
                "graph.jpg",
                cy.jpg({ full: true, quality: 0.92, bg: "#ffffff" })
            );
        }, DELAYS.export),

        exportPositions: debounce(() => {
            const cy = context.getCyInstance();
            downloadJson("graph-positions.json", getPositionsPayload(cy));
        }, DELAYS.export),
    };
}

// Toolbar initialization
function initToolbar(context) {
    const clickHandlers = createClickHandlers(context);
    context
        .getElementById(IDS.fullscreen)
        .addEventListener("click", clickHandlers.fullscreen);
    context
        .getElementById(IDS.refresh)
        .addEventListener("click", clickHandlers.refresh);
    context
        .getElementById(IDS.exportVisible)
        .addEventListener("click", clickHandlers.export);
    context
        .getElementById(IDS.exportFull)
        .addEventListener("click", clickHandlers.exportFull);
    context
        .getElementById(IDS.exportSelected)
        .addEventListener("click", clickHandlers.exportSelected);
    context
        .getElementById(IDS.exportPng)
        .addEventListener("click", clickHandlers.exportPng);
    context
        .getElementById(IDS.exportJpg)
        .addEventListener("click", clickHandlers.exportJpg);
    context
        .getElementById(IDS.exportPositions)
        .addEventListener("click", clickHandlers.exportPositions);
}

export default initToolbar;
