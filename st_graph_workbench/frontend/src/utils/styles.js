// Color theme
const COLOR = {
    dark: {
        highlight: "rgb(210, 0, 0)",
        selection: "rgb(66, 153, 255)",
        line: "rgb(48, 49, 57)",
        font: "rgb(250, 250, 250)",
        border: "rgb(48, 49, 57)",
        fontHighlight: "rgb(250, 250, 250)",
    },
    light: {
        line: "rgb(195,195,195)",
        font: "rgb(5,5,5)",
        border: "rgb(250,250,250)",
        highlight: "rgb(255,50,50)",
        selection: "rgb(0, 107, 230)",
        fontHighlight: "rgb(250, 250, 250)",
    },
};

// Common style configs
const fixedNodeStyles = {
    "width": 20,
    "height": 20,
    "border-width": 0.8,
    "font-size": 3.6,
    "text-valign": "bottom",
    "text-margin-y": 3.2,
    "background-repeat": "no-repeat",
    "background-width": "60%",
    "background-height": "60%",
    "background-color": "#0a0a0a",
};

const fixedEdgeStyles = {
    "width": 2,
    "font-size": 3.2,
    "text-rotation": "autorotate",
    "text-background-padding": 1,
    "text-background-opacity": 1,
    "text-background-shape": "round-rectangle",
    "arrow-scale": 0.6,
    "curve-style": "bezier",
};

const fixedNodeHStyles = {
    "outline-width": 0.6,
    "font-weight": "bold",
    "text-background-opacity": 1,
    "text-background-shape": "round-rectangle",
    "text-background-padding": 1,
};

const fixedEdgeHStyles = {
    "font-weight": "bold",
};

function _getDefault(theme) {
    return [
        {
            selector: "*",
            style: {
                "min-zoomed-font-size": 10,
            },
        },
        {
            selector: "node",
            style: {
                ...fixedNodeStyles,
                "color": COLOR[theme].font,
                "border-color": COLOR[theme].border,
            },
        },
        {
            selector: "edge",
            style: {
                ...fixedEdgeStyles,
                "color": COLOR[theme].font,
                "line-color": COLOR[theme].line,
                "background-color": COLOR[theme].line,
                "target-arrow-color": COLOR[theme].line,
                "text-background-color": COLOR[theme].line,
            },
        },
    ];
}

function _getHighlight(theme) {
    return [
        {
            selector: "node.highlight",
            style: {
                ...fixedNodeHStyles,
                "color": COLOR[theme].fontHighlight,
                "text-background-color": COLOR[theme].highlight,
                "outline-color": COLOR[theme].highlight,
            },
        },
        {
            selector: "edge.highlight",
            style: {
                ...fixedEdgeHStyles,
                "color": COLOR[theme].fontHighlight,
                "line-color": COLOR[theme].highlight,
                "target-arrow-color": COLOR[theme].highlight,
                "text-background-color": COLOR[theme].highlight,
            },
        },
        {
            selector: "node:selected",
            style: {
                ...fixedNodeHStyles,
                "border-color": COLOR[theme].selection,
                "border-width": 2.4,
                "color": COLOR[theme].fontHighlight,
                "outline-color": COLOR[theme].selection,
                "outline-width": 1.6,
                "text-background-color": COLOR[theme].selection,
                "z-index": 9999,
            },
        },
        {
            selector: "edge:selected",
            style: {
                ...fixedEdgeHStyles,
                "color": COLOR[theme].fontHighlight,
                "line-color": COLOR[theme].selection,
                "source-arrow-color": COLOR[theme].selection,
                "target-arrow-color": COLOR[theme].selection,
                "text-background-color": COLOR[theme].selection,
                "width": 4,
                "z-index": 9998,
            },
        },
        {
            selector: "node.search-match",
            style: {
                "outline-width": 2,
                "outline-color": "hsl(38, 100%, 50%)",
                "text-background-color": "hsl(38, 100%, 50%)",
                "z-index": 9999,
            },
        },
        {
            selector: "edge.search-match",
            style: {
                "line-color": "hsl(38, 100%, 50%)",
                "source-arrow-color": "hsl(38, 100%, 50%)",
                "target-arrow-color": "hsl(38, 100%, 50%)",
                "text-background-color": "hsl(38, 100%, 50%)",
                "width": 4,
                "z-index": 9998,
            },
        },
        {
            selector: "node.search-context",
            style: {
                "outline-width": 1,
                "outline-color": "hsl(38, 100%, 65%)",
                "z-index": 9997,
            },
        },
        {
            selector: "edge.search-context",
            style: {
                "line-color": "hsl(38, 100%, 65%)",
                "source-arrow-color": "hsl(38, 100%, 65%)",
                "target-arrow-color": "hsl(38, 100%, 65%)",
                "width": 3,
                "z-index": 9996,
            },
        },
        {
            selector: "node.analysis-result",
            style: {
                "outline-width": 1.2,
                "outline-color": "hsl(45, 100%, 45%)",
                "text-background-color": "hsl(45, 100%, 45%)",
            },
        },
        {
            selector: "edge.analysis-result",
            style: {
                "line-color": "hsl(45, 100%, 45%)",
                "target-arrow-color": "hsl(45, 100%, 45%)",
                "source-arrow-color": "hsl(45, 100%, 45%)",
                "text-background-color": "hsl(45, 100%, 45%)",
                "width": 4,
            },
        },
    ];
}

function _getPerformance(profile) {
    if (profile === "dense") {
        return [
            {
                selector: "*",
                style: {
                    "min-zoomed-font-size": 28,
                },
            },
            {
                selector: "edge",
                style: {
                    "curve-style": "haystack",
                    "haystack-radius": 0.35,
                    "text-opacity": 0,
                    "width": 1,
                },
            },
        ];
    }

    if (profile === "large") {
        return [
            {
                selector: "*",
                style: {
                    "min-zoomed-font-size": 18,
                },
            },
            {
                selector: "edge",
                style: {
                    "text-opacity": 0.65,
                    "width": 1.4,
                },
            },
        ];
    }

    return [];
}

const STYLES = {
    light: {
        default: _getDefault("light"),
        highlight: _getHighlight("light"),
    },
    dark: {
        default: _getDefault("dark"),
        highlight: _getHighlight("dark"),
    },
};

function getStyles(theme, customStyle, performanceProfile) {
    return [
        ...STYLES[theme]["default"],
        ...customStyle,
        ..._getPerformance(performanceProfile),
        ...STYLES[theme]["highlight"],
    ];
}

export { getStyles };
export default STYLES;
