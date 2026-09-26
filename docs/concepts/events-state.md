# Events, state, and synchronization

## On this page

- [Event envelope](#event-envelope)
- [Built-in event families](#built-in-event-families)
- [Callbacks and retained values](#callbacks-and-retained-values)
- [Session-state pattern](#session-state-pattern)
- [Synchronization choices](#synchronization-choices)

## Event envelope

Browser interactions return a JSON-compatible `GraphEvent`:

```json
{
  "action": "analysis",
  "data": {
    "analysis": "degree",
    "node_id": "ABC123",
    "degree": 4,
    "indegree": 1,
    "outdegree": 3,
    "edge_ids": ["case-vehicle", "vehicle-camera"]
  },
  "timestamp": 1780000000000
}
```

`action` routes the event, `data` contains action-specific fields, and
`timestamp` identifies the interaction that produced it.

## Built-in event families

| Action | Produced by | Typical use |
| --- | --- | --- |
| `selection` | Selecting or clearing graph elements | Build tables or contextual actions |
| `search` | Applying browser search | Inspect matched records and IDs |
| `expand` / `remove` | Node actions or context menu | Query or modify related records |
| `visibility` | Hide/restore tools | Track visible subgraphs |
| `analysis` | Analysis toolbox | Consume paths, traversals, components, or degree |
| `crud` | CRUD toolbox | Open Python-owned dialogs and persistence workflows |
| `edit` | Browser-local editing | Mirror immediate edits into Python state |
| `viewport` | Viewport tools | Save or restore pan and zoom |
| `positions` | Position export/return | Persist manual node placement |
| `export` | Export toolbar | Record export metadata |
| `load_more` | Progressive loading control | Fetch and append the next data batch |

Custom `Event` names cannot reuse reserved built-in action names.

## Callbacks and retained values

Without `on_change`, read the component's return value after Streamlit reruns.
With a callback, Streamlit stores the event under the component key before
calling the handler:

```python
def handle_graph_change() -> None:
    event = st.session_state.get("case-graph")
    if not isinstance(event, dict):
        return
    if event.get("action") == "selection":
        st.session_state.selected_ids = event["data"]["selected_node_ids"]
```

An event value can remain present on later reruns. Compare `timestamp` with the
last handled timestamp before applying a mutation so one intent is not applied
twice.

## Session-state pattern

Keep durable graph data, command queues, last handled timestamps, and dialog
state under separate keys. Initialize each key once with `setdefault`. Apply a
mutation to Python state first, then render from that state on the next run.

## Synchronization choices

Use `elements_sync="always"` for ordinary applications. Use
`elements_sync="initial"` only with a stable component key and unique graph
command IDs. Mutating commands should also pass through
`apply_graph_command()` or `apply_graph_commands()` so browser and Python state
describe the same graph.

## Conclusion

Treat events as messages, not database writes. Idempotent handlers and one
authoritative Python graph eliminate most rerun and disappearing-canvas bugs.
