# Events, exports, and positions

## On this page

- [Custom event listeners](#custom-event-listeners)
- [Event validation](#event-validation)
- [Export formats](#export-formats)
- [Position payloads](#position-payloads)
- [Movement metadata](#movement-metadata)
- [Choosing browser or Python export](#choosing-browser-or-python-export)

## Custom event listeners

Use `Event(name, event_type, selector)` for lower-level Cytoscape interactions
not already represented by selection, CRUD, analysis, or other built-in tools:

```python
events = [
    Event("vehicle_click", "click tap", "node[label = 'VEHICLE']"),
    Event("location_double_click", "dblclick dbltap", "node[label = 'LOCATION']"),
]
```

The returned event uses the custom name as `action` and includes event type,
target ID, target group, target data, and timestamp. Changing `events` updates
listeners on the existing component without requiring a new key.

## Event validation

Names and event types must be non-empty strings. Selectors must be strings.
Custom names cannot be reserved values such as `selection`, `search`,
`analysis`, `crud`, `edit`, `viewport`, `positions`, or `export`.

## Export formats

The browser toolbar provides:

- Visible graph JSON.
- Full graph JSON, including currently hidden elements.
- Selected subgraph JSON.
- PNG image.
- JPG image.
- Node positions JSON.

JSON exports preserve graph element data. Image exports capture the current
canvas appearance and viewport; they are evidence illustrations rather than a
replacement for source records.

## Position payloads

Set `return_positions=True` to receive position events. Each record contains a
node `id` and model `position` with `x` and `y`. Apply those positions to
Python-owned nodes and render with `layout="preset"` to restore manual layouts.

```python
--8<-- "docs/snippets/persist_positions.py"
```

## Movement metadata

Position events produced by a node drag include a `movement` dictionary:

```json
{
  "operation": "connected_drag",
  "status": "applied",
  "anchor_node_id": "location-1",
  "moved_node_ids": ["location-1", "vehicle-1", "vehicle-2"],
  "connected_node_ids": ["vehicle-1", "vehicle-2"],
  "depth": 1,
  "candidate_count": 2,
  "max_nodes": 100
}
```

`moved_node_ids` includes native anchor/selected-group movement plus automatic
followers. `connected_node_ids` contains followers only. Status is `applied`,
`disabled`, `limit_exceeded`, or `layout_running`; operation is `drag` for
ordinary dragging and `connected_drag` for configured connected gestures.
Layout-generated position events remain unchanged and omit `movement`.

## Choosing browser or Python export

Use browser exports for analyst-driven snapshots. Use returned records and
`records_to_dataframe()` when the application must add metadata, enforce access
control, create a repeatable report, or write to a controlled destination.

## Conclusion

Custom events expose Cytoscape without weakening the higher-level API. Keep
event names application-specific and retain structured records beside images.
