"""Branch ownership, stale responses, cache preservation and bounded exploration."""

import json
import time
import tracemalloc
from dataclasses import replace

import pytest

from st_graph_workbench import (
    ExpansionConfig,
    ExpansionController,
    ExpansionResponse,
    InMemoryExpansionProvider,
    apply_graph_commands,
)


def graph():
    ids = ["ABC123", "location-1", "location-2", "camera-1", "shared", "time-1", "leaf"]
    links = [
        ("ABC123", "location-1"),
        ("ABC123", "location-2"),
        ("location-1", "camera-1"),
        ("location-1", "shared"),
        ("location-2", "shared"),
        ("camera-1", "time-1"),
        ("time-1", "camera-1"),
        ("shared", "leaf"),
    ]
    return {
        "nodes": [{"data": {"id": key, "label": "RECORD", "name": key}} for key in ids],
        "edges": [
            {
                "data": {
                    "id": f"e-{index}",
                    "source": a,
                    "target": b,
                    "label": "LINK",
                    "observed_at": "2026-01-01T12:00:00Z",
                }
            }
            for index, (a, b) in enumerate(links)
        ],
    }


def setup(config=None):
    source = graph()
    return ExpansionController(
        {"nodes": source["nodes"][:1], "edges": []}, config=config
    ), InMemoryExpansionProvider(source)


def ids(controller):
    return {n["data"]["id"] for n in controller.view()["nodes"]}


def opened():
    controller, provider = setup()
    for key in ("ABC123", "location-1", "location-2", "camera-1"):
        assert controller.expand(key, provider)
    return controller, provider


def test_independent_locations_shared_records_and_nested_restore():
    controller, provider = opened()
    controller.expand("time-1", provider)
    before = controller.loaded()
    controller.collapse(["location-1"])
    assert ids(controller) == {"ABC123", "location-1", "location-2", "shared"}
    assert any(
        row["id"] == "shared" and row["change"] == "retained"
        for row in controller.changes
    )
    assert controller.loaded() == before
    assert not controller.expand("location-1", provider)
    assert "time-1" in ids(controller)
    assert controller.loaded() == before
    controller.collapse(["ABC123"])
    assert ids(controller) == {"ABC123"}
    controller.expand("ABC123", provider)
    assert "time-1" in ids(controller)


@pytest.mark.parametrize(
    "order", [("location-1", "location-2"), ("location-2", "location-1")]
)
def test_shared_removed_only_after_last_branch(order):
    controller, _ = opened()
    controller.collapse([order[0]])
    assert "shared" in ids(controller)
    controller.collapse([order[1]])
    assert ids(controller) == {"ABC123", "location-1", "location-2"}


def test_collapse_all_protection_and_filter_masks():
    controller, provider = opened()
    controller.protect(["shared"])
    controller.collapse_all()
    assert ids(controller) == {"ABC123", "shared"}
    controller.set_visibility(hidden=["shared"], filtered=["ABC123"])
    assert not ids(controller)
    controller.set_visibility(hidden=[])
    assert ids(controller) == {"shared"}
    controller.set_visibility(filtered=[])
    controller.protect(["shared"], enabled=False)
    assert ids(controller) == {"ABC123"}
    controller.expand("ABC123", provider)
    assert ids(controller) == {"ABC123", "location-1", "location-2"}


def test_duplicate_stale_cancelled_and_out_of_order_responses():
    controller, provider = setup()
    request = controller.request("ABC123")
    response = provider.expand(request)
    assert controller.apply_response(response)
    assert not controller.apply_response(response)
    first = controller.request("location-1")
    second = controller.request("location-2")
    controller.collapse(["location-1"])
    assert not controller.apply_response(provider.expand(first))
    assert controller.apply_response(provider.expand(second))
    pending = controller.request("shared")
    controller.cancel()
    assert not controller.apply_response(provider.expand(pending))
    pending = controller.request("shared")
    controller.invalidate(
        {"nodes": graph()["nodes"][:1], "edges": []}, source_version="2"
    )
    assert not controller.apply_response(provider.expand(pending))


def test_failure_and_invalid_response_leave_view_unchanged():
    controller, provider = setup()
    before = controller.view()
    request = controller.request("ABC123")
    invalid = ExpansionResponse(
        request.request_id,
        {
            "nodes": [],
            "edges": [{"data": {"id": "bad", "source": "missing", "target": "ABC123"}}],
        },
    )
    with pytest.raises(ValueError):
        controller.apply_response(invalid)
    assert controller.view() == before
    retry = controller.request("ABC123")
    assert retry.cursor is None and retry.request_id != request.request_id
    assert controller.apply_response(provider.expand(retry))


def test_pagination_cursor_filters_edge_only_and_count_preview():
    controller, provider = setup(ExpansionConfig(page_size=1))
    assert controller.describe(provider)["nodes"]["ABC123"]["next_nodes"] == 1
    controller.expand("ABC123", provider)
    assert len(ids(controller)) == 2
    controller.expand("ABC123", provider, more=True)
    assert len(ids(controller)) == 3
    controller.expand("location-1", provider, query={"direction": "incoming"})
    # The same records can be independently required by differently filtered branches.
    assert len(controller.describe(provider)["branches"]) == 2
    root = graph()["nodes"][:3]
    edge_controller = ExpansionController({"nodes": root, "edges": []})
    info = edge_controller.describe(provider)["nodes"]["ABC123"]
    assert info["next_nodes"] == 0 and info["next_edges"] == 2 and info["can_expand"]
    edge_controller.expand("ABC123", provider)
    assert len(edge_controller.view()["edges"]) == 2
    edge_controller.collapse(["ABC123"])
    assert (
        len(edge_controller.view()["nodes"]) == 3
        and not edge_controller.view()["edges"]
    )
    request = controller.request("location-2", query={"time_from": "2027-01-01"})
    assert provider.expand(request).elements == {"nodes": [], "edges": []}


def test_edits_positions_deletions_and_snapshot_roundtrip():
    controller, provider = opened()
    controller.update_records(
        {
            "nodes": [
                {
                    "data": {"id": "camera-1", "name": "Edited"},
                    "position": {"x": 44, "y": 99},
                }
            ]
        }
    )
    controller.collapse(["location-1"])
    controller.expand("location-1", provider)
    camera = next(
        n for n in controller.view()["nodes"] if n["data"]["id"] == "camera-1"
    )
    assert camera["data"]["name"] == "Edited" and camera["position"] == {
        "x": 44,
        "y": 99,
    }
    snapshot = json.loads(json.dumps(controller.snapshot()))
    restored = ExpansionController.restore(snapshot, source_version="1")
    assert restored.view() == controller.view()
    with pytest.raises(ValueError):
        ExpansionController.restore(snapshot, source_version="2")
    controller.delete_records(["camera-1"])
    controller.expand("location-1", provider, query={"direction": "outgoing"})
    assert "camera-1" not in ids(controller)


def test_commands_match_projection_without_replacing_existing_positions():
    controller, provider = setup()
    previous = controller.view()
    assert controller.commands(previous) == []
    controller.expand("ABC123", provider)
    commands = controller.commands(previous)
    assert apply_graph_commands(previous, commands) == controller.view()
    previous = controller.view()
    controller.collapse_all()
    assert (
        apply_graph_commands(previous, controller.commands(previous))
        == controller.view()
    )


def test_bulk_depth_limits_and_recovery():
    controller, provider = setup(ExpansionConfig(page_size=1, max_depth=2))
    controller.start_bulk(["ABC123"])
    for _ in range(30):
        if not controller.step(provider):
            break
    assert controller.bulk["status"] == "complete"
    assert "camera-1" in ids(controller) and "time-1" not in ids(controller)
    limited, provider = setup(ExpansionConfig(page_size=1, max_nodes=2))
    limited.start_bulk(["ABC123"])
    for _ in range(30):
        if not limited.step(provider):
            break
    assert len(ids(limited)) <= 3
    assert limited.bulk["status"] == "limited"


def test_source_search_returns_context_not_fabricated_edges():
    _, provider = setup()
    result = provider.search("time-1", roots=["ABC123"])
    assert result["paths"]["time-1"] == ["ABC123", "location-1", "camera-1", "time-1"]
    assert len(result["elements"]["edges"]) == 3


@pytest.mark.parametrize("count", [100, 1000, 10000])
def test_increasing_datasets_respect_limits(count, record_property):
    source = {
        "nodes": [{"data": {"id": str(i)}} for i in range(count)],
        "edges": [
            {"data": {"id": f"e{i}", "source": "0", "target": str(i)}}
            for i in range(1, count)
        ],
    }
    tracemalloc.start()
    start = time.perf_counter()
    provider = InMemoryExpansionProvider(source)
    controller = ExpansionController(
        {"nodes": source["nodes"][:1], "edges": []},
        config=ExpansionConfig(max_nodes=100, max_depth=1),
    )
    controller.update_records(source)
    assert len(controller.loaded()["nodes"]) == count
    controller.start_bulk(["0"])
    for _ in range(10):
        if not controller.step(provider):
            break
    describe_started = time.perf_counter()
    description = controller.describe(provider)
    record_property("describe_seconds", time.perf_counter() - describe_started)
    assert len(description["nodes"]) <= 101
    assert description["nodes"]["0"]["next_nodes"] == min(
        50, count - len(ids(controller))
    )
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    record_property("seconds", time.perf_counter() - start)
    record_property("peak_bytes", peak)
    assert len(ids(controller)) <= 101


def test_cached_bulk_reopen_obeys_display_limits():
    controller, provider = opened()
    controller.collapse(["ABC123"])
    controller.limits = ExpansionConfig(max_nodes=2)
    controller.start_bulk(["ABC123"])
    assert not controller.step(provider)
    assert ids(controller) == {"ABC123"}
    assert controller.bulk["status"] == "limited"


def test_retry_failure_cursor_and_cancellation():
    controller, provider = setup(ExpansionConfig(page_size=1))

    class Failing:
        def expand(self, request):
            raise RuntimeError("Provider unavailable; retry")

    controller.start_bulk(["ABC123"])
    assert not controller.step(Failing())
    assert controller.bulk["status"] == "failed"
    assert ids(controller) == {"ABC123"}
    controller.retry_bulk()
    assert controller.step(provider)
    assert len(ids(controller)) == 2
    controller.cancel()
    assert not controller.step(provider)
    assert controller.bulk["status"] == "cancelled"


def test_snapshot_integrity_and_controller_event_isolation():
    controller, provider = opened()
    snapshot = controller.snapshot()
    with pytest.raises(ValueError, match="identity"):
        ExpansionController.restore(snapshot, source_version="1", source_id="other")
    key = next(iter(snapshot["branches"]))
    snapshot["branches"][key]["node_ids"].append("unknown")
    with pytest.raises(ValueError, match="unknown"):
        ExpansionController.restore(snapshot, source_version="1")
    before = controller.view()
    controller.handle_event(
        {
            "action": "expansion",
            "data": {
                "operation": "collapse_all",
                "request_id": "old",
                "controller_id": "obsolete",
            },
        },
        provider,
    )
    assert controller.view() == before


def test_provider_cache_is_detached_and_unknown_counts_remain_unknown():
    source = graph()
    provider = InMemoryExpansionProvider(source)
    source["nodes"][1]["data"]["name"] = "Mutated"
    controller, _ = setup()
    assert controller.describe()["nodes"]["ABC123"]["next_nodes"] is None
    controller.expand("ABC123", provider)
    assert controller.view()["nodes"][1]["data"]["name"] == "location-1"
    controller.collapse_all()
    controller.expand("ABC123", provider)
    assert controller.describe(provider)["nodes"]["ABC123"]["next_nodes"] == 0


def test_cached_unpositioned_records_are_placed_only_when_displayed():
    controller, provider = setup()
    controller.update_records(graph())
    before = controller.loaded()
    controller.describe(provider)
    assert controller.loaded() == before
    controller.expand("ABC123", provider)
    positions = [
        n["position"] for n in controller.view()["nodes"] if n["data"]["id"] != "ABC123"
    ]
    assert len(positions) == 2 and positions[0] != positions[1]
    assert "position" not in next(
        n for n in controller.loaded()["nodes"] if n["data"]["id"] == "camera-1"
    )


def test_protected_edges_and_masked_badges():
    controller, provider = opened()
    controller.protect(["e-5"])
    controller.collapse_all()
    assert ids(controller) == {"ABC123", "camera-1", "time-1"}
    assert [e["data"]["id"] for e in controller.view()["edges"]] == ["e-5"]
    controller, provider = setup()
    controller.update_records(graph())
    controller.set_visibility(hidden=["location-1"])
    counts = controller.describe(provider)["nodes"]["ABC123"]
    assert counts["next_nodes"] == 1 and counts["next_edges"] == 1


def test_search_reveal_can_start_at_a_protected_edge_endpoint():
    source = {
        "nodes": [{"data": {"id": key}} for key in ("root", "a", "b", "leaf")],
        "edges": [
            {"data": {"id": "pin", "source": "a", "target": "b"}},
            {"data": {"id": "detail", "source": "a", "target": "leaf"}},
        ],
    }
    controller = ExpansionController({"nodes": source["nodes"][:1], "edges": []})
    provider = InMemoryExpansionProvider(source)
    controller.update_records(source)
    controller.protect(["pin"])
    controller.expand("a", provider)
    controller.collapse(["a"])
    assert "leaf" not in ids(controller)
    controller.reveal("leaf")
    assert "leaf" in ids(controller)


def test_bad_provider_identity_and_duplicate_event_retry_are_safe():
    controller, provider = setup()

    class WrongIdentity:
        def expand(self, request):
            return ExpansionResponse("wrong", {"nodes": [], "edges": []})

    assert not controller.expand("ABC123", WrongIdentity())
    assert controller.describe()["nodes"]["ABC123"]["error"]
    event = {
        "action": "expansion",
        "data": {"operation": "retry", "node_ids": ["ABC123"], "request_id": "retry"},
    }
    controller.handle_event(event, provider)
    controller.handle_event(event, provider)
    assert len(ids(controller)) == 3


@pytest.mark.parametrize(
    "position", [{"x": "bad", "y": 0}, {"x": 0}, {"x": float("nan"), "y": 0}, None]
)
def test_invalid_positions_never_change_the_last_valid_graph(position):
    controller, _ = setup()
    before = controller.view()
    request = controller.request("ABC123")
    with pytest.raises(ValueError):
        controller.apply_response(
            ExpansionResponse(
                request.request_id,
                {"nodes": [{"data": {"id": "new"}, "position": position}], "edges": []},
            )
        )
    assert controller.view() == before and controller.loaded() == before
    with pytest.raises(ValueError):
        controller.update_records(
            {"nodes": [{"data": {"id": "ABC123"}, "position": position}]}
        )
    assert controller.view() == before


def test_explicit_edge_edit_survives_collapse_and_reopen():
    controller, provider = opened()
    controller.update_records(
        {
            "nodes": [{"data": {"id": "new-target"}}],
            "edges": [
                {"data": {"id": "e-2", "source": "location-1", "target": "new-target"}}
            ],
        }
    )
    controller.collapse(["location-1"])
    controller.expand("location-1", provider)
    assert "new-target" in ids(controller)
    controller.collapse(["location-1"])
    controller.expand("location-1", provider, query={"direction": "outgoing"})
    assert "new-target" in ids(controller)
    assert (
        next(e for e in controller.view()["edges"] if e["data"]["id"] == "e-2")["data"][
            "target"
        ]
        == "new-target"
    )


def test_filtered_branch_identity_and_independent_edge_contributions():
    controller, provider = setup()
    first = {"direction": "outgoing", "relationships": ["LINK", "LINK"]}
    second = {"direction": "outgoing", "relationships": ["LINK"]}
    assert controller.branch_id("ABC123", first) == controller.branch_id(
        "ABC123", second
    )
    controller.expand("ABC123", provider)
    controller.expand("ABC123", provider, query=first)
    controller.collapse(branch_id=controller.branch_id("ABC123"))
    assert len(controller.view()["edges"]) == 2
    assert all(
        row["retained_by"] == ["ABC123"]
        for row in controller.changes
        if row["kind"] == "edge"
    )
    controller.collapse(branch_id=controller.branch_id("ABC123", first))
    assert not controller.view()["edges"]


@pytest.mark.parametrize(
    "kwargs",
    [{"page_size": 0}, {"max_depth": True}, {"max_nodes": -1}, {"max_edges": 2.5}],
)
def test_limits_are_finite_positive_integers(kwargs):
    with pytest.raises(ValueError):
        ExpansionConfig(**kwargs)


@pytest.mark.parametrize("identity", [True, 1, 1.0, 2.5])
def test_scalar_ids_and_optional_groups_follow_existing_contract(identity):
    source = {"nodes": [{"data": {"id": identity}}]}
    controller = ExpansionController(source)
    provider = InMemoryExpansionProvider(source)
    assert controller.view() == {
        "nodes": [{"data": {"id": str(identity)}}],
        "edges": [],
    }
    assert controller.expand(identity, provider)
    assert ExpansionController({}).view() == {"nodes": [], "edges": []}


@pytest.mark.parametrize("parent", [None, ""])
def test_empty_optional_parent_is_not_a_structural_id(parent):
    source = {"nodes": [{"data": {"id": "root", "parent": parent}}]}
    controller = ExpansionController(source)
    assert controller.view()["nodes"][0]["data"] == {"id": "root"}
    assert source["nodes"][0]["data"]["parent"] == parent


def test_snapshot_preserves_current_starting_edges_and_compound_context():
    controller = ExpansionController(
        {
            "nodes": [{"data": {"id": "a"}}, {"data": {"id": "b"}}],
            "edges": [{"data": {"id": "ab", "source": "a", "target": "b"}}],
        }
    )
    controller.update_records(
        {
            "nodes": [
                {"data": {"id": "group"}},
                {"data": {"id": "c", "parent": "group"}},
            ],
            "edges": [{"data": {"id": "ab", "source": "a", "target": "c"}}],
        }
    )
    controller.delete_records(["b"])
    restored = ExpansionController.restore(controller.snapshot(), source_version="1")
    assert restored.view() == controller.view()
    assert ids(restored) == {"a", "c", "group"}


def test_branch_identity_takes_precedence_over_its_node_selection():
    controller, provider = setup()
    controller.expand("ABC123", provider)
    controller.expand("ABC123", provider, query={"direction": "outgoing"})
    controller.collapse(
        ["ABC123"], branch_id=controller.branch_id("ABC123", {"direction": "outgoing"})
    )
    states = {
        row["query"]["direction"]: row["opened"]
        for row in controller.describe()["branches"]
    }
    assert states == {"both": True, "outgoing": False}


@pytest.mark.parametrize("mask", ["hidden", "filtered"])
def test_hidden_then_restored_anchors_reject_old_pending_results(mask):
    controller, provider = setup()
    request = controller.request("ABC123")
    response = provider.expand(request)
    controller.set_visibility(**{mask: ["ABC123"]})
    controller.set_visibility(**{mask: []})
    assert not controller.apply_response(response)
    assert controller.expand("ABC123", provider)


@pytest.mark.parametrize("change", ["delete", "rewire"])
def test_source_reveal_respects_current_edge_edits_and_deletions(change):
    controller, provider = setup()
    controller.expand("ABC123", provider)
    result = provider.search("location-1", roots=["ABC123"])
    if change == "delete":
        controller.delete_records(["e-0"])
    else:
        controller.update_records(
            {
                "edges": [
                    {"data": {"id": "e-0", "source": "ABC123", "target": "location-2"}}
                ]
            }
        )
    before = controller.snapshot()
    with pytest.raises(ValueError, match="missing relationship"):
        controller.reveal_search_result(result, "location-1")
    assert controller.snapshot() == before


@pytest.mark.parametrize("field", ["source_version", "source_dataset_id"])
def test_source_reveal_rejects_obsolete_search_provenance(field):
    controller, provider = setup()
    result = {**provider.search("location-1", roots=["ABC123"]), field: "obsolete"}
    before = controller.snapshot()
    with pytest.raises(ValueError, match="obsolete"):
        controller.reveal_search_result(result, "location-1")
    assert controller.snapshot() == before


@pytest.mark.parametrize(
    "query",
    [
        {"direction": []},
        {"time_field": ""},
        {"time_field": 42},
        {"time_from": "yesterday"},
        {"time_to": 1},
        {"time_from": "2026-01-02", "time_to": "2026-01-01"},
    ],
)
def test_invalid_filters_fail_before_requesting_or_cancelling_work(query):
    controller, provider = setup()
    pending = controller.request("ABC123")
    with pytest.raises(ValueError):
        controller.start_bulk(["ABC123"], query=query)
    assert controller.apply_response(provider.expand(pending))


def test_invalid_bulk_node_does_not_cancel_pending_work():
    controller, provider = setup()
    controller.expand("ABC123", provider)
    pending = controller.request("location-1")
    with pytest.raises(ValueError, match="starting nodes"):
        controller.start_bulk(["e-0"])
    assert controller.apply_response(provider.expand(pending))


def test_exact_null_filter_does_not_match_missing_attributes():
    source = graph()
    source["nodes"][1]["data"]["status"] = None
    provider = InMemoryExpansionProvider(source)
    controller, _ = setup()
    controller.expand("ABC123", provider, query={"attributes": {"status": None}})
    assert ids(controller) == {"ABC123", "location-1"}


@pytest.mark.parametrize("limit", [0, -1, True, 2.5, "3"])
def test_provider_limits_require_positive_integers(limit):
    controller, provider = setup()
    request = replace(controller.request("ABC123"), limit=limit)
    with pytest.raises(ValueError, match="positive integer"):
        provider.expand(request)
    with pytest.raises(ValueError, match="positive integer"):
        provider.search("location", roots=["ABC123"], limit=limit)


def test_description_indexes_preserve_order_detachment_and_cache_updates():
    controller, provider = opened()
    before = controller.view()
    loaded = controller.loaded()
    description = controller.describe(provider)
    assert controller.view() == before
    assert controller.loaded() == loaded
    description["loaded"]["nodes"][0]["data"]["name"] = "External mutation"
    assert controller.loaded() == loaded
    controller.update_records(
        {"nodes": [{"data": {"id": "ABC123", "name": "Updated"}}]}
    )
    assert (
        controller.describe(provider)["loaded"]["nodes"][0]["data"]["name"] == "Updated"
    )
    controller.delete_records(["camera-1"])
    assert "camera-1" not in controller.describe(provider)["nodes"]


def test_filtered_branch_failures_are_visible_and_retry_clears_them():
    controller, provider = setup()
    query = {"direction": "outgoing"}
    request = controller.request("ABC123", query=query)
    controller.fail(request.request_id, "Source temporarily unavailable")
    assert (
        controller.describe(provider)["nodes"]["ABC123"]["error"]
        == "Source temporarily unavailable"
    )
    assert controller.expand("ABC123", provider, query=query, more=True)
    assert controller.describe(provider)["nodes"]["ABC123"]["error"] is None


def test_repeated_source_analysis_retains_request_identity():
    class Provider(InMemoryExpansionProvider):
        def analyze(self, request):
            return {"analysis": "degree", "node_id": "ABC123", "degree": 2}

    controller, _ = setup()
    provider = Provider(graph())
    results = []
    for identity in ("first-analysis", "second-analysis"):
        event = {
            "action": "expansion",
            "data": {"operation": "analyze", "request_id": identity},
        }
        controller.handle_event(event, provider)
        result = controller.describe(provider)["analysis_result"]
        assert result["request_id"] == identity
        results.append(result)
        controller.handle_event(event, provider)
        assert controller.describe(provider)["analysis_result"] == result
    assert {k: v for k, v in results[0].items() if k != "request_id"} == {
        k: v for k, v in results[1].items() if k != "request_id"
    }
