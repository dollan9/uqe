"""Timecode utilities: frame <-> seconds <-> SMPTE conversions.

Supports integer and fractional rates (29.97/23.976 style) with non-drop
SMPTE formatting, plus FFmpeg ``HH:MM:SS.mmm`` expressions used by FCPXML.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_TC_RE = re.compile(r"^(\d+):(\d{1,2}):(\d{1,2})(?:[.:](\d{1,3}))?$")
_SMPTE_RE = re.compile(r"^(\d+):(\d{2}):(\d{2}):(\d{2})$")     # non-drop HH:MM:SS:FF
_DF_RE = re.compile(r"^(\d+):(\d{2}):(\d{2});(\d{2})$")        # drop-frame HH:MM:SS;FF


@dataclass(frozen=True)
class Timebase:
    """A rational timebase, e.g. 30000/1001 for 29.97 fps."""

    numerator: int = 30000
    denominator: int = 1000

    @property
    def fps(self) -> float:
        return self.numerator / self.denominator

    @classmethod
    def from_float(cls, fps: float) -> "Timebase":
        # Snap common NTSC fractional rates exactly; otherwise use thousandths.
        known = {23.976: (24000, 1001), 24.0: (24, 1), 25.0: (25, 1), 29.97: (30000, 1001),
                 30.0: (30, 1), 48.0: (48, 1), 50.0: (50, 1), 59.94: (60000, 1001), 60.0: (60, 1)}
        for rate, (n, d) in known.items():
            if abs(fps - rate) < 0.01:
                return cls(n, d)
        return cls(int(round(fps * 1000)), 1000)


def frames_to_seconds(frame: int, tb: Timebase) -> float:
    return frame * tb.denominator / tb.numerator


def seconds_to_frames(t: float, tb: Timebase) -> int:
    """Round-half-away-from-zero frame mapping (frame-accurate conform)."""
    raw = t * tb.numerator / tb.denominator
    return int(raw + 0.5) if raw >= 0 else -int(-raw + 0.5)


def frames_to_timecode(frame: int, tb: Timebase, drop: bool = False) -> str:
    """SMPTE HH:MM:SS:FF (non-drop) or HH:MM:SS;FF (drop-frame approximation).

    Non-drop uses the nominal (rounded) frame rate so the FF field is always a
    valid frame index in ``0 .. round(fps)-1``. Fractional-rate timecodes are
    approximations of wall-clock time; exact conform should use frame numbers.
    Drop-frame uses the standard SMPTE offset formula for whole minutes.
    """
    nominal = round(tb.fps)
    if drop:
        # SMPTE drop-frame: the standard conversion maps a real frame count to
        # the DF display counter by adding back the dropped-frame offsets
        # (drop_frames per whole minute, except every 10th minute).
        drop_frames = nominal - int(tb.fps)  # 2 for 29.97, 4 for 59.94
        m = frame // (nominal * 60)          # whole minutes of real time
        adjusted = frame + drop_frames * (m - m // 10)
        total_seconds = adjusted // nominal
        ff = adjusted % nominal
    else:
        total_seconds = frame // nominal
        ff = frame % nominal
    h = total_seconds // 3600
    mi = (total_seconds % 3600) // 60
    s = total_seconds % 60
    sep = ";" if drop else ":"
    return f"{h:02d}:{mi:02d}:{s:02d}{sep}{int(ff):02d}"


def timecode_to_frames(tc: str, tb: Timebase) -> int:
    """Parse SMPTE ``HH:MM:SS:FF`` / ``HH:MM:SS;FF`` or ``HH:MM:SS(.mmm)`` to frames."""
    tc = tc.strip()
    nd = _SMPTE_RE.match(tc)
    if nd:
        nominal = round(tb.fps)
        h, mi, s, ff = (int(g) for g in nd.groups())
        if ff >= nominal:
            raise ValueError(f"Frame field {ff} out of range for {nominal} fps: {tc!r}")
        return (h * 3600 + mi * 60 + s) * nominal + ff
    df = _DF_RE.match(tc)
    if df:
        nominal = round(tb.fps)
        drop_frames = nominal - int(tb.fps)
        h, mi, s, ff = (int(g) for g in df.groups())
        if ff >= nominal:
            raise ValueError(f"Frame field {ff} out of range for {nominal} fps: {tc!r}")
        total_minutes = h * 60 + mi
        # Drop-frame display time -> real frame count (standard SMPTE conversion):
        # subtract the dropped frames accumulated over whole minutes, except
        # every 10th minute where no frames are dropped.
        return ((total_minutes * 60 + s) * nominal + ff) - drop_frames * (
            total_minutes - total_minutes // 10)
    m = _TC_RE.match(tc)
    if not m:
        raise ValueError(f"Unrecognized timecode: {tc!r}")
    h, mi, s, frac = m.group(1), m.group(2), m.group(3), m.group(4)
    frames = ((int(h) * 3600 + int(mi) * 60 + int(s)) * round(tb.fps))
    if frac is not None:
        frames += int(round(int(frac) / (10 ** len(frac)) * tb.fps))
    return int(frames)


def seconds_to_ffmpeg_time(t: float) -> str:
    """HH:MM:SS.mmm expression for FCPXML/FFmpeg (frame-accurate at source rate)."""
    if t < 0:
        raise ValueError("negative time")
    total_ms = int(round(t * 1000))
    h, rem = divmod(total_ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def parse_ffmpeg_time(value: str) -> float:
    """Parse ``HH:MM:SS(.mmm)``, ``SS(.mmm)`` or plain seconds to float."""
    value = value.strip()
    if value.upper().endswith("S") and ":" not in value:
        return float(value[:-1])
    parts = value.split(":")
    if len(parts) == 1:
        return float(parts[0])
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    raise ValueError(f"Cannot parse time expression: {value!r}")


def snap_to_frame(t: float, tb: Timebase) -> float:
    """Quantize a timestamp to the nearest exact frame boundary."""
    return frames_to_seconds(seconds_to_frames(t, tb), tb)


def frames_between(t0: float, t1: float, tb: Timebase) -> int:
    return seconds_to_frames(t1, tb) - seconds_to_frames(t0, tb)
