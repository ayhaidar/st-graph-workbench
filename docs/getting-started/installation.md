# Installation

## On this page

- [Requirements](#requirements)
- [Install the package](#install-the-package)
- [Install from source](#install-from-source)
- [Install documentation tools](#install-documentation-tools)
- [Build the frontend](#build-the-frontend)
- [Verify the checkout](#verify-the-checkout)

## Requirements

- Python 3.10 or newer.
- pandas 2.2.2 or newer.
- Streamlit 1.57 or newer.
- Node.js 22.15 or newer when changing the JavaScript frontend; CI uses Node.js 24.
- A Chromium browser for Playwright tests and screenshot capture.

## Install the package

Add the library to a `uv` project:

```powershell
uv add st-graph-workbench
```

Or install it with `pip`:

```powershell
python -m pip install st-graph-workbench
```

## Install from source

From the repository root:

```powershell
python -m pip install .
```

For a development checkout managed by `uv`:

```powershell
uv sync --extra dev
```

`uv.lock` gives maintainers and CI a reproducible environment. A consuming
application does not need the lock file after installing the package.

## Install documentation tools

The MkDocs site provides a concise library overview, task-oriented guides, and
detailed API entries for every public function. Choose any unused local port;
this example uses `8000`:

```powershell
uv sync --extra docs
uv run mkdocs serve -f mkdocs.local.yml --dev-addr 127.0.0.1:8000
```

Use both extras when editing documentation screenshots or running all checks:

```powershell
uv sync --extra dev --extra docs
```

## Build the frontend

The wheel already contains the compiled frontend. Rebuild it only after editing
files under `st_graph_workbench/frontend/src`:

```powershell
cd st_graph_workbench/frontend
npm ci
npm run build
cd ../..
```

Restart Streamlit after a production build if a browser still loads an older
hashed bundle.

## Verify the checkout

```powershell
uv run ruff check .
uv run mypy st_graph_workbench/
uv run pytest --reruns 0 -q
uv run mkdocs build --strict
```

The example commands use `8502` for Streamlit and `8000` for MkDocs. You may
choose different unused ports; keeping the two services on separate ports
prevents one from replacing the other.

Automated browser checks use Chromium. Chrome and Edge share its browser
engine; Firefox and WebKit are not part of the automated compatibility gate.

## Conclusion

Continue to [Quick start](quickstart.md) and render the first graph.
