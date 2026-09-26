# Frontend architecture

## On this page

- [Component registration](#component-registration)
- [Mount and update lifecycle](#mount-and-update-lifecycle)
- [Feature modules](#feature-modules)
- [State and payload flow](#state-and-payload-flow)
- [Managed exploration](#managed-exploration)
- [Layout and resize guards](#layout-and-resize-guards)
- [Bundle structure](#bundle-structure)

## Component registration

The Python wrapper registers `st_graph_workbench.graph_workbench` through
Streamlit Components v2. It supplies component HTML, scoped CSS, and one hashed
JavaScript entry bundle. The component mounts in the light DOM, which allows
reliable pointer handling for Cytoscape box selection.

Each public key is encoded losslessly into a Streamlit-safe internal key.
Per-instance state prevents selection, viewport, custom listeners, and command
history from leaking between multiple graphs.

## Mount and update lifecycle

1. Python validates options, elements, styles, layouts, events, and commands.
2. Components v2 passes normalized props into the frontend render function.
3. The frontend creates one Cytoscape instance or reuses the existing instance.
4. Full elements are reconciled or unseen command IDs are applied.
5. Styles, layouts, tool groups, selection modes, and viewport bounds update.
6. Browser interactions produce normalized JSON event dictionaries.
7. Cleanup disconnects resize/listener resources and destroys the Cytoscape
   instance when the component unmounts.

## Feature modules

The frontend is divided by user behavior rather than by screen: graph creation,
selection, box interaction, search, analysis, CRUD intents, graph commands,
progressive loading, bounded connected dragging,
node actions, edit tools, viewport tools, exports, styles, layouts, expansion
badges, information panels, and payload construction. See the
[capability matrix](../reference/capability-matrix.md) for the complete map.

## State and payload flow

Browser state tracks the current selection, active style/theme, layout, last
expansion, and expansion-badge visibility. Modules subscribe only to the state
they need. `setImmediateStreamlitValue` is used for interactions that must
return immediately; Components v2 state supports persistent component values.

Payload helpers normalize selected and connected records, search matches, CRUD
context, edit details, viewport values, and positions before Python sees them.

## Managed exploration

`ExpansionController` is independent of Streamlit. The provider owns the source;
the controller owns validated cached records and projects a displayed graph.
Branches identify an anchor plus normalized filters and record their node/edge
contributions. Visibility is computed from the starting graph, protected records,
and reachable open branches. It is not recursive deletion of graph neighbors:
shared records survive other active branches, while disconnected cycles cannot
keep themselves alive. Nested open flags can be suspended without being forgotten.

`expansionControls.js` supplies opt-in branch actions, filters, scope controls,
and one-batch-at-a-time continuation. Requests persist through Components v2
reruns until Python returns their receipt IDs. Provider responses additionally
must match the request, source version, and branch revision. A receipt does not
mean that an application-owned asynchronous provider has completed its work.

Managed graph commands remain queued until the browser acknowledges applying
them. The controller emits only actual differences; unchanged selection or
analysis events do not start a graph-update feedback loop. Commands preserve
positions and viewport, and the current Python view remains the recovery
checkpoint if the browser needs to synchronize again.

Loaded-record analysis uses a separate headless Cytoscape instance; the displayed
renderer highlights only available result IDs. Source analysis stays with a
capable provider. See the [expansion API](../reference/expansion.md) for snapshots,
cache invalidation, and the [branch guide](../guides/expansion-visibility.md) for
the complete executable workflow.

## Layout and resize guards

Async layout extensions can finish out of order. A request token ensures only
the newest layout callback changes readiness or viewport state. A
`ResizeObserver` calls `cy.resize()` after container changes, and height updates
do not require remounting.

## Bundle structure

Webpack produces one hashed entry bundle plus asynchronously loaded layout and
connected-drag chunks, copied component markup/CSS, and packaged SVG icons.
Cytoscape Automove and its controller load only when `connected_drag` is
configured, so the default graph path does not download that feature. The entry and asset
budget is `512000` bytes. Wheels contain runtime build assets, while source
distributions also contain frontend source and developer configuration.

## Conclusion

The architecture keeps Streamlit reruns, component updates, and Cytoscape's
long-lived browser state explicit. New capabilities should expose a typed Python
surface, a focused frontend module, a normalized event shape, and tests at both
boundaries.
