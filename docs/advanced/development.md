# Development and packaging

## On this page

- [Environment](#environment)
- [Frontend workflow](#frontend-workflow)
- [Documentation workflow](#documentation-workflow)
- [Quality checks](#quality-checks)
- [Package contents](#package-contents)
- [Release verification](#release-verification)

## Environment

```powershell
uv sync --extra dev --extra docs
uv run playwright install chromium
```

The Python package requires Python 3.10, pandas 2.2.2, and Streamlit 1.57 or
newer. Frontend development requires Node.js 22.15 or newer; CI uses Node.js
24. Installing the Python library does not require Node.js.

## Frontend workflow

```powershell
cd st_graph_workbench/frontend
npm ci
npm run format
npm run lint
npm run build
```

The production build updates tracked files under `frontend/build`. Restart the
Streamlit process after rebuilding when validating the new hash.

## Documentation workflow

```powershell
# Live documentation on http://localhost:8000
uv run mkdocs serve -f mkdocs.local.yml --dev-addr 127.0.0.1:8000

# Interactive examples on http://localhost:8502
uv run streamlit run examples/app.py --server.port 8502

# Refresh committed documentation screenshots
uv run python scripts/capture_docs_screenshots.py --base-url http://localhost:8502

# Refresh only the README/homepage workflow gallery
uv run python scripts/capture_docs_screenshots.py --gallery --base-url http://localhost:8502
```

Use `--output-dir` to capture into a temporary review folder. Documentation
pages use executable snippets from `docs/snippets` and the root changelog is
included directly, avoiding manually synchronized copies.

The gallery is captured from real tutorial interactions, with fixed framing and
assertions on the resulting graph records. It does not fabricate interface
screens. Use `--gallery --check` for a temporary capture without replacing the
reviewed images. Omitting `--base-url` starts and cleans up a temporary examples
server on a free port.

## Quality checks

```powershell
uv run ruff format --check .
uv run ruff check .
uv run mypy st_graph_workbench/
uv run pytest --reruns 0 -q
uv run mkdocs build --strict
uv build
```

Frontend checks are separate because they use npm. Browser tests start the
examples app on a free port and exercise the rendered Components v2 surface.
CI installs both locked extras because the full suite also builds MkDocs.
Automatic test retries are disabled locally and in CI.
CI validates pull requests, pushes to `main`, and version tags. A fast core
Python matrix covers 3.10 through 3.14, while the complete Chromium suite runs
once on Python 3.12. A separate job verifies the declared minimum pandas and
Streamlit versions.
The automated browser gate uses Chromium. Firefox/WebKit compatibility and a
complete keyboard/screen-reader accessibility review require separate sign-off;
a passing Chromium run does not establish those results.

Audit the actual environment as well as the frontend's production dependencies:

```powershell
uvx pip-audit --path .venv/Lib/site-packages
cd st_graph_workbench/frontend
npm audit --omit=dev
```

The Python path above is for Windows; on other systems use the environment's
`site-packages` directory. A scanner skip for a local checkout is not a security
assessment of its code.
Review dependency findings and refresh only the affected locked packages before
rerunning the regression checks.

## Package contents

The wheel contains the Python package, component manifest, compiled JavaScript,
component markup/CSS, async chunks, and supported SVG icons. It excludes tests,
examples, documentation sources, and frontend source.
It also includes `py.typed`, the project's Apache 2.0 `LICENSE` and `NOTICE`,
upstream license files, and
`frontend/build/THIRD_PARTY_LICENSES.txt`. The production build generates the
latter from the installed, locked production npm packages and fails when their
license texts are missing or their installed versions do not match the lockfile.

The source distribution contains the README, changelog, MkDocs sources,
screenshots, examples, tests, screenshot tool, frontend source, and production
build. It excludes `node_modules`, debug pages, caches, and generated `site/`.

## Release verification

After the quality checks and frontend build, verify fresh distribution artifacts:

```powershell
uv run python scripts/verify_release.py
```

This creates an isolated environment outside the checkout, checks distribution
metadata with Twine, checks installed typing with MyPy, and renders a browser
smoke app using the installed wheel. It uses a free temporary port and cleans
up its server. It does not upload artifacts or change Git history. The script
requires `uv`, network access to install dependencies, and the Playwright
Chromium browser installed by the development workflow.

The release gate also verifies the [Apache 2.0 license and attribution](../license.md),
retained third-party notices, reviewed dependency audit results, passing tests without retries, and
a version/changelog review. A 600-record interaction test is a regression
scenario, not a guarantee about every larger dataset's performance. The manual
Progressive Loading Scale Test probes larger browser checkpoints without
turning machine-specific timings into CI requirements.

## Conclusion

Build and test both language boundaries. A Python-only pass cannot detect stale
bundles or pointer behavior, and a frontend-only pass cannot validate graph
contracts or package contents.
