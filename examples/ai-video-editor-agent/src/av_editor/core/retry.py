"""Retry logic with exponential backoff and jitter for idempotent operations (§6.5)."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import TypeVar

from av_editor.logging import get_logger

log = get_logger("av_editor.retry")

T = TypeVar("T")


class RetryExhausted(Exception):
    """Raised when all retry attempts fail; carries the last underlying error."""

    def __init__(self, attempts: int, last_error: BaseException) -> None:
        super().__init__(f"Retry exhausted after {attempts} attempts: {last_error}")
        self.attempts = attempts
        self.last_error = last_error


def retry_with_backoff(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    jitter: bool = True,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    op_name: str = "operation",
) -> T:
    """Run ``fn`` with capped exponential backoff. Deterministic ordering is the
    caller's responsibility; only side-effect-free/idempotent work should use it."""
    delay = base_delay
    last: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except retry_on as exc:
            last = exc
            if attempt == attempts:
                break
            sleep_for = min(delay, max_delay)
            if jitter:
                sleep_for *= 0.5 + random.random()  # deterministic RNG seeded upstream
            log.warning("retry_attempt", op=op_name, attempt=attempt,
                        error=str(exc), sleep_s=round(sleep_for, 3))
            time.sleep(sleep_for)
            delay *= 2
    assert last is not None
    raise RetryExhausted(attempts, last)
