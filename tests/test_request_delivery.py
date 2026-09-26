"""Persistent Components v2 requests survive reruns without duplicate callbacks."""

import pytest
from st_graph_workbench.component import component
from st_graph_workbench import ExpansionController, add_elements_command


@pytest.fixture
def bridge(monkeypatch):
    state, calls = {}, []
    monkeypatch.setattr(component.st, "session_state", state)
    monkeypatch.setattr(
        component, "_component_func", lambda **kwargs: calls.append(kwargs)
    )
    return state, calls


def event(identity, action="expansion"):
    return {
        "action": action,
        "data": {"request_id": identity, "operation": "expand"},
        "timestamp": 1,
    }


def render(callback=None):
    return component.graph_workbench(
        {"nodes": [{"data": {"id": "a"}}], "edges": []},
        key="delivery",
        on_change=callback,
    )


def test_requests_are_deduplicated_and_receipts_are_explicit(bridge):
    state, calls = bridge
    seen = []

    def callback():
        seen.append(state["delivery"])

    render(callback)
    call = calls[-1]
    state[call["key"]] = {"requests": [event("one"), event("two", "load_more")]}
    call["on_requests_change"]()
    call["on_requests_change"]()
    assert [e["data"]["request_id"] for e in seen] == ["one", "two"]
    render(callback)
    assert calls[-1]["data"]["receivedRequestIds"] == ["one", "two"]


def test_return_only_consumers_receive_each_request(bridge):
    state, calls = bridge
    render()
    call = calls[-1]
    state[call["key"]] = {"requests": [event("one"), event("two")]}
    call["on_requests_change"]()
    assert render()["data"]["request_id"] == "one"
    calls[-1]["on_requests_change"]()
    assert render()["data"]["request_id"] == "two"


def test_failed_handler_does_not_acknowledge_unprocessed_request(bridge):
    state, calls = bridge

    def fail():
        raise RuntimeError("try again")

    render(fail)
    call = calls[-1]
    state[call["key"]] = {"requests": [event("one")]}
    with pytest.raises(RuntimeError):
        call["on_requests_change"]()
    render()
    assert calls[-1]["data"]["receivedRequestIds"] == []


def test_managed_commands_remain_pending_until_browser_ack(bridge):
    state, calls = bridge
    controller = ExpansionController({"nodes": [{"data": {"id": "a"}}], "edges": []})
    command = add_elements_command("batch", nodes=[{"data": {"id": "b"}}])

    def draw(commands):
        component.graph_workbench(
            controller.view(),
            key="queued",
            expansion=controller.describe(),
            graph_commands=commands,
        )

    draw([command])
    draw([])
    assert calls[-1]["data"]["graphCommands"] == [command]
    call = calls[-1]
    state[call["key"]] = {"command_receipts": ["batch"]}
    call["on_command_receipts_change"]()
    draw([command])
    assert calls[-1]["data"]["graphCommands"] == []


def test_incomplete_managed_configuration_fails_before_browser_render(bridge):
    with pytest.raises(ValueError, match="controller_id"):
        component.graph_workbench(
            {"nodes": [], "edges": []}, key="bad", expansion={"nodes": {}}
        )
    assert not bridge[1]


def test_successful_requests_stay_acknowledged_when_a_later_handler_fails(bridge):
    state, calls = bridge
    seen = []
    fail_second = True

    def callback():
        identity = state["delivery"]["data"]["request_id"]
        if identity == "two" and fail_second:
            raise RuntimeError("retry second request")
        seen.append(identity)

    render(callback)
    call = calls[-1]
    state[call["key"]] = {"requests": [event("one"), event("two")]}
    with pytest.raises(RuntimeError):
        call["on_requests_change"]()
    fail_second = False
    call["on_requests_change"]()
    assert seen == ["one", "two"]


def test_long_inflight_queue_does_not_replay_evicted_receipts(bridge):
    state, calls = bridge
    seen = []
    render(lambda: seen.append(state["delivery"]["data"]["request_id"]))
    call = calls[-1]
    queued = [event(str(i)) for i in range(300)]
    state[call["key"]] = {"requests": queued}
    call["on_requests_change"]()
    call["on_requests_change"]()
    assert seen == [str(i) for i in range(300)]
    render()
    assert len(calls[-1]["data"]["receivedRequestIds"]) == 300
    state[call["key"]] = {"requests": []}
    call["on_requests_change"]()
    render()
    assert len(calls[-1]["data"]["receivedRequestIds"]) == 256


def test_malformed_requests_do_not_block_the_valid_queue(bridge):
    state, calls = bridge
    seen = []
    render(lambda: seen.append(state["delivery"]["data"]["request_id"]))
    call = calls[-1]
    state[call["key"]] = {
        "requests": [
            None,
            {"action": "expansion", "data": None},
            event(""),
            event("valid"),
        ]
    }
    call["on_requests_change"]()
    assert seen == ["valid"]
