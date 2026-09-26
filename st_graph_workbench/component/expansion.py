"""Reversible, application-owned exploration of connected records.

The controller owns a loaded cache and a view, never a database connection.
Providers execute outside the controller so applications retain authorization,
timeouts and scheduling. A response can safely arrive after its branch closes.
"""

from __future__ import annotations

from collections import defaultdict, deque
from copy import copy, deepcopy
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
from typing import Any, Literal, Protocol
from uuid import uuid4

from ._expansion_contract import (
    normalize_elements as _validate_loaded,
    normalize_query as _query,
    positive_limit,
)
from ._ids import normalize_id, normalize_id_list
from .commands import delete_elements_command, upsert_elements_command
from .elements import delete_elements, upsert_elements
from .types import Element, ElementId, Elements, GraphCommand, GraphEvent


ExpansionOperation = Literal[
    "expand",
    "load_more",
    "collapse",
    "collapse_all",
    "expand_all",
    "protect",
    "unprotect",
    "cancel",
    "retry",
    "reveal",
    "search",
    "analyze",
    "continue",
]
"""Explicit operations emitted by opt-in expansion controls."""


@dataclass(frozen=True)
class ExpansionConfig:
    """Finite exploration limits; bulk limits count additional displayed records."""

    page_size: int = 50
    max_depth: int = 3
    max_nodes: int = 500
    max_edges: int = 2000

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            positive_limit(value, name)


@dataclass(frozen=True)
class ExpansionRequest:
    """One versioned, repeatable provider query, with an opaque JSON cursor."""

    request_id: str
    branch_id: str
    node_id: str
    query: dict[str, Any]
    cursor: Any
    limit: int
    source_id: str
    source_version: str
    revision: int


@dataclass(frozen=True)
class ExpansionResponse:
    """One complete batch; edges may reference records in the loaded cache.

    Totals count distinct nodes and edges separately, not domain rows. ``None``
    means unknown. A continuing response must advance its cursor.
    """

    request_id: str
    elements: Elements
    has_more: bool = False
    cursor: Any = None
    total_nodes: int | None = None
    total_edges: int | None = None


class ExpansionProvider(Protocol):
    """Application-owned loader. Optional ``search``/``analyze`` stay explicit.

    Implement ``expand(request)`` to return a batch or raise an actionable error.
    Optional ``preview(request)`` returns the same batch without I/O, enabling
    exact next-change counts. It must not fetch from a remote service on render.
    """

    def expand(self, request: ExpansionRequest) -> ExpansionResponse:
        """Retrieve one authorized batch without modifying controller state."""
        ...


@dataclass
class _Branch:
    node_id: str
    query: dict[str, Any]
    revision: int = 0
    opened: bool = False
    fetched: bool = False
    node_ids: set[str] = field(default_factory=set)
    edge_ids: set[str] = field(default_factory=set)
    cursor: Any = None
    has_more: bool = True
    total_nodes: int | None = None
    total_edges: int | None = None
    pending: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class _RecordIndex:
    elements: Elements
    nodes: dict[str, Element]
    edges: dict[str, Element]
    order: dict[str, int]


class ExpansionController:
    """Maintain reversible graph views, independent of a Streamlit runtime.

    Initialize with the starting graph. Store one controller per application
    session/component. Call ``request`` then the provider, then ``apply_response``;
    or use ``expand`` for a synchronous batch. ``view`` is safe to render and
    ``loaded`` includes collapsed records. Neither returns mutable internal data.
    """

    def __init__(
        self,
        elements: Elements,
        *,
        source_id: str = "graph",
        source_version: str = "1",
        config: ExpansionConfig | None = None,
    ) -> None:
        elements = _validate_loaded(elements)
        self.source_id = str(source_id)
        self._instance_id = uuid4().hex
        self.source_version = str(source_version)
        self.limits = config or ExpansionConfig()
        self._base = deepcopy(elements)
        self._cache = deepcopy(elements)
        self._record_index: _RecordIndex | None = None
        self._branches: dict[str, _Branch] = {}
        self._requests: dict[str, ExpansionRequest] = {}
        self._protected: set[str] = set()
        self._hidden: set[str] = set()
        self._filtered: set[str] = set()
        self._deleted: set[str] = set()
        self._handled: set[str] = set()
        self._last_view = deepcopy(elements)
        self.changes: list[dict[str, Any]] = []
        self.revision = 0
        self.viewport: dict[str, Any] = {}
        self.bulk: dict[str, Any] | None = None
        self.search_result: dict[str, Any] | None = None
        self.analysis_result: dict[str, Any] | None = None
        self.last_error: str | None = None

    def branch_id(self, node_id: ElementId, query: dict[str, Any] | None = None) -> str:
        """Return a stable identity for a starting node and normalized filters."""
        payload = [normalize_id(node_id, option_name="node_id"), _query(query)]
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[
            :24
        ]

    def _branch(
        self, node_id: ElementId, query: dict[str, Any] | None = None
    ) -> tuple[str, _Branch]:
        node_id = normalize_id(node_id, option_name="node_id")
        key = self.branch_id(node_id, query)
        if key not in self._branches:
            self._branches[key] = _Branch(node_id, _query(query))
        return key, self._branches[key]

    def _projection(
        self, closed: set[str] | None = None
    ) -> tuple[Elements, dict[str, set[str]]]:
        records = self._index()
        nodes, edges = records.nodes, records.edges
        anchors = self._anchors()
        visible = anchors & nodes.keys()
        edge_ids = anchors & edges.keys()
        support: dict[str, set[str]] = defaultdict(set)
        by_node: dict[str, list[tuple[str, _Branch]]] = defaultdict(list)
        for key, branch in self._branches.items():
            if branch.opened and key not in (closed or set()):
                by_node[branch.node_id].append((key, branch))
        pending = deque(sorted(visible))
        processed: set[str] = set()
        # Traverse exploration contributions from anchors, not arbitrary graph edges.
        while pending:
            node_id = pending.popleft()
            if node_id in processed or node_id not in nodes:
                continue
            processed.add(node_id)
            parent = nodes[node_id]["data"].get("parent")
            if parent is not None and str(parent) not in visible:
                visible.add(str(parent))
                pending.append(str(parent))
            for key, branch in by_node[node_id]:
                for record_id in branch.node_ids | branch.edge_ids:
                    support[record_id].add(key)
                additions = branch.node_ids - visible
                visible.update(additions)
                pending.extend(sorted(additions))
                edge_ids.update(branch.edge_ids)
        blocked = self._hidden | self._filtered | self._deleted
        visible = (visible & nodes.keys()) - blocked
        # A compound child cannot render without its containing parent.
        changed = True
        while changed:
            removed = {
                i
                for i in visible
                if nodes[i]["data"].get("parent") is not None
                and str(nodes[i]["data"]["parent"]) not in visible
            }
            changed = bool(removed)
            visible -= removed
        return {
            "nodes": [
                nodes[key] for key in sorted(visible, key=records.order.__getitem__)
            ],
            "edges": [
                edges[key]
                for key in sorted(
                    (edge_ids & edges.keys()) - blocked, key=records.order.__getitem__
                )
                if str(edges[key]["data"]["source"]) in visible
                and str(edges[key]["data"]["target"]) in visible
            ],
        }, support

    def view(self) -> Elements:
        """Return the displayed graph, excluding collapsed, hidden and filtered data."""
        return deepcopy(self._projection()[0])

    def loaded(self) -> Elements:
        """Return all cached records, including collapsed branches, without fetching."""
        return deepcopy(self._cache)

    @staticmethod
    def _ids(elements: Elements) -> set[str]:
        return {
            str(e["data"]["id"])
            for group in ("nodes", "edges")
            for e in elements.get(group, [])
        }

    def _index(self) -> _RecordIndex:
        # Cache updates replace the graph, so identity also invalidates trial indexes.
        if self._record_index is None or self._record_index.elements is not self._cache:
            nodes = {n["data"]["id"]: n for n in self._cache["nodes"]}
            edges = {e["data"]["id"]: e for e in self._cache["edges"]}
            self._record_index = _RecordIndex(
                self._cache,
                nodes,
                edges,
                {key: index for index, key in enumerate([*nodes, *edges])},
            )
        return self._record_index

    def _anchors(self) -> set[str]:
        anchors = self._ids(self._base) | self._protected
        edges = self._index().edges
        for key in list(anchors):
            if key in edges:
                anchors.update(
                    str(edges[key]["data"][endpoint])
                    for endpoint in ("source", "target")
                )
        return anchors

    def _changed(self) -> None:
        current, support = self._projection()
        previous = self._ids(self._last_view)
        present = self._ids(current)
        base = self._ids(self._base)
        kinds = {
            str(e["data"]["id"]): group[:-1]
            for graph in (self._last_view, current)
            for group in ("nodes", "edges")
            for e in graph[group]
        }
        self.changes = [
            {
                "id": key,
                "kind": kinds.get(key, "record"),
                "change": "added"
                if key not in previous
                else "hidden"
                if key not in present
                else "retained",
                "reason": "not_in_view"
                if key not in present
                else "starting_graph"
                if key in base
                else "protected"
                if key in self._protected
                else "shared"
                if len(support.get(key, set())) > 1
                else "active_branch",
                "retained_by": sorted(
                    {self._branches[k].node_id for k in support.get(key, set())}
                )
                if key in present
                else [],
            }
            for key in sorted(previous | present)
        ]
        self._last_view = deepcopy(current)
        self.revision += 1

    def request(
        self,
        node_id: ElementId,
        *,
        query: dict[str, Any] | None = None,
        more: bool = False,
    ) -> ExpansionRequest | None:
        """Start a batch, or restore a cached branch without fetching again."""
        if str(node_id) not in {str(n["data"]["id"]) for n in self.view()["nodes"]}:
            raise ValueError("Expansion requires a displayed starting node.")
        key, branch = self._branch(node_id, query)
        if branch.pending:
            return None
        if branch.fetched and not more:
            was_open = branch.opened
            branch.opened = True
            if self._over_bulk_limit():
                branch.opened = was_open
                branch.error = "Expansion stopped at the configured record limit."
                return None
            branch.error = None
            self._changed()
            return None
        if not branch.has_more:
            return None
        request = ExpansionRequest(
            uuid4().hex,
            key,
            str(node_id),
            deepcopy(branch.query),
            deepcopy(branch.cursor),
            self.limits.page_size,
            self.source_id,
            self.source_version,
            branch.revision,
        )
        self._requests[request.request_id] = request
        branch.pending = request.request_id
        branch.error = None
        return request

    def apply_response(self, response: ExpansionResponse) -> bool:
        """Atomically accept a current response; return false for stale/duplicate data."""
        request = self._requests.get(response.request_id)
        if request is None:
            return False
        branch = self._branches[request.branch_id]
        displayed_before = self._ids(self.view())
        if (
            request.source_version != self.source_version
            or request.source_id != self.source_id
            or request.revision != branch.revision
            or branch.pending != response.request_id
            or request.node_id not in self._ids(self.view())
        ):
            self._requests.pop(response.request_id, None)
            if branch.pending == response.request_id:
                branch.pending = None
            return False
        try:
            for count in (response.total_nodes, response.total_edges):
                if count is not None and (
                    isinstance(count, bool) or not isinstance(count, int) or count < 0
                ):
                    raise ValueError(
                        "Expansion totals must be nonnegative integers or None."
                    )
            if response.has_more and response.cursor == request.cursor:
                raise ValueError("A continuing response must advance its cursor.")
            json.dumps(response.cursor, allow_nan=False)
            incoming = _validate_loaded(response.elements, strict=False)
            if not isinstance(response.has_more, bool):
                raise ValueError("has_more must be a boolean.")
            for group, other in (("nodes", "edges"), ("edges", "nodes")):
                other_records = (
                    self._index().nodes if other == "nodes" else self._index().edges
                )
                if any(e["data"]["id"] in other_records for e in incoming[group]):
                    raise ValueError(
                        "A response cannot change a record's node/edge identity."
                    )
            incoming["nodes"] = [
                n
                for n in incoming["nodes"]
                if str(n["data"]["id"]) not in self._deleted
            ]
            incoming["edges"] = [
                e
                for e in incoming["edges"]
                if not (
                    {str(e["data"][x]) for x in ("id", "source", "target")}
                    & self._deleted
                )
            ]
            known = self._index().order
            additions = {
                group: [e for e in incoming[group] if str(e["data"]["id"]) not in known]
                for group in ("nodes", "edges")
            }
            candidate = (
                upsert_elements(
                    self._cache, nodes=additions["nodes"], edges=additions["edges"]
                )
                if additions["nodes"] or additions["edges"]
                else self._cache
            )
            node_ids = {str(n["data"]["id"]) for n in incoming["nodes"]} - {
                request.node_id
            }
            cached_edges = (
                self._index().edges
                if candidate is self._cache
                else {e["data"]["id"]: e for e in candidate["edges"]}
            )
            for edge in incoming["edges"]:
                data = cached_edges[str(edge["data"]["id"])]["data"]
                node_ids.update(
                    str(data[x])
                    for x in ("source", "target")
                    if str(data[x]) != request.node_id
                )
            old_cache, old_branch = self._cache, deepcopy(branch)
            self._cache = candidate
            branch.node_ids.update(node_ids)
            branch.edge_ids.update(str(e["data"]["id"]) for e in incoming["edges"])
            branch.opened = True
            if self._over_bulk_limit():
                self._cache = old_cache
                self._branches[request.branch_id] = old_branch
                self.fail(
                    response.request_id,
                    "Expansion stopped at the configured record limit.",
                )
                return False
            branch.fetched = True
            branch.has_more = response.has_more
            branch.cursor = deepcopy(response.cursor)
            branch.total_nodes, branch.total_edges = (
                response.total_nodes,
                response.total_edges,
            )
            branch.pending = None
            self._requests.pop(response.request_id)
            self._place_new_nodes(request.node_id, displayed_before)
            self._changed()
            return True
        except (TypeError, ValueError, KeyError) as error:
            self.fail(response.request_id, str(error))
            raise

    def _place_new_nodes(self, origin_id: str, known: set[str]) -> None:
        origin = self._index().nodes[origin_id]
        position = origin.get("position", {"x": 0, "y": 0})
        additions = [
            n
            for n in self._projection()[0]["nodes"]
            if str(n["data"]["id"]) not in known and "position" not in n
        ]
        positions = {}
        for index, node in enumerate(additions):
            angle = index * 2.399963
            radius = 130 + 35 * math.sqrt(index)
            positions[str(node["data"]["id"])] = {
                "x": position["x"] + radius * math.cos(angle),
                "y": position["y"] + radius * math.sin(angle),
            }
        if positions:
            self._cache = {
                "nodes": [
                    {**node, "position": positions[str(node["data"]["id"])]}
                    if str(node["data"]["id"]) in positions
                    else node
                    for node in self._cache["nodes"]
                ],
                "edges": self._cache["edges"],
            }

    def fail(self, request_id: str, message: str) -> None:
        """Finish a failed request without advancing its cursor or changing its view."""
        request = self._requests.pop(request_id, None)
        if request:
            branch = self._branches[request.branch_id]
            if branch.pending == request_id:
                branch.pending = None
                branch.error = str(message)

    def expand(
        self,
        node_id: ElementId,
        provider: ExpansionProvider,
        *,
        query: dict[str, Any] | None = None,
        more: bool = False,
    ) -> bool:
        """Accept one synchronous batch, preserving the last valid view on failure.

        Return true for an accepted provider response. Restoring cached branches,
        already-pending requests, and failures return false; inspect ``describe``
        for pending/error status and ``view`` for the resulting graph.
        """
        request = self.request(node_id, query=query, more=more)
        if request is None:
            return False
        try:
            response = provider.expand(request)
            if response.request_id != request.request_id:
                raise ValueError(
                    "Provider response request_id does not match its request."
                )
            return self.apply_response(response)
        except Exception as error:
            self.fail(request.request_id, str(error))
            return False

    def collapse(
        self, node_ids: list[ElementId] | None = None, *, branch_id: str | None = None
    ) -> None:
        """Close branches, retaining anchors; an explicit branch_id takes precedence."""
        ids = set(normalize_id_list(node_ids or [], option_name="node_ids"))
        for key, branch in self._branches.items():
            matches = (
                key == branch_id if branch_id is not None else branch.node_id in ids
            )
            if matches:
                branch.opened = False
                branch.revision += 1
                if branch.pending:
                    self._requests.pop(branch.pending, None)
                    branch.pending = None
        self._invalidate_inactive_requests()
        if self.bulk and self.bulk["status"] == "running":
            self.cancel()
        self._changed()

    def _invalidate_inactive_requests(self) -> None:
        visible = self._ids(self.view())
        for branch in self._branches.values():
            if branch.node_id not in visible and branch.pending:
                self._requests.pop(branch.pending, None)
                branch.pending = None
                branch.revision += 1

    def collapse_all(self) -> None:
        """Close all branches, preserving starting and explicitly protected records."""
        self.collapse([b.node_id for b in self._branches.values()])

    def protect(self, element_ids: list[ElementId], *, enabled: bool = True) -> None:
        """Keep records visible independently of branch state; not a position lock."""
        ids = set(normalize_id_list(element_ids, option_name="element_ids"))
        if not ids <= self._ids(self._cache):
            raise ValueError("Only loaded records can be protected.")
        self._protected = self._protected | ids if enabled else self._protected - ids
        self._changed()

    def set_visibility(
        self, *, hidden: list[str] | None = None, filtered: list[str] | None = None
    ) -> None:
        """Set independent hide/filter masks; an empty list restores only that mask."""
        masks = {
            name: set(normalize_id_list(values, option_name=name))
            for name, values in (("hidden", hidden), ("filtered", filtered))
            if values is not None
        }
        for name, values in masks.items():
            setattr(self, "_" + name, values)
        self._invalidate_inactive_requests()
        self._changed()

    def update_records(self, elements: Elements) -> None:
        """Apply explicit application-owned edits to the cache, including positions."""
        candidate = upsert_elements(self._cache, **elements, replace=False)
        self._cache = _validate_loaded(candidate)
        edge_index = {
            str(edge["data"]["id"]): edge["data"] for edge in candidate["edges"]
        }
        for branch in self._branches.values():
            for edge_id in branch.edge_ids & edge_index.keys():
                branch.node_ids.update(
                    str(edge_index[edge_id][endpoint])
                    for endpoint in ("source", "target")
                    if str(edge_index[edge_id][endpoint]) != branch.node_id
                )
        self._changed()

    def delete_records(self, element_ids: list[ElementId]) -> None:
        """Apply actual source deletion, unlike collapse; suppress stale resurrection."""
        ids = set(normalize_id_list(element_ids, option_name="element_ids"))
        nodes = {str(n["data"]["id"]) for n in self._cache["nodes"]} & ids
        updated = delete_elements(
            self._cache, node_ids=sorted(nodes), edge_ids=sorted(ids - nodes)
        )
        self._deleted.update(self._ids(self._cache) - self._ids(updated))
        self._cache = updated
        self._base = {
            group: [
                e
                for e in self._base[group]
                if str(e["data"]["id"]) not in self._deleted
            ]
            for group in ("nodes", "edges")
        }
        self._protected -= self._deleted
        self.cancel()
        self._changed()

    def invalidate(self, elements: Elements, *, source_version: str) -> None:
        """Replace the source checkpoint explicitly, clearing incompatible exploration."""
        replacement = ExpansionController(
            elements,
            source_id=self.source_id,
            source_version=source_version,
            config=self.limits,
        )
        self.__dict__.update(replacement.__dict__)

    def commands(
        self, previous: Elements, *, restore_positions: bool = False
    ) -> list[GraphCommand]:
        """Reconcile the view; restore_positions explicitly reapplies saved positions."""
        current = self.view()
        known = self._ids(previous)
        removed = known - self._ids(current)
        nodes = {str(n["data"]["id"]) for n in previous.get("nodes", [])}
        commands: list[GraphCommand] = []
        if removed:
            commands.append(
                delete_elements_command(
                    uuid4().hex,
                    node_ids=sorted(removed & nodes),
                    edge_ids=sorted(removed - nodes),
                )
            )
        updates: Elements = {"nodes": [], "edges": []}
        for group in ("nodes", "edges"):
            previous_records = {
                str(e["data"]["id"]): e for e in previous.get(group, [])
            }
            for record in current[group]:
                old = previous_records.get(str(record["data"]["id"]), {})
                if group == "nodes" and old and not restore_positions:
                    record = {k: v for k, v in record.items() if k != "position"}
                    old = {k: v for k, v in old.items() if k != "position"}
                if record != old:
                    updates[group].append(record)
        if updates["nodes"] or updates["edges"]:
            commands.append(
                upsert_elements_command(uuid4().hex, **updates, replace=False)
            )
        return commands

    def start_bulk(
        self, node_ids: list[ElementId], *, query: dict[str, Any] | None = None
    ) -> None:
        """Queue breadth-first bounded exploration; call step once per application tick."""
        ids = normalize_id_list(
            node_ids or [n["data"]["id"] for n in self._base["nodes"]],
            option_name="node_ids",
        )
        view = self.view()
        if not set(ids) <= {n["data"]["id"] for n in view["nodes"]}:
            raise ValueError("Bulk expansion requires displayed starting nodes.")
        filters = _query(query)
        self.cancel()
        self.bulk = {
            "id": uuid4().hex,
            "status": "running",
            "queue": [[i, 0] for i in sorted(set(ids))],
            "visited": [],
            "query": filters,
            "batches": 0,
            "baseline": {
                g: [str(e["data"]["id"]) for e in view[g]] for g in ("nodes", "edges")
            },
            "limits": {"nodes": self.limits.max_nodes, "edges": self.limits.max_edges},
        }

    def _over_bulk_limit(self) -> bool:
        if not self.bulk or self.bulk["status"] != "running":
            return False
        view = self._projection()[0]
        exceeded = any(
            len(
                {str(e["data"]["id"]) for e in view[group]}
                - set(self.bulk["baseline"][group])
            )
            > self.bulk["limits"][group]
            for group in ("nodes", "edges")
        )
        if exceeded:
            self.bulk["status"] = "limited"
        return exceeded

    def step(self, provider: ExpansionProvider) -> bool:
        """Process at most one batch. Return whether more bulk work remains."""
        if not self.bulk or self.bulk["status"] != "running":
            return False
        bulk = self.bulk
        while bulk["queue"]:
            node_id, depth = bulk["queue"].pop(0)
            if depth >= self.limits.max_depth or node_id not in self._ids(self.view()):
                continue
            key, branch = self._branch(node_id, bulk["query"])
            if key in bulk["visited"]:
                continue
            if not branch.fetched or branch.has_more:
                self.expand(node_id, provider, query=bulk["query"], more=branch.fetched)
                branch = self._branches[key]
                bulk["batches"] += 1
                if branch.error:
                    if bulk["status"] == "running":
                        bulk["status"] = "failed"
                    bulk["queue"].insert(0, [node_id, depth])
                    return False
            else:
                self.request(node_id, query=bulk["query"])
                if bulk["status"] != "running":
                    bulk["queue"].insert(0, [node_id, depth])
                    return False
            if branch.has_more:
                bulk["queue"].insert(0, [node_id, depth])
            else:
                bulk["visited"].append(key)
                bulk["queue"].extend(
                    [[child, depth + 1] for child in sorted(branch.node_ids)]
                )
            if not bulk["queue"]:
                bulk["status"] = "complete"
            return bool(bulk["status"] == "running")
        bulk["status"] = "complete"
        return False

    def cancel(self) -> None:
        """Invalidate outstanding responses and stop scheduling new bulk batches."""
        for branch in self._branches.values():
            if branch.pending:
                branch.revision += 1
                branch.pending = None
        self._requests.clear()
        if self.bulk and self.bulk["status"] in {"running", "failed"}:
            self.bulk["status"] = "cancelled"

    def retry_bulk(self) -> None:
        """Resume a failed bulk request at its unchanged cursor."""
        if self.bulk and self.bulk["status"] == "failed":
            self.bulk["status"] = "running"

    def reveal(self, element_id: ElementId) -> None:
        """Restore a cached result through recorded branches, including real context."""
        target = str(element_id)
        routes: dict[str, list[str]] = {key: [] for key in self._anchors()}
        pending = deque(routes)
        by_node: dict[str, list[tuple[str, _Branch]]] = defaultdict(list)
        for key, branch in self._branches.items():
            if branch.fetched:
                by_node[branch.node_id].append((key, branch))
        while pending and target not in routes:
            anchor = pending.popleft()
            for key, branch in by_node[anchor]:
                for child in sorted(branch.node_ids | branch.edge_ids):
                    if child not in routes:
                        routes[child] = [*routes[anchor], key]
                        pending.append(child)
        if target not in routes or target in self._deleted:
            raise ValueError("No cached exploration path reaches this record.")
        restore = {target}
        for edge in self._cache["edges"]:
            if str(edge["data"]["id"]) == target:
                restore.update(
                    str(edge["data"][endpoint]) for endpoint in ("source", "target")
                )
        for key in routes[target]:
            branch = self._branches[key]
            branch.opened = True
            restore.update(branch.node_ids | branch.edge_ids | {branch.node_id})
        self._hidden -= restore
        self._filtered -= restore
        self._changed()

    def reveal_search_result(self, result: dict[str, Any], node_id: str) -> None:
        """Validate and reveal a provider-supplied real path from an existing anchor."""
        for name, expected in (
            ("source_version", self.source_version),
            ("source_dataset_id", self.source_id),
        ):
            if name in result and result[name] != expected:
                raise ValueError(
                    "Source search result is obsolete; refresh the source search."
                )
        path = result.get("paths", {}).get(node_id)
        if not path or path[-1] != node_id or path[0] not in self._anchors():
            raise ValueError(
                "Source search must provide a path from a starting/protected record."
            )
        incoming = _validate_loaded(result["elements"])
        if set(path) & self._deleted:
            raise ValueError(
                "Search result contains deleted records; refresh the source."
            )
        known = self._ids(self._cache)
        candidate = upsert_elements(
            self._cache,
            nodes=[
                n
                for n in incoming["nodes"]
                if n["data"]["id"] not in known | self._deleted
            ],
            edges=[
                e
                for e in incoming["edges"]
                if e["data"]["id"] not in known
                and not {e["data"][name] for name in ("id", "source", "target")}
                & self._deleted
            ],
        )
        if not set(path) <= {n["data"]["id"] for n in candidate["nodes"]}:
            raise ValueError("Source search path has a missing node.")
        contributions = []
        supplied_edges = {e["data"]["id"] for e in incoming["edges"]}
        for source, target in zip(path, path[1:]):
            edges = {
                str(e["data"]["id"])
                for e in candidate["edges"]
                if e["data"]["id"] in supplied_edges
                and {str(e["data"]["source"]), str(e["data"]["target"])}
                == {source, target}
            }
            if not edges:
                raise ValueError("Source search path has a missing relationship.")
            contributions.append((source, target, edges))
        self._cache = candidate
        for source, target, edges in contributions:
            _, branch = self._branch(source)
            branch.node_ids.add(target)
            branch.edge_ids.update(edges)
            branch.fetched = True
            branch.opened = True
        self.reveal(node_id)

    def _starting_graph(self) -> Elements:
        """Resolve starting records against current edits, with required context."""
        base = self._ids(self._base)
        nodes = self._index().nodes
        edges = [e for e in self._cache["edges"] if e["data"]["id"] in base]
        node_ids = base & nodes.keys()
        for edge in edges:
            node_ids.update(edge["data"][name] for name in ("source", "target"))
        pending = list(node_ids)
        while pending:
            parent = nodes[pending.pop()]["data"].get("parent")
            if parent is not None and parent not in node_ids:
                node_ids.add(parent)
                pending.append(parent)
        return {
            "nodes": [n for key, n in nodes.items() if key in node_ids],
            "edges": edges,
        }

    def snapshot(self) -> dict[str, Any]:
        """Export state without provider objects; source properties may be sensitive."""
        branches = {
            key: {
                **asdict(b),
                "node_ids": sorted(b.node_ids),
                "edge_ids": sorted(b.edge_ids),
                "pending": None,
            }
            for key, b in self._branches.items()
        }
        return deepcopy(
            {
                "schema_version": 1,
                "source_id": self.source_id,
                "source_version": self.source_version,
                "config": asdict(self.limits),
                "base": self._starting_graph(),
                "loaded": self._cache,
                "branches": branches,
                "protected": sorted(self._protected),
                "hidden": sorted(self._hidden),
                "filtered": sorted(self._filtered),
                "deleted": sorted(self._deleted),
                "viewport": self.viewport,
            }
        )

    @classmethod
    def restore(
        cls,
        snapshot: dict[str, Any],
        *,
        source_version: str,
        source_id: str | None = None,
    ) -> ExpansionController:
        """Restore a compatible snapshot; require explicit invalidation for new sources."""
        if snapshot.get("schema_version") != 1 or snapshot.get("source_version") != str(
            source_version
        ):
            raise ValueError(
                "Snapshot schema/source version differs; invalidate explicitly."
            )
        if source_id is not None and snapshot.get("source_id") != str(source_id):
            raise ValueError("Snapshot source identity differs; invalidate explicitly.")
        obj = cls(
            snapshot["base"],
            source_id=snapshot["source_id"],
            source_version=source_version,
            config=ExpansionConfig(**snapshot["config"]),
        )
        obj._cache = _validate_loaded(snapshot["loaded"])
        nodes = {str(n["data"]["id"]) for n in obj._cache["nodes"]}
        edges = {str(e["data"]["id"]) for e in obj._cache["edges"]}
        if not obj._ids(obj._base) <= nodes | edges:
            raise ValueError("Snapshot starting records must exist in its cache.")
        for key, value in snapshot["branches"].items():
            data = deepcopy(value)
            data["node_ids"], data["edge_ids"] = (
                set(data["node_ids"]),
                set(data["edge_ids"]),
            )
            data["query"] = _query(data["query"])
            data["pending"] = None
            if (
                isinstance(data["revision"], bool)
                or not isinstance(data["revision"], int)
                or data["revision"] < 0
                or any(
                    not isinstance(data[field], bool)
                    for field in ("opened", "fetched", "has_more")
                )
            ):
                raise ValueError("Invalid snapshot branch state.")
            if obj.branch_id(data["node_id"], data["query"]) != key:
                raise ValueError("Invalid snapshot branch identity.")
            deleted = set(snapshot["deleted"])
            if (
                data["node_id"] not in nodes | deleted
                or not data["node_ids"] <= nodes | deleted
                or not data["edge_ids"] <= edges | deleted
            ):
                raise ValueError("Snapshot branch references unknown records.")
            obj._branches[key] = _Branch(**data)
        for name in ("protected", "hidden", "filtered", "deleted"):
            setattr(obj, "_" + name, set(snapshot[name]))
        obj.viewport = deepcopy(snapshot["viewport"])
        if not isinstance(obj.viewport, dict):
            raise ValueError("Snapshot viewport must be a dictionary.")
        if obj.viewport:
            from .commands import viewport_command

            viewport_command("snapshot-validation", "set_viewport", **obj.viewport)
        if not obj._protected <= nodes | edges:
            raise ValueError("Snapshot protected records must exist in its cache.")
        json.dumps(obj.snapshot(), allow_nan=False)
        obj._changed()
        return obj

    def describe(self, provider: ExpansionProvider | None = None) -> dict[str, Any]:
        """Return JSON configuration for graph_workbench(expansion=...).

        Includes independent expand/collapse availability and exact next-change
        counts when a local preview exists. Unknown remote counts remain None.
        """
        view = self.view()
        visible = self._ids(view)
        node_ids = {n["data"]["id"] for n in view["nodes"]}
        rows: dict[str, Any] = {}
        for node in view["nodes"]:
            node_id = str(node["data"]["id"])
            key, branch = self._branch(node_id)
            closed = {k for k, b in self._branches.items() if b.node_id == node_id}
            collapsed, _ = self._projection(closed)
            hidden = visible - self._ids(collapsed)
            next_nodes: int | None = None
            next_edges: int | None = None
            available: bool | None = None
            preview = getattr(provider, "preview", None)
            if branch.fetched and not branch.opened:
                restored = copy(self)
                restored._branches = {**self._branches, key: deepcopy(branch)}
                restored._branches[key].opened = True
                restored_view = restored.view()
                next_nodes = len(
                    {str(n["data"]["id"]) for n in restored_view["nodes"]} - visible
                )
                next_edges = len(
                    {str(e["data"]["id"]) for e in restored_view["edges"]} - visible
                )
            elif preview and branch.has_more:
                request = ExpansionRequest(
                    "preview",
                    key,
                    node_id,
                    deepcopy(branch.query),
                    deepcopy(branch.cursor),
                    self.limits.page_size,
                    self.source_id,
                    self.source_version,
                    branch.revision,
                )
                try:
                    batch = preview(request)
                    available = batch.has_more
                    trial = copy(self)
                    trial._branches = {**self._branches, key: deepcopy(branch)}
                    trial._requests = {request.request_id: request}
                    trial._branches[key].pending = request.request_id
                    trial.bulk = None
                    trial.apply_response(batch)
                    trial_view = trial.view()
                    next_nodes = len(
                        {str(n["data"]["id"]) for n in trial_view["nodes"]} - visible
                    )
                    next_edges = len(
                        {str(e["data"]["id"]) for e in trial_view["edges"]} - visible
                    )
                except Exception:
                    # A preview is optional; an unavailable source must not blank the view.
                    next_nodes = next_edges = None
            elif not branch.has_more:
                next_nodes, next_edges = 0, 0
            rows[node_id] = {
                "branch_id": key,
                "opened": branch.opened,
                "fetched": branch.fetched,
                "has_more": branch.has_more,
                "can_expand": not branch.opened
                and (
                    branch.fetched
                    or next_nodes is None
                    or available
                    or bool(next_nodes or next_edges)
                ),
                "can_load_more": branch.opened and branch.has_more,
                "can_collapse": any(self._branches[k].opened for k in closed),
                "next_nodes": next_nodes,
                "next_edges": next_edges,
                "collapse_nodes": len(hidden & node_ids),
                "collapse_edges": len(hidden - node_ids),
                "protected": node_id in self._protected,
                "pending": bool(branch.pending),
                "error": branch.error
                or next(
                    (
                        self._branches[k].error
                        for k in sorted(closed)
                        if self._branches[k].error
                    ),
                    None,
                ),
            }
        return {
            "nodes": rows,
            "controller_id": self._instance_id,
            "branches": [
                {
                    "branch_id": k,
                    "node_id": b.node_id,
                    "query": deepcopy(b.query),
                    "opened": b.opened,
                    "active": b.opened and b.node_id in visible,
                    "has_more": b.has_more,
                    "error": b.error,
                }
                for k, b in self._branches.items()
                if b.fetched or b.pending or b.error
            ],
            "limits": asdict(self.limits),
            "bulk": deepcopy(self.bulk),
            "source_id": self.source_id,
            "source_version": self.source_version,
            "view_revision": self.revision,
            "loaded": self.loaded(),
            "hidden_count": len(self._hidden | self._filtered),
            "source_search": callable(getattr(provider, "search", None)),
            "source_analysis": callable(getattr(provider, "analyze", None)),
            "search_result": deepcopy(self.search_result),
            "analysis_result": deepcopy(self.analysis_result),
            "error": self.last_error,
        }

    def handle_event(
        self, event: GraphEvent | None, provider: ExpansionProvider
    ) -> None:
        """Handle explicit expansion intents; applications schedule bulk step separately."""
        self.last_error = None
        try:
            self._handle_event(event, provider)
        except Exception as error:
            self.last_error = str(error)

    def _handle_event(
        self, event: GraphEvent | None, provider: ExpansionProvider
    ) -> None:
        if not event or event.get("action") != "expansion":
            return
        data = event.get("data", {})
        if data.get("controller_id", self._instance_id) != self._instance_id:
            return
        identity = str(data.get("request_id", event.get("timestamp", "")))
        if identity in self._handled:
            return
        self._handled.add(identity)
        operation = data.get("operation")
        if data.get("limits") is not None:
            self.limits = ExpansionConfig(**data["limits"])
        ids = data.get("node_ids", [])
        if operation == "retry" and self.bulk and self.bulk["status"] == "failed":
            self.retry_bulk()
        elif operation in {"expand", "load_more", "retry"}:
            for node_id in ids:
                if data.get("branch_id") and str(node_id) not in self._ids(self.view()):
                    self.reveal(node_id)
                self.expand(
                    node_id,
                    provider,
                    query=data.get("query"),
                    more=operation != "expand",
                )
        elif operation == "collapse":
            self.collapse(ids, branch_id=data.get("branch_id"))
        elif operation == "collapse_all":
            self.collapse_all()
        elif operation in {"protect", "unprotect"}:
            self.protect(ids, enabled=operation == "protect")
        elif operation == "expand_all":
            self.start_bulk(ids, query=data.get("query"))
        elif operation == "cancel":
            self.cancel()
        elif operation == "continue":
            self.step(provider)
        elif operation == "search":
            search = getattr(provider, "search", None)
            if not callable(search):
                raise ValueError("The provider does not support source search.")
            self.search_result = search(
                str(data.get("text", "")),
                roots=sorted(self._anchors()),
                limit=self.limits.page_size,
            )
            self.search_result = {
                **self.search_result,
                "scope": "source",
                "source_dataset_id": self.source_id,
                "source_version": self.source_version,
                "view_revision": self.revision,
            }
        elif operation == "reveal":
            for node_id in ids:
                if data.get("scope") == "source" and self.search_result:
                    self.reveal_search_result(self.search_result, node_id)
                else:
                    self.reveal(node_id)
        elif operation == "analyze":
            analyze = getattr(provider, "analyze", None)
            if not callable(analyze):
                raise ValueError("The provider does not support source analysis.")
            result = analyze(deepcopy(data))
            self.analysis_result = {
                **result,
                # Identical results from a new request must reapply cleared highlights.
                "request_id": identity,
                "scope": "source",
                "source_dataset_id": self.source_id,
                "source_version": self.source_version,
                "view_revision": self.revision,
                "node_count": result.get("node_count"),
                "edge_count": result.get("edge_count"),
                "complete": result.get("complete", False),
                "source_complete": result.get("complete", False),
            }
            result_ids = set(result.get("node_ids", [])) | set(
                result.get("edge_ids", [])
            )
            if result.get("node_id") is not None:
                result_ids.add(result["node_id"])
            for group in result.get("components", []):
                result_ids.update(group.get("node_ids", []))
                result_ids.update(group.get("edge_ids", []))
            self.analysis_result["collapsed_result_ids"] = sorted(
                result_ids - self._ids(self.view())
            )
