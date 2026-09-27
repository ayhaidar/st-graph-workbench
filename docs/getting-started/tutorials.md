# Interactive tutorials

## On this page

- [Choose a view](#choose-a-view)
- [Learning sequence](#learning-sequence)
- [Independent checkpoints](#independent-checkpoints)
- [Code and reference](#code-and-reference)

## Choose a view

The Streamlit examples app is the interactive learning environment. MkDocs is
the manual and API reference. Start the app on an unused port such as `8502`:

```powershell
uv run streamlit run examples/app.py --server.port 8502
```

Open `http://localhost:8502/` after starting the app. **Tutorials** provides an
ordered path with focused controls. **Feature Lab** contains comprehensive
playgrounds for experimenting with individual features. Its feature finder
links directly to working examples, without repeating the documentation
directory.

## Learning sequence

### Foundations

1. **Build your first graph** (`/`): dictionaries, IDs, validation, and rendering.
2. **Change nodes and edges** (`/learn_change_records`): Python element helpers and state.
3. **Style your graph** (`/learn_style_graph`): categories, selectors, icons, and relationships.
4. **Arrange and navigate** (`/learn_layouts`): ten layouts and viewport controls.
5. **Load your own data** (`/learn_load_data`): tables, records, JSON, and validation.

### Exploration

6. **Select and use records** (`/learn_selection`): selection modes and linked tables.
7. **Find and reveal connections** (`/learn_search`): search and neighborhood visibility.
8. **Analyze relationships** (`/learn_analysis`): five algorithm scenarios with expected results.
9. **Expand progressively** (`/learn_expansion`): context menus, badges, and on-demand records.

### Application workflows

10. **Build CRUD workflows** (`/learn_crud`): dialogs and Python-owned writes.
11. **Edit in the browser** (`/learn_editing`): local changes, undo, and redo.
12. **Send graph commands** (`/learn_commands`): every operation and synchronization mode.
13. **Export and restore** (`/learn_exports`): graph/image downloads and saved positions.

### Advanced

14. **Organize and scale** (`/learn_scale`): compound parents, counts, and profiles.
15. **Load larger datasets incrementally** (`/learn_loading`): batches, overlap, retry, completion, and restart.
16. **Integrate component events** (`/learn_events`): custom events, callbacks, and independent instances.

## Independent checkpoints

Every lesson opens with deterministic source records. Earlier lessons are not
prerequisites for running a page. Python-owned working data belongs to that
lesson and survives navigation within the same session; Reset restores only
that lesson. Refreshing the browser or restarting the server can end a session.

Browser-local edits and undo history are deliberately separate: leaving their
page unmounts the component. Persist edit events or export the graph when those
changes must survive. The editing lesson demonstrates this boundary explicitly.

The vehicle/location/time dataset is an example, not a domain restriction.
Replace it with workflow, network, dependency, knowledge-graph, or other records.

## Code and reference

Each page contains source data, executed code, a working graph, annotated
dictionaries, practical results, common mistakes, and a conclusion. Complete
page source is available in an expander. Shared helpers live alongside the
pages under `examples/tutorials/` and have pure-function tests.

The existing demo routes remain unchanged. The previous live README is at
`/readme`, and legacy documentation routes remain available without cluttering
the tutorial navigation. Use the sidebar's manual and API links for the
canonical reference. The examples link to the published manual by default.
`GRAPH_WORKBENCH_DOCS_URL=http://localhost:8000` can point them to a local
documentation server while editing the two applications together.

## Conclusion

Start with a small working graph, then add the interaction your application
needs. Open **Feature Lab** at `/demo_overview` for deeper controls and use the
[API reference](../reference/index.md) for complete signatures and types.
