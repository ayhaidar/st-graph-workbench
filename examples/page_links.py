"""Reference links shared by navigation and lessons."""

import os
from pathlib import PurePosixPath


DEFAULT_DOCS_URL = "https://ayhaidar.github.io/st-graph-workbench"


def docs_url(path=""):
    base = os.environ.get("GRAPH_WORKBENCH_DOCS_URL", DEFAULT_DOCS_URL).rstrip("/")
    if not path:
        return f"{base}/"
    destination = PurePosixPath(path).with_suffix("")
    if destination.name == "index":
        destination = destination.parent
    relative = destination.as_posix().strip("/")
    return f"{base}/" if relative == "." else f"{base}/{relative}/"
