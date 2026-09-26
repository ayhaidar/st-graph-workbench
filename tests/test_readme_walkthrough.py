from pathlib import Path
import re
import runpy

import pytest
import streamlit as st

import st_graph_workbench as workbench


ROOT = Path(__file__).resolve().parents[1]
SNIPPETS = ROOT / "docs/snippets"
EXAMPLES = (
    "readme_graph.py",
    "readme_style.py",
    "readme_records.py",
    "readme_selection.py",
)


def test_readme_code_matches_executable_snippets_and_mkdocs():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    home = (ROOT / "docs/index.md").read_text(encoding="utf-8")
    blocks = re.findall(
        r"<!-- example: ([a-z_]+\.py) -->\n```python\n(.*?)\n```",
        readme,
        re.DOTALL,
    )
    assert tuple(name for name, _ in blocks) == EXAMPLES
    for filename, code in blocks:
        assert code + "\n" == (SNIPPETS / filename).read_text(encoding="utf-8")
        assert f'--8<-- "docs/snippets/{filename}"' in home
        assert readme.count(f"<!-- live-output: {filename} -->") == 1


def test_readme_and_mkdocs_share_the_capability_summary():
    def capabilities(path):
        source = path.read_text(encoding="utf-8")
        section = source.split("## What the library provides\n", 1)[1]
        section = section.split("\n## ", 1)[0]
        return [line for line in section.splitlines() if line.startswith("- ")]

    assert capabilities(ROOT / "README.md") == capabilities(ROOT / "docs/index.md")
    assert len(capabilities(ROOT / "README.md")) == 13


def test_readme_embeds_all_five_workflow_screenshots():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    screenshots = re.findall(
        r"!\[([^\]]+)\]\(docs/assets/screenshots/(workflow-[a-z-]+\.png)\)",
        readme,
    )
    expected = {
        "workflow-analysis.png",
        "workflow-search.png",
        "workflow-expansion-open.png",
        "workflow-expansion-collapsed.png",
        "workflow-crud.png",
    }
    assert len(screenshots) == len(expected)
    assert {filename for _, filename in screenshots} == expected
    for alt, filename in screenshots:
        assert alt.strip()
        assert (ROOT / "docs/assets/screenshots" / filename).is_file()
    assert "### Publish the documentation on GitHub Pages" not in readme
    assert "manual-only" not in readme


def test_introductions_describe_a_general_purpose_library():
    introductions = []
    for path in (ROOT / "README.md", ROOT / "docs/index.md"):
        text = path.read_text(encoding="utf-8")
        intro = text.split("## On this page", 1)[0]
        assert "general-purpose graph component for Streamlit" in intro
        assert not re.search(r"\b(analyst|vehicle|sighting|intelligence)\b", intro)
        purpose = intro.split("## Why st-graph-workbench\n", 1)[1].strip()
        introductions.append(purpose)
    assert introductions[0] == introductions[1]


@pytest.mark.parametrize(
    "action,ids,expected",
    [
        (None, [], 0),
        ("selection", ["ABC123"], 2),
        ("selection", ["camera-7"], 0),
        ("selection", [], 0),
        ("search", ["ABC123"], 0),
    ],
)
def test_readme_walkthrough_uses_real_records(monkeypatch, action, ids, expected):
    calls = []
    output = []
    event = (
        None
        if action is None
        else {
            "action": action,
            "data": {"selected_node_ids": ids, "selected_elements": []},
        }
    )

    def render(elements, **kwargs):
        workbench.validate_elements(elements)
        calls.append((elements, kwargs))
        return event

    monkeypatch.setattr(workbench, "graph_workbench", render)
    monkeypatch.setattr(st, "dataframe", lambda frame, **kwargs: output.append(frame))
    monkeypatch.setattr(st, "metric", lambda label, value: None)
    scope = {}
    for filename in EXAMPLES:
        scope.update(runpy.run_path(str(SNIPPETS / filename), init_globals=scope))

    assert len(calls) == 2
    assert calls[0][0] == calls[1][0]
    assert calls[0][1]["key"] != calls[1][1]["key"]
    assert calls[1][1]["node_styles"][0].icon == "directions_car"
    assert len(scope["sightings_df"]) == 3
    assert len(scope["records"]) == 3
    assert scope["sightings_df"]["record_group"].unique().tolist() == ["sightings"]
    assert [node["data"]["id"] for node in scope["vehicle_nodes"]] == [
        "ABC123",
        "12VEC",
    ]
    workbench.validate_elements({"nodes": scope["vehicle_nodes"], "edges": []})
    assert len(output[-1]) == expected
    if expected:
        assert output[-1]["time"].tolist() == ["08:14", "08:41"]
