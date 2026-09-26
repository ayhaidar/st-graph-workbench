"""Prepare repository-relative README images for the PyPI description."""

from pathlib import Path
from typing import Any

from hatchling.metadata.plugin.interface import MetadataHookInterface


RAW_REPOSITORY_URL = (
    "https://raw.githubusercontent.com/ayhaidar/st-graph-workbench/main/"
)


def prepare_pypi_readme(readme: str) -> str:
    """Make repository-relative image paths absolute for package indexes."""
    return readme.replace('src="images/', f'src="{RAW_REPOSITORY_URL}images/').replace(
        "](docs/assets/screenshots/",
        f"]({RAW_REPOSITORY_URL}docs/assets/screenshots/",
    )


class CustomMetadataHook(MetadataHookInterface):
    """Supply one README source with PyPI-safe image URLs."""

    def update(self, metadata: dict[str, Any]) -> None:
        readme = Path(self.root, "README.md").read_text(encoding="utf-8")
        metadata["readme"] = {
            "content-type": "text/markdown",
            "text": prepare_pypi_readme(readme),
        }
