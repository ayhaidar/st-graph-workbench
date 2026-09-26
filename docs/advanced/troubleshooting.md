# Troubleshooting

## On this page

- [Port conflicts](#port-conflicts)
- [Stale or missing frontend bundle](#stale-or-missing-frontend-bundle)
- [Blank graph after a mutation](#blank-graph-after-a-mutation)
- [Progressive loading stalls](#progressive-loading-stalls)
- [Expansion fails over HTTP](#expansion-fails-over-http)
- [Selection prevents panning](#selection-prevents-panning)
- [Search focuses the wrong area](#search-focuses-the-wrong-area)
- [Expansion badges are incorrect](#expansion-badges-are-incorrect)
- [Layout errors](#layout-errors)
- [BidiComponent errors](#bidicomponent-errors)

## Port conflicts

Run MkDocs and Streamlit on separate, unused ports. The documentation examples
use `8000` for MkDocs and `8502` for Streamlit, but neither value is required.
Before restarting a service, identify which process owns the chosen port.

```powershell
Get-NetTCPConnection -LocalPort 8000,8502 -State Listen
```

Leave an unrelated process running and choose another documentation port when
needed, for example:

```powershell
uv run mkdocs serve -f mkdocs.local.yml --dev-addr 127.0.0.1:8765
```

## Stale or missing frontend bundle

Symptoms include old controls, a missing component, or an error pointing to an
older hashed `index-*.js`. Run `npm run build` in the frontend directory,
confirm only one entry bundle exists under `frontend/build`, stop Streamlit, and
start it again.

## Blank graph after a mutation

Validate the resulting Python elements and the command batch. Common causes are
an edge whose source or target does not exist, deleting a node without incident
edges, replacing state with an event dictionary, or allowing browser and Python
graphs to diverge under `elements_sync="initial"`.

Use the same command with `apply_graph_command()` before sending it to the
browser. Keep one authoritative `st.session_state` graph.

## Progressive loading stalls

If a handled fetch fails without advancing the cursor, echo its `request_id`
as `progressive_loading["acknowledged_request_id"]` in the callback's `finally`
block. A normal rerun alone does not complete a pending request. Set
`has_more=False` after an empty final page.

If the progress counter advances but nodes do not appear after a reset, check
for reused command IDs. Command sequences must survive data resets for a stable
component key. If nodes exist but overlap at the origin, supply positions or
explicitly request a layout. See the
[progressive loading guide](../guides/progressive-loading.md#failures-and-retries).

## Expansion fails over HTTP

Older frontend builds can raise `crypto.randomUUID is not a function` when
expanding through a network hostname or IP address over HTTP, even though the
same app works on localhost. The current build uses `crypto.getRandomValues`
for both managed-expansion and progressive-loading request IDs, which also works
on those HTTP origins. Update the package, restart Streamlit, and reload the
browser; source checkouts must rebuild the frontend first.

Request IDs are opaque correlation strings: compare them for deduplication and
acknowledgment, but do not depend on a UUID format. Do not disable browser
security to work around an old bundle.

## Selection prevents panning

In `selection_mode="box"`, choose **Pan** before dragging blank canvas to move
the graph. Choose **Box select** only for rectangular selection. Clear selected
elements by toggling a node, clicking blank canvas, or using **Selection > Clear**.
The details-panel **X** also clears selection, leaving the visibility preference
unchanged. To hide details without deselecting, uncheck **Show selection details**
in Selection. Recheck it to display the current selection again.

## Search focuses the wrong area

Search should collect the matching elements and fit that collection, not the
whole graph. Confirm the mode and query, then inspect the returned `search`
dictionary's matched IDs. Invalid Cytoscape selectors should produce feedback
instead of a viewport change.

## Expansion badges are incorrect

Badges come from `node.data.expansion`, not current degree. Remove metadata from
terminal nodes. Recalculate `next_count`, `collapse_count`, and `total_count`
after each successful expansion or collapse.

## Layout errors

Both layout strings and dictionaries are validated. A dictionary must include a
supported `name`. `preset` is valid but requires node positions for meaningful
placement. Supported names are `preset`, `cose`, `fcose`, `dagre`, `cola`,
`grid`, `circle`, `concentric`, `breadthfirst`, and `random`.

## BidiComponent errors

First rebuild the frontend and restart Streamlit. Then verify the installed
Streamlit version is at least 1.57 and that component markup, CSS, entry bundle,
and async chunks come from the same build. A stack trace ending inside a hashed
bundle often indicates mixed or stale assets rather than invalid graph data.

If the component loads but later fails, reproduce with the smallest validated
elements dictionary and one option family at a time.

## Conclusion

Diagnose from the boundary inward: service and asset health, Python validation,
synchronization mode, event/command payload, then browser interaction.
