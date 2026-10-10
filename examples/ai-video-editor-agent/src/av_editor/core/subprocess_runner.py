"""Safe subprocess runner (§6.2).

Rules: ``shell=False``, explicit argument lists, hard timeouts, captured
stdout/stderr, structured errors, optional retry with exponential backoff for
idempotent commands. No user input is ever interpolated into a shell string —
this is the single choke point that prevents shell injection (§6.10).
"""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from av_editor.errors import AVEditorError
from av_editor.logging import get_logger

log = get_logger("av_editor.subprocess")


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    duration_s: float
    attempts: int = 1

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class SubprocessRunner:
    """Deterministic, auditable subprocess execution."""

    def __init__(self, *, default_timeout: float = 600.0, max_retries: int = 0,
                 backoff_base: float = 0.5, env_extra: dict[str, str] | None = None) -> None:
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.env_extra = env_extra or {}

    def which(self, binary: str) -> str | None:
        return shutil.which(binary)

    def require(self, binary: str, hint: str) -> str:
        path = self.which(binary)
        if path is None:
            raise AVEditorError(
                f"Required external binary '{binary}' not found on PATH.",
                binary=binary, remediation=hint)
        return path

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        retries: int | None = None,
        retry_on_failure: bool = False,
        cwd: Path | None = None,
        stdin_data: bytes | None = None,
        check: bool = True,
    ) -> CommandResult:
        """Execute an argv list safely.

        Args:
            argv: program + args; never a shell string.
            retries: number of *additional* attempts for idempotent commands.
            retry_on_failure: retry even on non-zero exit (only safe for
                idempotent read-only commands such as ffprobe).
        """
        argv_l = [str(a) for a in argv]
        if not argv_l:
            raise AVEditorError("Empty argv passed to SubprocessRunner.run")
        timeout = timeout if timeout is not None else self.default_timeout
        retries = self.max_retries if retries is None else retries
        last_err: Exception | None = None
        attempts = 0
        start = time.monotonic()
        while attempts <= retries:
            attempts += 1
            try:
                proc = subprocess.run(
                    argv_l,
                    shell=False,
                    capture_output=True,
                    timeout=timeout,
                    cwd=str(cwd) if cwd else None,
                    input=stdin_data,
                    env={**_base_env(), **self.env_extra},
                )
                result = CommandResult(
                    argv=tuple(argv_l),
                    returncode=proc.returncode,
                    stdout=proc.stdout.decode("utf-8", errors="replace"),
                    stderr=proc.stderr.decode("utf-8", errors="replace"),
                    duration_s=time.monotonic() - start,
                    attempts=attempts,
                )
                if check and not result.ok:
                    err = AVEditorError(
                        f"Command failed (exit {result.returncode}): {argv_l[0]}",
                        argv=argv_l[:4], stderr_tail=result.stderr[-800:],
                        attempts=attempts)
                    if retry_on_failure and attempts <= retries:
                        last_err = err
                        time.sleep(self.backoff_base * (2 ** (attempts - 1)))
                        continue
                    raise err
                return result
            except subprocess.TimeoutExpired as exc:
                err = AVEditorError(
                    f"Command timed out after {timeout}s: {argv_l[0]}",
                    argv=argv_l[:4], timeout=timeout)
                if attempts <= retries:
                    last_err = err
                    time.sleep(self.backoff_base * (2 ** (attempts - 1)))
                    continue
                raise err from exc
        assert last_err is not None
        raise last_err


_ENV_CACHE: dict[str, str] | None = None


def _base_env() -> dict[str, str]:
    global _ENV_CACHE
    if _ENV_CACHE is None:
        import os
        _ENV_CACHE = dict(os.environ)
    return _ENV_CACHE


DEFAULT_RUNNER = SubprocessRunner()
