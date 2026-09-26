"""One deterministic connected dataset shared by the lesson and Feature Lab."""

from st_graph_workbench import InMemoryExpansionProvider


def expansion_source():
    records = [
        ("ABC123", "VEHICLE", "ABC123", 350, 120),
        ("location-1", "PLACE", "Location 1", 150, 270),
        ("location-2", "PLACE", "Location 2", 550, 270),
        ("camera-1", "CAMERA", "Camera 1", 40, 450),
        ("camera-2", "CAMERA", "Camera 2", 760, 450),
        ("shared", "DOCUMENT", "Shared report", 360, 460),
        ("time-0814", "TIME", "08:14", 180, 450),
        ("AB123", "VEHICLE", "AB123", 560, 490),
        ("sighting-1", "DOCUMENT", "Sighting 118", 40, 650),
        ("time-0840", "TIME", "08:40", 210, 650),
        ("location-3", "PLACE", "Location 3", 570, 670),
        ("document-2", "DOCUMENT", "Report attachment", 370, 690),
    ]
    links = [
        ("ABC123", "location-1", "SEEN_AT"),
        ("ABC123", "location-2", "SEEN_AT"),
        ("location-1", "camera-1", "HAS_CAMERA"),
        ("location-1", "shared", "RECORDED_IN"),
        ("location-2", "shared", "RECORDED_IN"),
        ("location-2", "camera-2", "HAS_CAMERA"),
        ("location-1", "time-0814", "OBSERVED_AT"),
        ("location-2", "AB123", "OBSERVED_VEHICLE"),
        ("camera-1", "sighting-1", "CAPTURED"),
        ("sighting-1", "camera-1", "VERIFIED_BY"),
        ("camera-1", "time-0840", "OBSERVED_AT"),
        ("shared", "document-2", "ATTACHMENT"),
        ("AB123", "location-3", "SEEN_AT"),
    ]
    return {
        "nodes": [
            {
                "data": {"id": key, "label": label, "name": name},
                "position": {"x": x, "y": y},
            }
            for key, label, name, x, y in records
        ],
        "edges": [
            {
                "data": {
                    "id": f"relation-{i}",
                    "source": a,
                    "target": b,
                    "label": label,
                    "observed_at": f"2026-01-01T{8 + i % 3:02}:14:00Z",
                }
            }
            for i, (a, b, label) in enumerate(links)
        ],
    }


def expansion_start():
    return {"nodes": expansion_source()["nodes"][:1], "edges": []}


class ExampleExpansionProvider(InMemoryExpansionProvider):
    """Local loader plus an example of application-owned source analysis."""

    def analyze(self, request):
        if request["analysis"] != "degree":
            raise NotImplementedError(
                "This example provider supports source degree only. Use Displayed graph or Loaded records for other algorithms."
            )
        node_id = request["node_ids"][0]
        edges = [
            e["data"]
            for e in self._elements["edges"]
            if node_id in {e["data"]["source"], e["data"]["target"]}
        ]
        return {
            "analysis": "degree",
            "node_id": node_id,
            "degree": len(edges),
            "indegree": sum(e["target"] == node_id for e in edges),
            "outdegree": sum(e["source"] == node_id for e in edges),
            "edge_ids": [e["id"] for e in edges],
            "node_count": len(self._elements["nodes"]),
            "edge_count": len(self._elements["edges"]),
            "complete": True,
        }
