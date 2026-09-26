const COUNT_FORMATTER = new Intl.NumberFormat("en-US");

function normalizeCount(value) {
    const count = Number(value);
    if (!Number.isFinite(count) || count <= 0) {
        return 0;
    }
    return Math.floor(count);
}

function pluralize(count, word) {
    return `${COUNT_FORMATTER.format(count)} ${word}${count === 1 ? "" : "s"}`;
}

function formatExactCount(value) {
    return COUNT_FORMATTER.format(normalizeCount(value));
}

function formatCompactCount(value) {
    const count = normalizeCount(value);
    if (count < 1000) {
        return String(count);
    }

    const units = [
        { value: 1000000000, suffix: "B" },
        { value: 1000000, suffix: "M" },
        { value: 1000, suffix: "k" },
    ];
    const unit = units.find((item) => count >= item.value);
    const rawCompact = count / unit.value;
    const digits = rawCompact < 10 ? 1 : 0;
    const precision = 10 ** digits;
    const compact = Math.floor(rawCompact * precision) / precision;
    return `${compact.toFixed(digits).replace(".0", "")}${unit.suffix}`;
}

function getExpansion(data) {
    const expansion = data?.expansion;
    if (!expansion || typeof expansion !== "object") {
        return null;
    }
    return expansion;
}

function getExpansionBadge(data) {
    const expansion = getExpansion(data);
    if (!expansion) {
        return null;
    }

    const state = expansion.state === "expanded" ? "expanded" : "collapsed";
    const nextCount = normalizeCount(expansion.next_count);
    const totalCount = normalizeCount(expansion.total_count);
    const collapseCount = normalizeCount(expansion.collapse_count);

    if (state === "expanded" && collapseCount > 0) {
        return {
            count: collapseCount,
            label: `-${formatCompactCount(collapseCount)}`,
            state: "expanded",
            sign: "-",
        };
    }

    if (nextCount > 0) {
        const label =
            totalCount > nextCount
                ? `+${formatCompactCount(nextCount)}/${formatCompactCount(
                      totalCount
                  )}`
                : `+${formatCompactCount(nextCount)}`;
        return {
            count: nextCount,
            label: label,
            state: "collapsed",
            sign: "+",
            totalCount: totalCount,
        };
    }

    return null;
}

function getExpansionAction(data) {
    const expansion = getExpansion(data);
    if (!expansion) {
        return null;
    }

    const state = expansion.state === "expanded" ? "expanded" : "collapsed";
    const nextCount = normalizeCount(expansion.next_count);
    const collapseCount = normalizeCount(expansion.collapse_count);

    if (state === "expanded" && collapseCount > 0) {
        return {
            label: "Collapse node",
            state: "expanded",
        };
    }

    if (nextCount > 0) {
        return {
            label: "Expand node",
            state: "collapsed",
        };
    }

    return null;
}

function getExpansionSummary(data) {
    const expansion = getExpansion(data);
    if (!expansion) {
        return [];
    }

    const state = expansion.state === "expanded" ? "expanded" : "collapsed";
    const nextCount = normalizeCount(expansion.next_count);
    const totalCount = normalizeCount(expansion.total_count);
    const depth = normalizeCount(expansion.depth);
    const collapseCount = normalizeCount(expansion.collapse_count);
    const summary = [];

    if (state === "expanded" && collapseCount > 0) {
        summary.push(["Collapse hides", pluralize(collapseCount, "node")]);
    } else if (nextCount > 0) {
        summary.push(["Next expansion", pluralize(nextCount, "node")]);
    }

    if (totalCount > 0) {
        let total = pluralize(totalCount, "node");
        if (depth > 0) {
            total = `${total} across ${pluralize(depth, "layer")}`;
        }
        summary.push(["Total hidden", total]);
    }

    return summary;
}

export {
    formatCompactCount,
    formatExactCount,
    getExpansionAction,
    getExpansionBadge,
    getExpansionSummary,
    normalizeCount,
};
