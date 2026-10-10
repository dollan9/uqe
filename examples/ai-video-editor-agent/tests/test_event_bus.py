"""Tests for the pub/sub event bus (core/event_bus.py)."""

from __future__ import annotations

from av_editor.core.event_bus import EventBus


def test_publish_delivers_to_named_and_wildcard() -> None:
    bus = EventBus()
    seen: list[tuple[str, dict]] = []
    bus.subscribe("stage_done", lambda e, p: seen.append((e, p)))
    unsub_star = bus.subscribe("*", lambda e, p: seen.append(("wild:" + e, p)))
    bus.publish("stage_done", stage="cut")
    assert ("stage_done", {"stage": "cut"}) in seen
    assert ("wild:stage_done", {"stage": "cut"}) in seen

    # unsubscribe stops delivery
    unsub_star()
    seen.clear()
    bus.publish("stage_done", stage="qa")
    assert all(e != "wild:stage_done" for e, _ in seen)


def test_broken_listener_does_not_break_pipeline() -> None:
    bus = EventBus()
    good_calls: list[str] = []

    def bad(event: str, payload: dict) -> None:
        raise RuntimeError("boom")

    bus.subscribe("evt", bad)
    bus.subscribe("evt", lambda e, p: good_calls.append(e))
    bus.publish("evt")  # must not raise
    assert good_calls == ["evt"]


def test_history_is_bounded_and_recent_returns_tail() -> None:
    bus = EventBus()
    bus._history_limit = 10
    for i in range(25):
        bus.publish("tick", i=i)
    assert len(bus.history) == 10
    recent = bus.recent(3)
    assert [r["payload_i"] if "payload_i" in r else r["i"] for r in recent] == [22, 23, 24]
