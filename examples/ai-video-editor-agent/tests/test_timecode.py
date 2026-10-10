"""Tests for timecode conversions (core/timecode.py)."""

from __future__ import annotations

import pytest

from av_editor.core.timecode import (
    Timebase,
    frames_between,
    frames_to_seconds,
    frames_to_timecode,
    parse_ffmpeg_time,
    seconds_to_ffmpeg_time,
    seconds_to_frames,
    snap_to_frame,
    timecode_to_frames,
)

TB30 = Timebase(30, 1)
TB2997 = Timebase(30000, 1001)
TB23976 = Timebase(24000, 1001)


class TestTimebase:
    def test_from_float_snaps_ntsc(self):
        assert Timebase.from_float(29.97) == TB2997
        assert Timebase.from_float(23.976) == TB23976

    def test_from_float_generic(self):
        tb = Timebase.from_float(48.0)
        assert tb.fps == pytest.approx(48.0)


class TestFrameSecondRoundtrip:
    @pytest.mark.parametrize("tb", [TB30, TB2997, TB23976])
    def test_roundtrip(self, tb: Timebase):
        for frame in (0, 1, 29, 30, 179_999, 360_000):
            t = frames_to_seconds(frame, tb)
            assert seconds_to_frames(t, tb) == frame

    def test_half_up_rounding(self):
        assert seconds_to_frames(1.0 / 30 + 0.01, TB30) == 1
        assert seconds_to_frames(-0.02, TB30) == -1


class TestNonDropTimecode:
    def test_basic(self):
        assert frames_to_timecode(0, TB30) == "00:00:00:00"
        assert frames_to_timecode(30, TB30) == "00:00:01:00"
        assert frames_to_timecode(31, TB30) == "00:00:01:01"
        assert frames_to_timecode(30 * 61, TB30) == "00:01:01:00"
        assert frames_to_timecode(30 * 3661 + 5, TB30) == "01:01:01:05"

    def test_parse(self):
        assert timecode_to_frames("00:00:01:00", TB30) == 30
        assert timecode_to_frames("01:01:01:05", TB30) == 30 * 3661 + 5

    def test_frame_field_range_enforced(self):
        with pytest.raises(ValueError):
            timecode_to_frames("00:00:00:30", TB30)

    def test_fractional_rate_uses_nominal(self):
        # FF field must stay within 0..round(fps)-1 even at 29.97.
        tc = frames_to_timecode(100, TB2997)
        ff = int(tc.split(":")[-1])
        assert 0 <= ff < 30


class TestDropFrameTimecode:
    def test_canonical_one_minute(self):
        # SMPTE example: real frame 17982 at 29.97 DF is exactly 00;01;00.
        assert frames_to_timecode(17982, TB2997, drop=True) == "00:01;00"
        assert timecode_to_frames("00:01;00", TB2997) == 17982

    def test_canonical_ten_minutes(self):
        # 10 minutes of real frames at 29.97 -> 00:10:00;00 display.
        assert frames_to_timecode(17982 * 10, TB2997, drop=True) == "00:10:00;00"
        assert timecode_to_frames("00:10:00;00", TB2997) == 17982 * 10

    def test_zero(self):
        assert frames_to_timecode(0, TB2997, drop=True) == "00:00:00;00"

    @pytest.mark.parametrize("frame", [0, 1, 17981, 17982, 17983, 179_820, 1_000_003])
    def test_df_roundtrip(self, frame: int):
        tc = frames_to_timecode(frame, TB2997, drop=True)
        assert ";" in tc
        assert timecode_to_frames(tc, TB2997) == frame

    def test_wallclock_accuracy(self):
        # DF timecode tracks wall clock: after ~1 hour the displayed HH:MM:SS
        # should match the real elapsed time (non-drop drifts ~3.6 s/hour).
        one_hour_frames = seconds_to_frames(3600.0, TB2997)
        tc = frames_to_timecode(one_hour_frames, TB2997, drop=True)
        assert tc.startswith("01:00:00;")


class TestFfmpegTime:
    def test_format(self):
        assert seconds_to_ffmpeg_time(0) == "00:00:00.000"
        assert seconds_to_ffmpeg_time(3661.5) == "01:01:01.500"

    def test_negative_rejected(self):
        with pytest.raises(ValueError):
            seconds_to_ffmpeg_time(-0.001)

    @pytest.mark.parametrize("value,expected", [
        ("00:00:01.500", 1.5),
        ("01:01:01", 3661.0),
        ("01:30", 90.0),
        ("12.5", 12.5),
        ("12.5s", 12.5),
        ("12.5S", 12.5),
    ])
    def test_parse(self, value: str, expected: float):
        assert parse_ffmpeg_time(value) == pytest.approx(expected)

    def test_parse_bad(self):
        with pytest.raises(ValueError):
            parse_ffmpeg_time("a:b:c:d")


class TestSnapAndBetween:
    def test_snap(self):
        snapped = snap_to_frame(1.0 / 30 + 0.01, TB30)
        assert seconds_to_frames(snapped, TB30) == 1

    def test_frames_between(self):
        assert frames_between(1.0, 2.0, TB30) == 30
