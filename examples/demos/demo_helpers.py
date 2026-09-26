from __future__ import annotations

import copy
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import streamlit as st

from page_overview import PageSection, render_page_overview
from st_graph_workbench import (
    EdgeStyle,
    Elements,
    NodeStyle,
    Record,
    StyleRule,
    records_to_dataframe,
)


SIGHTING_RECORDS: list[Record] = [
    {
        "Entity": "ABC123",
        "Entity Type": "Vehicle",
        "Relationship": "Seen at",
        "Target": "Location 1",
        "Time": "2024-09-02 08:14",
        "Confidence": 0.94,
    },
    {
        "Entity": "ABC123",
        "Entity Type": "Vehicle",
        "Relationship": "Seen at",
        "Target": "Location 2",
        "Time": "2024-09-02 08:41",
        "Confidence": 0.91,
    },
    {
        "Entity": "ALPHA",
        "Entity Type": "Vehicle",
        "Relationship": "Seen at",
        "Target": "Location 1",
        "Time": "2024-09-02 08:11",
        "Confidence": 0.88,
    },
    {
        "Entity": "BETA",
        "Entity Type": "Vehicle",
        "Relationship": "Seen at",
        "Target": "Location 2",
        "Time": "2024-09-02 08:38",
        "Confidence": 0.9,
    },
    {
        "Entity": "12VEC",
        "Entity Type": "High-interest overlap",
        "Relationship": "Seen at",
        "Target": "Location 3",
        "Time": "2024-09-02 09:07",
        "Confidence": 0.86,
    },
]


RELATED_RECORDS: list[Record] = [
    {
        "Entity": "ABC123",
        "Entity Type": "Vehicle",
        "Relationship": "Registered to",
        "Target": "Person_MReed",
        "Target Type": "Person",
        "Time": "2024-09-02 07:58",
    },
    {
        "Entity": "Person_MReed",
        "Entity Type": "Person",
        "Relationship": "Uses",
        "Target": "Phone_0412",
        "Target Type": "Phone",
        "Time": "2024-09-02 08:02",
    },
    {
        "Entity": "Phone_0412",
        "Entity Type": "Phone",
        "Relationship": "Seen near",
        "Target": "Location 2",
        "Target Type": "Location",
        "Time": "2024-09-02 08:43",
    },
]


PRESET_POSITIONS: dict[str, dict[str, int]] = {
    "ABC123": {"x": 80, "y": 150},
    "ALPHA": {"x": 80, "y": 310},
    "BETA": {"x": 80, "y": 470},
    "12VEC": {"x": 80, "y": 630},
    "location_1": {"x": 340, "y": 230},
    "location_2": {"x": 340, "y": 390},
    "location_3": {"x": 340, "y": 560},
    "Person_MReed": {"x": 610, "y": 130},
    "Phone_0412": {"x": 610, "y": 330},
    "checkpoint": {"x": 610, "y": 520},
}


def normalize_location(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_")


def relationship_label(value: Any) -> str:
    return str(value).strip().title()


def build_sighting_graph(records: list[Record] | None = None) -> Elements:
    rows = copy.deepcopy(records or SIGHTING_RECORDS)
    counts = Counter(str(row["Entity"]) for row in rows)
    main_vehicle = counts.most_common(1)[0][0] if counts else ""
    node_ids: set[str] = set()
    edge_ids: set[str] = set()
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for row in rows:
        entity = str(row["Entity"])
        target = normalize_location(row["Target"])
        entity_type = str(row.get("Entity Type", "Vehicle"))
        label = "MAIN_VEHICLE" if entity == main_vehicle else entity_type.upper()

        if entity not in node_ids:
            nodes.append(
                {
                    "data": {
                        "id": entity,
                        "label": label,
                        "name": entity,
                        "type": entity_type,
                    },
                    "position": copy.deepcopy(PRESET_POSITIONS.get(entity, {})),
                }
            )
            node_ids.add(entity)

        if target not in node_ids:
            nodes.append(
                {
                    "data": {
                        "id": target,
                        "label": "PLACE",
                        "name": str(row["Target"]),
                        "type": "Location",
                    },
                    "position": copy.deepcopy(PRESET_POSITIONS.get(target, {})),
                }
            )
            node_ids.add(target)

        edge_id = f"{entity}-{target}-{str(row['Time']).replace(':', '')}"
        if edge_id not in edge_ids:
            edges.append(
                {
                    "data": {
                        "id": edge_id,
                        "label": relationship_label(row["Relationship"]),
                        "source": entity,
                        "target": target,
                        "Time": row["Time"],
                        "confidence": row.get("Confidence"),
                    }
                }
            )
            edge_ids.add(edge_id)

    return {"nodes": nodes, "edges": edges}


def demo_node_styles(*, text_size: float | None = None) -> list[NodeStyle | StyleRule]:
    styles: list[NodeStyle | StyleRule] = [
        NodeStyle("MAIN_VEHICLE", "#8BA393", "name", "directions_car", size=38),
        NodeStyle("VEHICLE", "#FF7F3E", "name", "directions_car", size=32),
        NodeStyle(
            "HIGH-INTEREST OVERLAP", "#D72638", "name", "directions_car", size=34
        ),
        NodeStyle("PLACE", "#7A5CFA", "name", "place", size=34),
        NodeStyle("PERSON", "#2A629A", "name", "person", size=32),
        NodeStyle("PHONE", "#0F766E", "name", "phone", size=30),
        NodeStyle("CHECKPOINT", "#6C757D", "name", "flag", size=30),
        NodeStyle("NODE", "#6C757D", "name", size=28),
        StyleRule(
            "node[label = 'MAIN_VEHICLE']",
            {
                "border-width": 4,
                "border-color": "#D72638",
                "shape": "ellipse" if text_size is not None else "diamond",
            },
        ),
    ]

    if text_size is not None:
        styles.extend(
            [
                NodeStyle("CAMERA", "#287D8E", "name", "videocam", size=32),
                NodeStyle("TIME", "#C46C29", "name", "schedule", size=32),
                NodeStyle("DOCUMENT", "#476C5E", "name", "description", size=32),
            ]
        )
        styles.append(
            StyleRule(
                "node",
                {
                    "font-size": text_size,
                    "min-zoomed-font-size": 0,
                    "label": "data(name)",
                },
            )
        )
    return styles


def demo_edge_styles() -> list[EdgeStyle]:
    return [
        EdgeStyle("Seen At", "#BFDBFE", "label", directed=True),
        EdgeStyle("Registered To", "#86EFAC", "label", directed=True),
        EdgeStyle("Uses", "#67E8F9", "label", directed=True),
        EdgeStyle("Seen Near", "#FDBA74", "label", directed=True, line_style="dashed"),
        EdgeStyle("Related", "#CBD5E1", "label", directed=True, line_style="dotted"),
    ]


def demo_graph() -> Elements:
    graph = build_sighting_graph(SIGHTING_RECORDS)
    extra_nodes = [
        {
            "data": {
                "id": "Person_MReed",
                "label": "PERSON",
                "name": "Maya Reed",
                "type": "Person",
            },
            "position": copy.deepcopy(PRESET_POSITIONS["Person_MReed"]),
        },
        {
            "data": {
                "id": "Phone_0412",
                "label": "PHONE",
                "name": "0412 000 111",
                "type": "Phone",
            },
            "position": copy.deepcopy(PRESET_POSITIONS["Phone_0412"]),
        },
    ]
    extra_edges = [
        {
            "data": {
                "id": "ABC123-Person_MReed",
                "label": "Registered To",
                "source": "ABC123",
                "target": "Person_MReed",
            }
        },
        {
            "data": {
                "id": "Person_MReed-Phone_0412",
                "label": "Uses",
                "source": "Person_MReed",
                "target": "Phone_0412",
            }
        },
        {
            "data": {
                "id": "Phone_0412-location_2",
                "label": "Seen Near",
                "source": "Phone_0412",
                "target": "location_2",
            }
        },
    ]
    return {
        "nodes": [*graph["nodes"], *extra_nodes],
        "edges": [*graph["edges"], *extra_edges],
    }


def graph_summary_rows(elements: Elements) -> list[Record]:
    return [
        {"metric": "Nodes", "value": len(elements.get("nodes", []))},
        {"metric": "Edges", "value": len(elements.get("edges", []))},
        {
            "metric": "Node labels",
            "value": len(
                {
                    node.get("data", {}).get("label")
                    for node in elements.get("nodes", [])
                }
            ),
        },
        {
            "metric": "Edge labels",
            "value": len(
                {
                    edge.get("data", {}).get("label")
                    for edge in elements.get("edges", [])
                }
            ),
        },
    ]


def capability_rows() -> list[Record]:
    return [
        {
            "capability": "Managed branch exploration",
            "API surface": "ExpansionController, ExpansionProvider, InMemoryExpansionProvider, expansion",
            "demo": "Branch Exploration",
            "what to try": "Explore both locations, collapse one branch, retain shared records, compare analysis scopes, and restore a snapshot.",
        },
        {
            "capability": "Render Cytoscape graphs",
            "API surface": "graph_workbench(elements, layout, height, key)",
            "demo": "Graph Workbench Showcase",
            "what to try": "Render one graph with selection, search, analysis, export, and state.",
        },
        {
            "capability": "Node styling",
            "API surface": "NodeStyle",
            "demo": "Node Styles",
            "what to try": "Change icon, caption, shape, size, border, opacity, and label position.",
        },
        {
            "capability": "Edge styling",
            "API surface": "EdgeStyle",
            "demo": "Edge Styles",
            "what to try": "Change arrows, line style, curve style, width, opacity, and captions.",
        },
        {
            "capability": "Advanced Cytoscape styles",
            "API surface": "StyleRule",
            "demo": "Node Styles, Edge Styles, Compound And Performance",
            "what to try": "Apply selector rules for high-priority or parent nodes.",
        },
        {
            "capability": "Layouts",
            "API surface": "layout string or layout dictionary",
            "demo": "Layout Algorithms",
            "what to try": "Compare preset, cose, fcose, dagre, cola, grid, and circle layouts.",
        },
        {
            "capability": "Selection modes",
            "API surface": "selection_mode: SelectionMode, return_selection, show_selection_details",
            "demo": "Investigation Tools",
            "what to try": "Use single, multiple, and box selection; hide details without clearing the returned records.",
        },
        {
            "capability": "Search",
            "API surface": "search=True",
            "demo": "Investigation Tools",
            "what to try": "Search by text, label, property, or selector without hiding context.",
        },
        {
            "capability": "Node actions and visibility",
            "API surface": "node_actions: list[NodeAction]",
            "demo": "Node Actions, Investigation Tools",
            "what to try": "Expand, remove, show neighbors, hide unselected, and restore hidden.",
        },
        {
            "capability": "Analysis tools",
            "API surface": "analysis_actions: list[AnalysisAction]",
            "demo": "Investigation Tools",
            "what to try": "Run shortest path, BFS, DFS, connected components, and degree.",
        },
        {
            "capability": "CRUD intents",
            "API surface": "crud_actions: list[CrudAction]",
            "demo": "Interactive CRUD / Data Loading",
            "what to try": "Create, read, update, delete, and request related graph data.",
        },
        {
            "capability": "Incremental browser updates",
            "API surface": "graph_commands, elements_sync: ElementsSync",
            "demo": "Data Helpers And Commands, Interactive CRUD / Data Loading",
            "what to try": "Send add, upsert, update, delete, set, clear, viewport, and layout commands.",
        },
        {
            "capability": "Browser editing",
            "API surface": "edit_actions: list[EditAction]",
            "demo": "Editing And Viewport Tools",
            "what to try": "Add browser nodes, connect selected nodes, delete, lock, snap, undo, and redo.",
        },
        {
            "capability": "Viewport controls",
            "API surface": "viewport_actions: list[ViewportAction], min_zoom, max_zoom, wheel_sensitivity",
            "demo": "Editing And Viewport Tools",
            "what to try": "Save, restore, reset, and constrain pan/zoom behavior.",
        },
        {
            "capability": "Compound nodes",
            "API surface": "node.data.parent",
            "demo": "Compound And Performance",
            "what to try": "Group entities under parent case nodes.",
        },
        {
            "capability": "Performance profiles",
            "API surface": "performance_profile: PerformanceProfile",
            "demo": "Compound And Performance",
            "what to try": "Compare default, large, and dense rendering profiles.",
        },
        {
            "capability": "Progressive loading",
            "API surface": "progressive_loading: ProgressiveLoadConfig",
            "demo": "Progressive Loading",
            "what to try": "Request cursor-aware batches and append them with idempotent graph commands.",
        },
        {
            "capability": "Dataframe and record conversion",
            "API surface": "dataframe_to_records, records_to_dataframe",
            "demo": "Data Helpers And Commands",
            "what to try": "Round-trip table records into graph elements and back to a dataframe.",
        },
        {
            "capability": "Typed data contracts",
            "API surface": "Element, ElementId, ElementIdInput, Elements, Record, Layout, GraphCommand, GraphEvent",
            "demo": "Graph Data Format, Data Helpers And Commands, Investigation Tools",
            "what to try": "Annotate graph inputs, commands, layouts, records, and returned browser events.",
        },
        {
            "capability": "Python element helpers",
            "API surface": "get_element, upsert_elements, update_element_data, delete_elements",
            "demo": "Data Helpers And Commands",
            "what to try": "Mutate Python-owned graph dictionaries before rendering.",
        },
        {
            "capability": "Validation",
            "API surface": "validate_elements, validate_graph_commands",
            "demo": "Data Helpers And Commands, Components V2 Validation",
            "what to try": "Catch broken IDs, bad parents, and invalid command payloads in Python.",
        },
        {
            "capability": "Custom event listeners",
            "API surface": "Event",
            "demo": "Event Listeners",
            "what to try": "Listen for raw Cytoscape click, tap, and double-click events.",
        },
        {
            "capability": "Components v2 multi-instance behavior",
            "API surface": "stable key, Components v2 runtime",
            "demo": "Components V2 Validation",
            "what to try": "Run two independent graph instances on the same page without iframes.",
        },
    ]


def render_capability_summary(
    title: str,
    rows: Sequence[Mapping[str, Any]],
    *,
    description: str = "A quick contents-style guide to the APIs used here.",
) -> None:
    st.markdown(f"#### {title}")
    with st.container(border=True):
        if description:
            st.caption(description)
        for row in rows:
            capability = str(row.get("capability", "Capability"))
            api_surface = str(row.get("API surface", ""))
            detail = str(row.get("what to try") or row.get("demo") or "")
            line = f"- **{capability}**"
            if api_surface:
                line += f"  \n  `{api_surface}`"
            if detail:
                line += f"  \n  {detail}"
            st.markdown(line)


def render_demo_intro(
    title: str,
    summary: str,
    capabilities: list[tuple[str, str]],
    sections: Sequence[PageSection] | None = None,
) -> None:
    st.markdown(f"# {title}")
    st.markdown(summary)
    render_page_overview(
        sections
        or [
            (
                "Capability coverage",
                "The public API features this demo is designed to explain.",
            ),
            (
                "Setup and controls",
                "The inputs, presets, or records used before the graph renders.",
            ),
            (
                "Interactive graph",
                "The live `st-graph-workbench` output and the controls to try.",
            ),
            (
                "Returned dictionaries",
                "The component payloads, graph records, or helper outputs returned to Python.",
            ),
            (
                "Reader checks",
                "Short checks that confirm the behavior is working as intended.",
            ),
        ],
        description=(
            "This demo overview gives readers the page structure before the "
            "graph or output tables appear."
        ),
    )
    render_capability_summary(
        "Capability coverage",
        [
            {
                "capability": feature,
                "API surface": "",
                "what to try": detail,
            }
            for feature, detail in capabilities
        ],
        description="The main features demonstrated on this page.",
    )


def render_elements_dataframe(elements: Elements, title: str) -> None:
    st.markdown(f"#### {title}")
    st.dataframe(records_to_dataframe(elements), hide_index=True)


def _dictionary_key_summary(payload: Any) -> str:
    if isinstance(payload, Mapping):
        keys = [str(key) for key in payload.keys()]
        if not keys:
            return "Top-level keys: none"
        return "Top-level keys: " + ", ".join(f"`{key}`" for key in keys[:8])
    if isinstance(payload, Sequence) and not isinstance(payload, str):
        return f"List length: {len(payload)} item(s)"
    return f"Payload type: `{type(payload).__name__}`"


def _json_preview_payload(payload: Any) -> Any:
    if payload is None:
        return {
            "status": "waiting_for_event",
            "note": "Interact with the graph above to populate this returned dictionary.",
        }
    if isinstance(payload, str):
        return {"value": payload}
    if isinstance(payload, Mapping):
        candidate = dict(payload)
    elif isinstance(payload, Sequence):
        candidate = list(payload)
    else:
        candidate = {"value": repr(payload)}

    try:
        json.dumps(candidate)
    except (TypeError, ValueError):
        return {"value": repr(payload)}
    return candidate


def render_dictionary_preview(
    title: str,
    payload: Any,
    description: str,
    *,
    height: int = 320,
    expanded: bool = True,
) -> None:
    st.markdown(f"#### {title}")
    with st.container(border=True):
        description_column, dictionary_column = st.columns(
            [0.38, 0.62],
            vertical_alignment="top",
        )
        with description_column:
            st.markdown("**Dictionary description**")
            st.markdown(description)
            st.caption(_dictionary_key_summary(payload))
        with dictionary_column:
            with st.container(height=height):
                st.json(_json_preview_payload(payload), expanded=expanded)


@st.cache_data
def read_source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def render_source_expander(path: str) -> None:
    with st.expander("Source", expanded=False, icon=":material/code:"):
        st.code(read_source(path), language="python")
