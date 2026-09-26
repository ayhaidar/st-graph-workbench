# Graph commands

## On this page

- [When to use commands](#when-to-use-commands)
- [Mutation commands](#mutation-commands)
- [Viewport commands](#viewport-commands)
- [Validation and application](#validation-and-application)
- [Synchronization pattern](#synchronization-pattern)

## When to use commands

Commands patch an existing browser graph without resending every element. Use
them for progressive loading, CRUD, streaming updates, or large graphs. For
small graphs, full `elements_sync="always"` reconciliation is simpler.

Each command has a non-empty scalar `command_id` and an `operation`. The browser
applies a command ID once, which makes Streamlit reruns idempotent.

## Mutation commands

| Builder | Operation | Behavior |
| --- | --- | --- |
| `add_elements_command` | `add_elements` | Adds only IDs not already present |
| `upsert_elements_command` | `upsert_elements` | Adds or updates by `data.id` |
| `update_data_command` | `update_data` | Merges or replaces one element's data |
| `delete_elements_command` | `delete_elements` | Removes selected IDs and optional incident edges |
| `set_elements_command` | `set_elements` | Replaces the full live graph |
| `clear_graph_command` | `clear` | Removes every live node and edge |

“Browser command” means a JSON dictionary sent as a component prop and applied
to the already mounted Cytoscape instance. It is not a shell command, network
request, or JavaScript string.

## Viewport commands

`viewport_command()` accepts `fit`, `center`, `pan`, `zoom`, `set_viewport`,
`set_zoom_bounds`, and `run_layout`.

```python
fit = viewport_command("fit-case", "fit", padding=60, duration=180)
zoom = viewport_command(
    "zoom-camera",
    "zoom",
    level=1.8,
    renderedPosition={"x": 480, "y": 260},
    duration=180,
)
```

Durations and padding are finite non-negative numbers. Pan dictionaries and
zoom anchors require finite numeric `x` and `y`. Zoom bounds follow the same
rules as component options.

## Validation and application

`validate_graph_commands(commands, elements=...)` checks command shape,
operations, IDs, endpoint references, update identity, delete safety, layout
names, and viewport values.

`apply_graph_command()` and `apply_graph_commands()` return new Python elements
dictionaries after applying mutation commands. Viewport commands leave Python
elements unchanged.

## Synchronization pattern

```python
--8<-- "docs/snippets/command_driven.py"
```

Always update Python state and the browser from the same command. Clear or
replace the one-item command queue when a later action occurs, and never reuse
a command ID for different content.

## Conclusion

Commands optimize transport and preserve the live viewport. They do not remove
the need for authoritative Python state or graph validation.
