import ast
from pathlib import Path

from st_graph_workbench.component.icons import SUPPORTED_ICONS


def test_supported_icons_match_source_svg_assets():
    icons_dir = (
        Path(__file__).resolve().parents[1]
        / "st_graph_workbench"
        / "frontend"
        / "src"
        / "assets"
        / "icons"
    )
    asset_names = {path.stem for path in icons_dir.glob("*.svg")}
    supported_names = set(SUPPORTED_ICONS)

    assert len(SUPPORTED_ICONS) == len(supported_names)
    assert supported_names == asset_names


def test_example_node_style_icons_are_bundled():
    root = Path(__file__).resolve().parents[1]
    supported_names = set(SUPPORTED_ICONS)
    missing: list[str] = []

    for path in (root / "examples").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if getattr(node.func, "id", "") != "NodeStyle":
                continue

            icon = None
            if len(node.args) >= 4 and isinstance(node.args[3], ast.Constant):
                icon = node.args[3].value
            for keyword in node.keywords:
                if keyword.arg == "icon" and isinstance(keyword.value, ast.Constant):
                    icon = keyword.value.value

            if isinstance(icon, str) and icon not in supported_names:
                missing.append(f"{path}:{node.lineno}:{icon}")

    assert missing == []
