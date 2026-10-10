"""In-process pub/sub event bus (§1.3 observability).

Events are typed dicts with an ``event`` name and structured payload; the
orchestrator, agents and UI API subscribe without coupling to each other.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from av_editor.logging import get_logger

log = get_logger("av_editor.events")

Listener = Callable[[str, dict[str, Any]], None]


class EventBus:
    def __init__(self) -> None:
        self._listeners: dict[str, list[Listener]] = defaultdict(list)
        self._lock = threading.RLock()
        self.history: list[dict[str, Any]] = []
        # Bounded history: an unbounded list is a memory leak for long runs.
        self._history_limit = 10_000

    def subscribe(self, pattern: str, listener: Listener) -> Callable[[], None]:
        """Pattern is an exact event name or ``*`` for all events.

        Returns an unsubscribe callable so listeners can be torn down without
        leaking references (e.g. per-run UI subscribers).
        """
        with self._lock:
            self._listeners[pattern].append(listener)

        def unsubscribe() -> None:
            with self._lock:
                try:
                    self._listeners[pattern].remove(listener)
                except ValueError:
                    pass

        return unsubscribe

    def publish(self, event: str, **payload: Any) -> None:
        record = {"event": event, **payload}
        with self._lock:
            self.history.append(record)
            if len(self.history) > self._history_limit:
                del self.history[: len(self.history) - self._history_limit]
            listeners = list(self._listeners.get(event, ())) + list(self._listeners.get("*", ()))
        for fn in listeners:
            try:
                fn(event, payload)
            except Exception as exc:  # a broken listener must never break the pipeline
                log.error("listener_failed", event=event, error=str(exc))

    def recent(self, n: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(self.history[-n:])
