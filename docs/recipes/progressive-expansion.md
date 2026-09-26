# Progressive expansion

## On this page

- [Initial graph](#initial-graph)
- [Expansion registry](#expansion-registry)
- [Handle expand and collapse](#handle-expand-and-collapse)
- [Keep positions stable](#keep-positions-stable)
- [Failure handling](#failure-handling)

## Initial graph

For shared records, nested branches, pagination and reproducible views, use the
[managed expansion controller](../guides/expansion-visibility.md#managed-branches).
The lower-level recipe below retains legacy callback compatibility; fixed-ID
deletion alone is not a shared-branch ownership model.

Start with a meaningful core, such as a case and its primary vehicle. Add
`data.expansion` only when a query can return additional records. The badge's
`next_count` must describe the next request, not the current node degree.

## Expansion registry

For local examples, a dictionary can map a parent node ID to nodes and edges.
Production applications usually replace this dictionary with a service call.
Track which records were introduced by each expansion so collapse removes only
that branch.

```python
--8<-- "docs/snippets/progressive_expansion.py"
```

## Handle expand and collapse

Deduplicate the event timestamp, verify that the selected node is expandable,
retrieve related records, validate endpoint references, and then upsert. On
collapse, call `delete_elements()` with the introduced node IDs and
`remove_incident_edges=True`.

Update expansion metadata after each successful operation. Expanded metadata
should report `collapse_count`; collapsed metadata should report the next
available count. Remove metadata when no further action exists.

## Keep positions stable

Capture `positions` events and apply them to Python nodes. New nodes should be
placed near the expansion origin or added through a layout constrained to the
new neighborhood. Do not replace the entire graph or rerun an animated global
layout after every expansion.

## Failure handling

- Leave the graph unchanged if retrieval or validation fails.
- Display a Python-side error explaining the source or malformed record.
- Never issue edges before their endpoint nodes are known.
- Give every retry a new command ID only when it represents a new command.
- Do not increment badges optimistically unless rollback is implemented.

## Conclusion

Progressive expansion is reliable when the application can answer three
questions: what will be added, what belongs to this branch, and where the
existing graph should remain after the update.
