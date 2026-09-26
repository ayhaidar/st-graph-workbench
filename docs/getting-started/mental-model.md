# How it works

## On this page

- [Four layers](#four-layers)
- [Render cycle](#render-cycle)
- [Intent versus mutation](#intent-versus-mutation)
- [Full synchronization versus commands](#full-synchronization-versus-commands)
- [Options that update live](#options-that-update-live)

## Four layers

An application passes JSON-compatible dictionaries to `graph_workbench()`.
The Python wrapper validates and normalizes the request. Streamlit Components
v2 carries the props into the light DOM, where Cytoscape.js renders and manages
the live graph. Interactions return event dictionaries to Python.

```text
database/dataframe -> Python elements -> graph_workbench -> Cytoscape.js
database/session   <- Python handler  <- GraphEvent     <- user action
```

## Render cycle

1. Load or construct `elements` in Python.
2. Validate node IDs, edge endpoints, parents, and expansion metadata.
3. Pass elements, styles, layout, actions, and a stable key to the component.
4. Let Cytoscape render and handle browser interaction.
5. Receive an event through the return value or `on_change` callback.
6. Apply approved mutations to `st.session_state` or a persistent store.
7. Rerender from the updated authoritative data.

## Intent versus mutation

`crud_actions=["create_node"]` does not silently write to a database. It emits
a `crud` event with an operation and selection context. Python can open a
dialog, validate the form, enforce access control, update storage, and issue a
graph command. The same pattern applies to expansion backed by an API or query.

Browser-local edit actions are deliberately different. They respond immediately
inside Cytoscape and emit enough information for Python to mirror the change.
Use them for responsive editing, then persist accepted changes in Python.

## Full synchronization versus commands

- `elements_sync="always"` reconciles the complete Python elements dictionary
  on each rerun. It is the default and simplest mode.
- `elements_sync="initial"` sends the initial graph once, then expects unique
  `graph_commands` to patch the live graph. Mirror mutating commands with
  `apply_graph_command()` so Python and the browser remain aligned.

Command IDs are idempotency keys. Reusing an ID prevents the browser from
applying the same command twice after a Streamlit rerun.

## Options that update live

Height and zoom-bound changes update the live component without replacing its
graph instance. This preserves selection and viewport state across ordinary
Streamlit reruns.

`height`, `selection_mode`, `events`, `min_zoom`, and `max_zoom` are reconciled
on an existing component instance. Cytoscape reads `wheel_sensitivity` during
initialization, so change the component `key` when intentionally remounting
with a different value.

## Conclusion

Choose the simplest ownership model that fits the application. Start with full
elements synchronization; adopt commands only when incremental updates provide
a meaningful responsiveness or payload-size benefit.
