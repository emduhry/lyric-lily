from __future__ import annotations

import pytest

from lyric_lily.main import _env_float
from lyric_lily.main import _sync_debug_table
from lyric_lily.now_playing.types import PlaybackSnapshot, PlayState


def test_env_float_uses_default_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LYRIC_LILY_SYNC_OFFSET_SEC", raising=False)
    assert _env_float("LYRIC_LILY_SYNC_OFFSET_SEC", 1.5) == 1.5


def test_env_float_parses_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LYRIC_LILY_SYNC_OFFSET_SEC", "-0.75")
    assert _env_float("LYRIC_LILY_SYNC_OFFSET_SEC", 0.0) == -0.75


def test_sync_debug_table_reports_active_and_next_lines() -> None:
    snap = PlaybackSnapshot(
        title="Song",
        artist="Artist",
        album=None,
        position_sec=5.0,
        duration_sec=10.0,
        state=PlayState.PLAYING,
        player_name="spotify",
    )
    table = _sync_debug_table(
        snap,
        "[00:01.00] one\n[00:05.00] two\n[00:08.00] three",
        sync_offset_sec=0.5,
    )
    rendered = "\n".join(str(cell) for column in table.columns for cell in column.cells)
    assert "5.000s" in rendered
    assert "5.500s" in rendered
    assert "1: [5.00s] two" in rendered
    assert "2: [8.00s] three" in rendered
