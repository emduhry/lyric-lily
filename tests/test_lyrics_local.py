from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from lyric_lily.lyrics import resolve_lyrics
from lyric_lily.now_playing.types import PlaybackSnapshot, PlayState

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "lucki-rip.lrc"


@pytest.fixture
def lucki_snap_with_local_lrc(tmp_path, monkeypatch: pytest.MonkeyPatch) -> PlaybackSnapshot:
    monkeypatch.chdir(tmp_path)
    lyrics = tmp_path / "lyrics"
    lyrics.mkdir()
    shutil.copy(_FIXTURE, lyrics / "LUCKI - RIP.lrc")
    return PlaybackSnapshot(
        title="RIP",
        artist="LUCKI",
        album="GEMINI!",
        position_sec=40.0,
        duration_sec=123.4,
        state=PlayState.PLAYING,
        player_name="spotify",
    )


def test_local_lrc_used_when_local_only(lucki_snap_with_local_lrc: PlaybackSnapshot) -> None:
    r = resolve_lyrics(lucki_snap_with_local_lrc, local_only=True)
    assert r.found
    assert "local file" in r.headline
    assert r.lrc_text and "LOCAL_FIXTURE" in r.lrc_text


def test_local_lrc_preferred_before_remote(
    lucki_snap_with_local_lrc: PlaybackSnapshot,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[str] = []

    def _boom(term: str) -> tuple[str, str]:
        called.append(term)
        raise AssertionError("remote fetch must not run when a local .lrc matches")

    monkeypatch.setattr("lyric_lily.lyrics.resolver.fetch_remote_lrc", _boom)
    r = resolve_lyrics(lucki_snap_with_local_lrc, local_only=False)
    assert r.found
    assert "local file" in r.headline
    assert r.lrc_text and "LOCAL_FIXTURE" in r.lrc_text
    assert called == []


def test_spotify_advertisement_skips_lyric_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    snap = PlaybackSnapshot(
        title="Advertisement",
        artist="Spotify",
        album=None,
        position_sec=12.0,
        duration_sec=30.0,
        state=PlayState.PLAYING,
        player_name="spotify",
        track_id="spotify:ad:12345",
        source_url="spotify:ad:12345",
    )
    called: list[str] = []

    def _boom(term: str) -> tuple[str, str]:
        called.append(term)
        raise AssertionError("remote fetch must not run for Spotify ads")

    monkeypatch.setattr("lyric_lily.lyrics.resolver.fetch_remote_lrc", _boom)
    r = resolve_lyrics(snap, local_only=False)
    assert not r.found
    assert "Skipping lyric lookup" in r.headline
    assert called == []
