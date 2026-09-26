# Changelog

All notable changes to `st-graph-workbench` will be documented in this file.

This changelog covers the standalone `st-graph-workbench` package beginning
with version `0.1.0`.

## [Unreleased]

No unreleased changes.

## [0.1.0] - 2026-09-26

### Added

- An adaptive top toolbar with expanded, compact, and minimized presentations,
  accessible search/minimize controls, stable-key preferences, and measured
  canvas space that prevents wrapped controls from covering graph records.
  Compact menus stay inside narrow pages, while an initial clipped graph is
  fitted once after layout without changing later user viewport choices.
- `ToolbarConfig` for application-controlled mode, collapse availability, top
  placement, and reserved-space behavior, with corresponding examples and
  browser coverage.

- Opt-in connected-record dragging with one-to-three-hop visible scopes,
  per-instance toolbar preferences, rigid selected-safe movement, bounded
  refusal, lazy Cytoscape Automove loading, and returned movement metadata.
- Connected-drag workflows in the selection tutorial, Investigation Tools,
  Progressive Loading, and the browser scale activity, including checkpointed
  positions and oversized-neighborhood guidance.

- A Progressive Loading Scale Test activity with deterministic 100-to-10,000
  record checkpoints and a repeatable Chromium capacity benchmark.
- User-facing Load more guidance covering bounded pages, Python-owned providers,
  incremental commands, cursor handling, and when to switch to filtering or expansion.

- Shortest-path experiments in Progressive Loading, with one/two-node selection,
  checkpoint-labelled relationship tables, and CSV export.
- Explicit Clear Selection and the details panel's X now also remove analysis
  highlights on nodes and edges, without changing search matches or saved results.

- Beginner-oriented progressive-loading guidance, single-root BFS experiments,
  optional paginated cross-location sightings, and snapshot-labelled visit tables
  with hop distances and CSV export in the Progressive Loading demo.

- Real tutorial screenshots in the README and MkDocs, including path analysis,
  search, independent branch collapse, and a populated Python-owned CRUD dialog.
- A reproducible workflow-gallery capture mode and project URL configuration
  for reviewed documentation assets.

- Learning objectives and review prompts for all sixteen tutorials, with more
  executing code, preserved teaching comments, and source-backed callback examples.

- CRUD tutorial type choices, styled browser drafts, side-by-side Python/edit
  reports, and practical scenarios explaining approval-first versus edit-first workflows.

- User-adjustable selection details through `show_selection_details` and the
  Selection menu checkbox, with independent per-graph rerun preferences.
- Readable 16px search inputs/dropdowns, 14px feedback, and responsive wrapping.
- Selection-details visibility is controlled by the toolbar checkbox; the
  panel's X retains its clear-selection behavior without changing that preference.

- Opt-in, Python-owned expansion with shared-record retention, nested restoration,
  paginated providers, bounded bulk operations, scoped search/analysis and snapshots.
- Persistent request delivery and browser command acknowledgments for managed
  exploration, plus reliable delivery of existing progressive-loading requests.
- Separate node/edge change badges, consistent degree scope, and preserved source
  records, cached edits, positions and viewport during collapse.
- A shared multi-location tutorial, Feature Lab and generated expansion API reference.

- A sixteen-lesson, tutorial-first examples app with independent checkpoints,
  visible source data, executable code, explained results, and local resets.
- A separate Feature Lab navigation view and searchable feature finder, with
  existing demonstration URLs and the live README walkthrough preserved.
- Curriculum coverage checks and browser tests for navigation, lesson state,
  selections, commands, expansion, CRUD, exports, and progressive loading.

- Apache License 2.0 for original project work, project attribution, and license
  metadata in both Python and frontend packages; upstream notices are retained.
- Contributor and private vulnerability-reporting guidance for public repository
  users.
- Loading request IDs and optional completion acknowledgments for retrying
  handled fetch failures without remounting or advancing the data cursor.
- Packaged typing markers, upstream license texts, generated production
  dependency notices, and isolated installed-wheel release verification.

- Cursor-aware progressive loading through `ProgressiveLoadConfig`, an
  in-canvas Load more control, and structured `load_more` event dictionaries.
- A Progressive Loading demo that grows a 600-record mobility graph through
  idempotent browser commands without replacing the current viewport.
- Graph-aware CRUD endpoint selectors, custom node/edge property fields, and
  duplicate-ID and endpoint validation in the interactive demo.
- Added a locally served Material for MkDocs site with task-oriented
  guides, intelligence-analysis recipes, generated API reference, a complete
  frontend capability matrix, screenshot automation, and strict CI builds.

- Public `Element`, `Elements`, `Record`, `Layout`, `GraphCommand`, and
  `GraphEvent` type aliases for annotated Python integrations.
- Public `ElementId` and `ElementIdInput` aliases now match the scalar and
  iterable identifier forms accepted by Python graph helpers.
- Selection and search element records can now be passed directly to
  `records_to_dataframe(...)` for a flattened pandas view.
- The Data Helpers And Commands demo now loads, validates, and previews the
  packaged intelligence graph JSON file.
- Box selection now includes an explicit Pan/Box select canvas-mode control,
  allowing users to navigate dense graphs without leaving box selection mode.
- Streamlit examples app branding with the repository logo and page-level
  Material Symbols icons.
- Front-page and demo-overview library badges for Cytoscape.js, Streamlit,
  Python, Components v2, and Material Symbols.
- README banner logo and source distribution packaging for `images/logo.png`
  and the Streamlit app icon asset.
- README guidance for running the local examples app on port 8502 and for the
  single-bundle Components v2 build invariant.
- An `examples/data/intelligence_case.json` sample with vehicles, places,
  times, people, and device links.
- Source distributions now include the examples app, tests, documentation
  assets, and frontend source needed for local review.
- Wheels keep only the Python package and built component runtime assets,
  excluding frontend source and npm metadata to reduce install size.

### Changed

- Shared expansion record/filter validation and reused indexed graph projections
  reduce repeated loaded-cache scans when preparing branch badges.

- Aligned the README, MkDocs home, and interactive overview around shared
  capability summaries and executable graph, styling, dataframe, and selection
  examples. The overview now renders the documented data and filtered evidence.
- CI installs locked development and documentation dependencies together, and
  the test suite no longer automatically retries failures.
- Updated the transitive production Lodash dependency to 4.18.1.
- Updated vulnerable frontend development dependencies, including the copy
  plugin and dev server. Frontend development now requires Node.js 22.15 or
  newer, with Node.js 24 in CI; Python installations do not need Node.js.
- README images use tracked relative paths in editors and on GitHub, while the
  distribution metadata converts those paths to public URLs for PyPI.
- Repository ignore rules now cover common Python, browser-test, coverage,
  editor, secret, and temporary outputs without hiding packaged frontend
  bundles, reviewed screenshots, or dependency lockfiles.
- The supported pandas floor is 2.2.2, avoiding the pandas 1.x and NumPy 2.x
  binary incompatibility while preserving Python 3.10 support.
- Documentation dependencies explicitly remain on MkDocs 1.x, and CI verifies
  minimum dependencies plus Python 3.10 through 3.14.
- Public documentation identifies local Streamlit routes without linking a
  published reader directly to `localhost`.
- CI validates pull requests, `main` pushes, and version tags, with immutable
  action revisions and one complete Chromium regression run.

- High-risk showcase nodes retain their semantic icon shape and use a red
  border instead of being forced into a diamond.
- The project introduction now positions the component as a general graph and
  knowledge-graph workbench for data science and application development.
- The Demo Overview now maps common dataframe, selection, related-data,
  browser-editing, and large-graph tasks to their recommended API patterns.
- `Event(...)` now validates required text fields and rejects names reserved by
  built-in component actions.
- Demo pages now share the same source-code expander helper instead of
  repeating per-page file readers.
- Graph Workbench Showcase now uses a vehicle, location, and time intelligence
  case instead of company and wallet records.
- Interactive CRUD / Data Loading now uses vehicle, location, time, person, and
  device records, with a state-version guard for clean hot reloads.
- Components V2 Validation now uses the same vehicle/person intelligence
  vocabulary while preserving the multi-instance icon asset check.
- Investigation Tools now uses vehicle, person, time-window, camera, phone,
  tower, and location records across search, selection, analysis, and export
  examples.
- Editing And Viewport Tools now uses vehicle, time-window, person, and device
  records, with a state-version guard for clean hot reloads.
- Graph Data Format and Compound And Performance now use the same
  intelligence-data vocabulary as the rest of the reader-facing examples.
- The old unreferenced company fixture was replaced with the intelligence-case
  sample dataset.
- Demo capability summaries now render as contents-style lists instead of front
  matter tables.
- Front-page library badges now render as a titled `Library stack` section so
  screenshots clearly label the Cytoscape.js, Streamlit, Python, Components v2,
  and Material Symbols stack.
- Dictionary preview blocks now show an explanatory waiting payload before any
  component event exists.
- README live outputs now use the same described, scrollable dictionary preview
  pattern as the demo pages.
- The Editing And Viewport Tools demo now makes custom mouse-wheel sensitivity
  opt-in so the default page load uses Cytoscape's native wheel behavior.
- Root package exports now include the action and mode typing aliases for
  node actions, CRUD actions, editing, viewport controls, analysis,
  selection, performance profiles, and element sync modes.
- The JavaScript-to-Streamlit capability map now includes selection controls
  and utility modules for layouts, expansion summaries, state, and context.
- Test coverage now checks that the JavaScript capability map mentions every
  current frontend source module.
- Test coverage now checks that the README Public API block lists every root
  package export.
- Browser tests now share Cytoscape/Playwright helper functions for component
  lookup, readiness, selection, toolbox menus, node IDs, edge IDs, badges, and
  positions.
- Runtime validation choices for graph options and graph command operations now
  derive from the same `Literal` aliases used for public type hints.
- Deprecated compatibility arguments now share one internal warning category.

### Fixed

- The progressive-loading button keeps a compact plus icon at all viewport
  widths instead of inheriting percentage sizing from icon-only toolbar buttons.

- The Data Helpers And Commands demo now reserves its command-status slot so
  feedback does not remount the graph during slow reruns, including circle layout.

- Managed expansion now generates request IDs on non-localhost HTTP origins,
  using the same secure-random helper as progressive loading. Right-click and
  dialog actions no longer fail when `crypto.randomUUID` is unavailable.

- Updated the locked GitPython dependency from 3.1.52 to the 3.1.59 security release.
- Selected-record details have a bounded, readable scrolling area, responsive
  width, and a close control separated from the node icon.
- Expansion snapshots preserve edited starting relationships and compound context
  after CRUD; source-search reveal rejects deleted or rewired paths.
- Request receipts survive partial callback failures and long in-flight queues;
  hidden/filtered anchors invalidate pending responses before they can reappear.
- Explicit branch collapse, null-property filters, time ranges and provider limits
  now enforce their documented scope and validation rules.

- Progressive-loading resets no longer reuse browser command IDs or report
  batches that the browser silently ignored.
- Handled failed fetches can release the Load more button without changing
  progress, and stale acknowledgments cannot complete a newer request.
- The empty-start loading snippet positions its nodes and fits its first page
  instead of stacking every node at the origin.

- Scalar numeric and boolean IDs now work consistently in lookup, update,
  delete, validation, and browser-command helpers; invalid object and
  non-finite numeric IDs fail with one shared error contract.
- Expansion counts now reject `NaN` and infinite values before they can become
  misleading browser badges.
- The selected-element details panel now has a direct clear-selection button,
  so an expanded overlay cannot trap a selected node underneath it.
- Named `preset` layouts and layout command strings now follow the same
  validated Python-to-Cytoscape path as layout option dictionaries.
- Initial info-panel and node-action state now starts collapsed before the
  first browser selection update.
- Position return events no longer let the initial layout overwrite manually
  dragged node coordinates.
- Node expansion from right-click and double-click/tap interactions is more
  reliable across browser reruns and Cytoscape event variants.
- User-command events such as CRUD, remove, search, analysis, viewport, and
  visibility actions now run without delayed click handlers, suppress
  follow-up selection/position emissions, and use monotonic event timestamps
  so Streamlit dialogs and notices are not dropped during fast interactions.
- Selection-menu visibility actions now respect the `node_actions` API:
  `hide_unselected` and `restore_hidden` are hidden and guarded unless the
  Python call enables those actions.
- Graph command validation now tracks node additions, deletions, clears, and
  full graph replacements across an ordered command list, so a valid batch can
  add a node and then add an edge to that node in the same rerun.
- Node-action remove and neighbor filters now read the live Cytoscape
  selection when clicked, avoiding stale cached selection during fast
  select-and-act workflows.
- Interactive CRUD / Data Loading now relies on CRUD payloads for selected
  records instead of emitting separate selection events, reducing dialog-open
  races during fast select-and-click workflows.
- The examples app now resolves pages, README/changelog content, debug pages,
  and icon assets from the app file location, so it can run from either the
  repository root or the `examples` directory.
- Browser tests now launch Streamlit through the active Python interpreter
  instead of whichever `streamlit` executable appears first on `PATH`.
- Package metadata now requires Streamlit 1.57 or newer, matching the
  Components v2 `isolate_styles` API used by the component wrapper.
- The component explicitly mounts with `isolate_styles=False` because
  Cytoscape box selection needs light-DOM pointer handling; the generic
  container CSS selector is now scoped to `.st-graph-workbench.container`.
- The frontend now marks the graph canvas ready only after Cytoscape listeners
  and active layouts are initialized, avoiding early click/tap races during
  first render and expansion animation.
- The frontend development HTML template no longer contains the invalid
  `id="infopanel" ,` attribute typo.
- Public documentation now consistently refers to bundled node-icon assets as
  Material Symbols-style assets instead of the older Material Icons wording.

### Initial foundation (2026-07-27)

#### Added

- Initial `st-graph-workbench` package structure.
- Public Python API through `graph_workbench(...)`.
- Streamlit Components v2 frontend integration.
- Cytoscape.js graph rendering with bundled frontend assets.
- Python graph validation with friendly errors for malformed nodes, edges,
  duplicate IDs, invalid edge references, invalid compound parents, and
  malformed expansion metadata.
- Python styling helpers:
  - `NodeStyle`
  - `EdgeStyle`
  - `StyleRule`
- Layout support for the bundled Cytoscape layouts.
- Unified graph toolbox with node actions, view controls, graph controls,
  display controls, selection tools, analysis tools, export tools, and CRUD
  intent actions.
- Expand/collapse action support with expansion-count badges.
- Selection modes and structured selection return payloads.
- Search and filter panel for graph investigation workflows.
- Non-destructive search behavior that highlights and selects every match,
  fits the viewport toward those matches, and keeps graph context visible.
- Neighborhood exploration actions for incoming, outgoing, and connected nodes.
- Frontend graph analysis actions for shortest path, BFS, DFS, connected
  components, and degree.
- Export and position-return support for saving graph state.
- Compound-node validation and performance profiles for larger graph scenarios.
- Graph-count overlay for shown, hidden, and total nodes and edges.
- CRUD/data-loading event contract and Python helper functions:
  - `get_element`
  - `upsert_elements`
  - `update_element_data`
  - `delete_elements`
- Incremental graph command helpers and browser command application:
  - `add_elements_command`
  - `upsert_elements_command`
  - `update_data_command`
  - `delete_elements_command`
  - `set_elements_command`
  - `clear_graph_command`
  - `viewport_command`
  - `apply_graph_command`
  - `apply_graph_commands`
- Browser-local edit tools for add node, connect selected, delete selected,
  lock/unlock, grabbable/ungrabbable, snap to grid, undo, and redo.
- Viewport controls and commands for zoom/pan toggles, saved views, reset view,
  pan, zoom, viewport restore, zoom bounds, fit, center, and rerun layout.
- Example pages for:
  - Graph Workbench Showcase
  - Interactive CRUD / Data Loading
  - Editing And Viewport Tools
  - Investigation Tools
  - Node Actions
  - Compound And Performance
  - Components V2 Validation
  - Node Styles
  - Edge Styles
  - Layout Algorithms
  - Events Listeners
- Standalone documentation sequence covering first graph, styling, selection/search,
  expand/collapse, CRUD/data loading, analysis/export, compound/large graphs,
  editing/viewport controls, and large graph behavior.
- Learning-focused documentation pages for graph data format, styling,
  frontend architecture, and CRUD/data loading.
- `uv`-based development workflow and lockfile.

#### Changed

- Package metadata uses the new distribution name `st-graph-workbench`.
- Python import package is `st_graph_workbench`.
- Main public function is `graph_workbench(...)`.

#### Notes

- This is the first changelog entry for the new package history.
