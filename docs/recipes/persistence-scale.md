# Persisted layouts and scale

## On this page

- [Persist positions](#persist-positions)
- [Restore a layout](#restore-a-layout)
- [Command-driven updates](#command-driven-updates)
- [Large and dense graphs](#large-and-dense-graphs)
- [Operational checks](#operational-checks)

## Persist positions

Enable `return_positions=True`, deduplicate position events, and store model
coordinates by stable node ID. Persist positions separately from business data
when the layout is user-specific.

```python
--8<-- "docs/snippets/persist_positions.py"
```

## Restore a layout

Attach each saved position to its node and use
`layout={"name": "preset", "fit": True, "padding": 40}`. Missing positions are
valid during gradual migration, but a complete saved layout produces the most
predictable result.

## Command-driven updates

```python
--8<-- "docs/snippets/command_driven.py"
```

`elements_sync="initial"` preserves the live Cytoscape viewport while commands
add, update, or remove small batches. Mirror mutation commands in Python so a
future remount starts from the same graph.

For a user-triggered cursor workflow, pass `ProgressiveLoadConfig` through the
`progressive_loading` argument. The complete callback and event dictionary are
shown in the [progressive loading guide](../guides/progressive-loading.md).

## Large and dense graphs

Choose `large` when element count and layout cost dominate. Choose `dense` when
edge count and visual clutter dominate. Combine profiles with progressive
expansion, labels that disappear at low zoom, non-animated updates, and focused
subgraph workflows.

## Operational checks

Measure node/edge totals, layout duration, command size, expansion latency,
browser memory, and drag/search responsiveness. Test repeated expansion,
collapse, selection, deselection, and viewport restoration rather than only the
initial render.

## Conclusion

Persisted positions protect analytical context. Incremental commands protect
responsiveness. Both depend on stable IDs and synchronized Python state.
