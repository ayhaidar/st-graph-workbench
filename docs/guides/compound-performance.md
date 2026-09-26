# Compound graphs and performance

## On this page

- [Compound nodes](#compound-nodes)
- [Performance profiles](#performance-profiles)
- [Scaling choices](#scaling-choices)
- [Validation at scale](#validation-at-scale)
- [What to measure](#what-to-measure)

## Compound nodes

Compound graphs group child nodes inside a parent using `data.parent`. They are
useful for cases, organizations, journeys, incidents, or source systems.

```python
nodes = [
    {"data": {"id": "case-42", "label": "CASE", "name": "Case 42"}},
    {
        "data": {
            "id": "ABC123",
            "label": "VEHICLE",
            "name": "ABC123",
            "parent": "case-42",
        }
    },
]
```

Use a `StyleRule("node:parent", ...)` for the container. `fcose`, `cola`, and
selected force layouts are usually more suitable than `preset` when compound
positions are not already available.

## Performance profiles

- `default`: labels, animation, and interaction tuned for ordinary graphs.
- `large`: reduced animation and bounded history for higher element counts.
- `dense`: stronger edge simplification, labels hidden at low zoom, reduced
  history, and renderer hints for dense connectivity.

Profiles adjust frontend defaults; explicit layout/style choices can still
override relevant properties.

## Scaling choices

Use the first-class `progressive_loading` control for ordered query pages and
progressive expansion to avoid loading irrelevant neighborhoods. Prefer
`elements_sync="initial"` and incremental commands when full graph payloads
become expensive. Avoid running a full animated layout after each small update.
Limit browser edit history and hide edge labels at low zoom on dense graphs.

`ExpansionController` reuses a record index for displayed projections and badge
previews. Updating the cache invalidates that index; collapse keeps it reusable.
This avoids rescanning every loaded record for each displayed node. The loaded
graph still contributes to transfer size and headless analysis memory, so keep
both loaded and displayed counts visible in performance measurements.

## Validation at scale

Validate incoming batches before issuing commands, including references against
the currently known graph. Keep IDs indexed in the data layer. Reject malformed
records before they reach Cytoscape so a single broken edge cannot blank or
destabilize the graph.

## What to measure

- Initial render and layout duration.
- Element counts and average/maximum degree.
- Command payload size and update latency.
- Browser memory during expansion and undo history.
- Interaction responsiveness at low and high zoom.
- Whether labels and edges remain interpretable for the analytical task.

The expansion regression fixtures cover 100, 1,000, and 10,000 loaded nodes with
bounded display sizes. They record elapsed time, badge-description time, and
peak Python memory as JUnit properties without machine-dependent timing limits:

```powershell
uv run pytest tests/test_expansion.py -k increasing --reruns=0 --junitxml=.tmp/scale-results.xml -o junit_family=xunit1
```

## Conclusion

Profiles are a starting point, not a substitute for controlling graph scope.
Progressive loading and deliberate visual density usually matter more than a
single rendering flag.
