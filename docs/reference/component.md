# Component API

## On this page

- [Main component](#main-component)
- [Action values](#action-values)
- [Update behavior](#update-behavior)
- [Progressive loading](#progressive-loading)
- [Connected dragging](#connected-dragging)
- [Adaptive toolbar](#adaptive-toolbar)

## Main component

::: st_graph_workbench.component.component.graph_workbench

## Action values

| Type | Accepted values |
| --- | --- |
| `NodeAction` | `remove`, `expand`, `show_neighbors`, `show_incoming`, `show_outgoing`, `hide_unselected`, `restore_hidden` |
| `CrudAction` | `create_node`, `create_edge`, `read_selected`, `update_selected`, `delete_selected`, `request_node_data` |
| `EditAction` | `add_node`, `connect_selected`, `delete_selected`, `lock_selected`, `unlock_selected`, `make_ungrabbable`, `make_grabbable`, `snap_to_grid`, `undo`, `redo` |
| `ViewportAction` | `toggle_zoom`, `toggle_pan`, `save_viewport`, `restore_viewport`, `reset_viewport` |
| `AnalysisAction` | `shortest_path`, `bfs`, `dfs`, `connected_components`, `degree` |
| `SelectionMode` | `single`, `multiple`, `box` |
| `PerformanceProfile` | `default`, `large`, `dense` |
| `ElementsSync` | `always`, `initial` |

## Progressive loading

Pass a validated `ProgressiveLoadConfig` to `progressive_loading` to show the
in-canvas Load more control. It emits `action == "load_more"`; Python fetches
the next page and returns it through `graph_commands`. See the
[progressive loading guide](../guides/progressive-loading.md) for every field
and a runnable callback.

Loading events include a unique `data.request_id`. The optional
`acknowledged_request_id` configuration field acknowledges a handled success
or failure without requiring changed counts or a new component key.

## Connected dragging

Pass `ConnectedDragConfig` to `connected_drag` to expose an opt-in Selection
toolbar preference. `enabled` and `depth` define the initial browser choice;
`max_depth` limits the available one-to-three-hop options; `max_nodes` places a
positive bound on automatic followers. `depth` cannot exceed `max_depth`.

Omitting the argument hides the controls and preserves existing drag behavior.
See [selection and search](../guides/selection-search.md#move-connected-nodes)
for interaction semantics and [events and exports](../guides/events-exports.md#movement-metadata)
for returned position metadata.

## Adaptive toolbar

Pass `ToolbarConfig` to `toolbar` to choose `adaptive`, `expanded`, `compact`,
or initially `minimized` presentation. `collapsible` exposes the reader's
minimize/restore button. `sticky=True` reserves the measured top toolbar height
instead of allowing controls to cover the graph canvas. Toolbar presentation is
browser-local and emits no graph event.

See [rendering and layouts](../guides/rendering-layouts.md#adaptive-toolbar) for
configuration examples and responsive behavior.

## Update behavior

Height, selection mode, custom events, and zoom bounds update on a live instance.
`show_selection_details` defaults to `True` and is a user-adjustable display
preference. Repeating its value preserves the Selection menu checkbox across
reruns; changing it overrides the checkbox without remounting. The checkbox
hides the panel without deselecting; the panel's X clears selection without
changing the checkbox. A new key or browser reload resets the
preference to the supplied value. See [selection and search](../guides/selection-search.md#optional-selection-details).
Connected-drag toolbar choices follow the same stable-key rule: unchanged Python
defaults preserve browser choices, while changed defaults override them without
remounting.
Toolbar minimize and compact-search choices are also isolated by stable key;
an explicitly changed Python toolbar configuration resets them.
Wheel sensitivity is read during Cytoscape initialization. Stable keys preserve
the intended component instance across reruns.
