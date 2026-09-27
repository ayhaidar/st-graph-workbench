# Interactive Examples

Start the app from the repository root:

```powershell
uv sync --extra dev
uv run streamlit run examples/app.py --server.port 8502
```

Choose an unused port if `8502` is occupied. Open <http://localhost:8502>.

## Tutorials

The first screen is a working graph. Sixteen independent lessons progress
through building, changing, styling, arranging, loading, selecting, searching,
analyzing, expanding, CRUD, browser editing, commands, exports, scale,
progressive loading, and custom events.

Each lesson shows source data before the graph, the code that runs, and useful
results with dictionary field descriptions. Lessons have their own checkpoint
and Reset button; completing an earlier page is never required.

Vehicle, location, and time records are sample data. The same techniques apply
to any application with connected records.

All datasets and records used by this examples app are synthetically generated.
They do not describe real people, vehicles, locations, organizations, claims,
or incidents.

## Feature Lab And Reference

Use the sidebar selector to open the comprehensive playgrounds and icon browser.
Existing demo URLs still work. The full README walkthrough is at `/readme`;
other legacy documentation routes remain accessible but are not duplicated in
the main navigation.

[MkDocs](https://ayhaidar.github.io/st-graph-workbench/) contains the manual
and API reference, and the
[learning path](../docs/getting-started/tutorials.md) describes the sequence.
Serve MkDocs separately on an unused port such as `8000`. Sidebar links default
to the published manual; set `GRAPH_WORKBENCH_DOCS_URL=http://localhost:8000`
when developing both applications locally.

## Development

`app.py` registers all routes. `page_catalog.py` owns lesson ordering, links,
and coverage destinations. `tutorials/` contains executable pages and shared
checkpoint/workflow helpers; `demos/` retains the full playgrounds.

Branding uses `images/logo.png` for the banner and `images/logo_icon.png` for
the sidebar and browser icon.

Run `uv run pytest --reruns=0 -q` from the repository root. Tests start their
own Streamlit service on a temporary port and stop it afterwards.
