# Contributing

Thank you for helping improve `st-graph-workbench`. Contributions should keep
the Python API, Streamlit examples, browser component, and documentation in
agreement.

## Set up the checkout

```powershell
uv sync --extra dev --extra docs
uv run playwright install chromium
cd st_graph_workbench/frontend
npm ci
cd ../..
```

Node.js is needed only when changing or rebuilding the frontend. The compiled
component is already included for ordinary Python development.

## Make a focused change

- Follow the existing public API and typing patterns.
- Add or update tests for changed behavior.
- Update the relevant tutorial and MkDocs guide for user-visible behavior.
- Use synthetic records in examples, tests, screenshots, and bug reports.
- Rebuild `st_graph_workbench/frontend/build` after frontend source changes.
- Preserve third-party attribution when adapting external code or assets.

## Run the checks

```powershell
uv run ruff format --check .
uv run ruff check .
uv run mypy st_graph_workbench/
uv run pytest --reruns=0 -q
uv run mkdocs build --strict
uv run python scripts/verify_release.py
```

For frontend changes, also run:

```powershell
cd st_graph_workbench/frontend
npm run format
npm run lint
npm run build
npm audit
```

## Submit the change

Describe the behavior, verification performed, and any compatibility impact.
Do not include credentials, private datasets, personal records, or generated
environment files. Contributions are accepted under the project's Apache
License 2.0.
