from __future__ import annotations

import os
import time
from dataclasses import replace
from typing import ClassVar

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Footer, Static

from lyric_lily.lyrics import resolve_lyrics
from lyric_lily.lyrics.types import LyricResolveResult
from lyric_lily.lrc_sync import line_index_at, parse_synced_lrc
from lyric_lily.now_playing import (
    NowPlayingBackend,
    PlaybackUnavailableError,
    PlaybackSnapshot,
    PlayState,
    default_backend,
)
from lyric_lily.ui.lyric_view import LyricView
from lyric_lily.themes import ThemePalette, load_theme


def run_ui(*, local_only: bool, sync_offset_sec: float = 0.0, theme_name: str | None = None) -> int:
    theme = load_theme(theme_name)
    LyricLilyApp(local_only=local_only, sync_offset_sec=sync_offset_sec, theme=theme).run()
    return 0


class LyricLilyApp(App[None]):
    """Minimal synced-lyrics view: poll playerctl, resolve LRC, highlight active line."""

    TITLE = "lyric-lily"
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "Quit"),
    ]

    CSS = """
    Screen {
        align: center middle;
        background: transparent;
    }
    #panel {
        width: 90%;
        max-width: 100;
        height: auto;
        max-height: 90%;
        padding: 1 3;
        background: transparent;
    }
    #meta { margin-bottom: 2; }
    #lyrics { height: auto; }
    #source { margin-top: 1; height: 1; }
    #error { color: $error; margin-bottom: 1; }
    """

    def __init__(self, *, local_only: bool, sync_offset_sec: float = 0.0, theme: ThemePalette) -> None:
        super().__init__()
        self._local_only = local_only
        self._sync_offset_sec = sync_offset_sec
        self._theme = theme
        self._backend: NowPlayingBackend | None = None
        self._backend_error: str | None = None
        self._track_key: tuple[str | None, str | None, str | None, str | None] | str | None = None
        self._resolve: LyricResolveResult | None = None
        self._lines: list[tuple[float, str]] = []
        self._last_snap: PlaybackSnapshot | None = None
        self._last_error: str | None = None
        self._clock_key: tuple[str | None, str | None] | None = None
        self._clock_position_sec: float = 0.0
        self._clock_seen_at: float | None = None
        self._clock_reported_position_sec: float | None = None
        self._clock_estimated: bool = False

    def compose(self) -> ComposeResult:
        with Container(id="panel"):
            yield Static("", id="error")
            yield Static("", id="meta")
            yield LyricView(id="lyrics", theme=self._theme)
            yield Static("", id="source")
        yield Footer()

    def on_mount(self) -> None:
        self.screen.styles.background = self._theme.background
        self.query_one("#panel", Container).styles.background = self._theme.background
        try:
            self._backend = default_backend()
        except NotImplementedError as e:
            self._backend_error = str(e)
            self.query_one("#error", Static).update(self._backend_error)
            return

        hz = float(os.environ.get("LYRIC_LILY_UI_POLL_HZ", "5") or "5")
        interval = max(0.05, 1.0 / min(30.0, hz))
        self.set_interval(interval, self._tick)

    def _tick(self) -> None:
        if self._backend is None:
            return
        try:
            snap = self._backend.read()
        except PlaybackUnavailableError as e:
            self._last_error = str(e)
            self._last_snap = None
            self._apply_error_only()
            return
        except Exception as e:
            self._last_error = f"Could not read playback state: {type(e).__name__}: {e}"
            self._last_snap = None
            self._apply_error_only()
            return

        snap = self._with_local_position_clock(snap)
        self._last_error = None
        self._last_snap = snap
        key = playback_track_key(snap)
        if key != self._track_key:
            self._track_key = key
            self._resolve = resolve_lyrics(snap, local_only=self._local_only)
            if self._resolve.found and self._resolve.lrc_text:
                self._lines = parse_synced_lrc(self._resolve.lrc_text)
            else:
                self._lines = []
            self.query_one("#lyrics", LyricView).set_lines(self._lines)
            try:
                fresh_snap = self._backend.read()
            except PlaybackUnavailableError:
                pass
            else:
                if playback_track_key(fresh_snap) == key:
                    fresh_snap = self._with_local_position_clock(fresh_snap)
                    snap = fresh_snap
                    self._last_snap = fresh_snap
        self._apply_lyrics(snap)

    def _with_local_position_clock(self, snap: PlaybackSnapshot) -> PlaybackSnapshot:
        """Keep lyrics moving when an MPRIS player reports a stuck position.

        Some clients keep title/artist updated but report ``Stopped`` and ``0.0``
        for position while playback is actually progressing. The backend remains
        faithful to playerctl; the UI layers on a best-effort clock so synced
        lyrics do not freeze at the first lines.
        """

        key = (snap.artist, snap.title)
        now = time.monotonic()
        if key != self._clock_key:
            self._clock_key = key
            self._clock_position_sec = max(0.0, snap.position_sec)
            self._clock_seen_at = now
            self._clock_reported_position_sec = snap.position_sec
            self._clock_estimated = False
            return snap

        previous_seen_at = self._clock_seen_at
        previous_reported = self._clock_reported_position_sec
        self._clock_seen_at = now
        self._clock_reported_position_sec = snap.position_sec

        if snap.state == PlayState.PAUSED:
            self._clock_position_sec = max(0.0, snap.position_sec)
            self._clock_estimated = False
            return snap

        elapsed = max(0.0, now - previous_seen_at) if previous_seen_at is not None else 0.0
        has_track = bool(snap.artist or snap.title)
        may_be_playing = snap.state in {PlayState.PLAYING, PlayState.UNKNOWN} or (
            snap.state == PlayState.STOPPED and has_track
        )

        if not may_be_playing:
            self._clock_position_sec = max(0.0, snap.position_sec)
            self._clock_estimated = False
            return snap

        reported_moved = (
            previous_reported is None
            or abs(snap.position_sec - previous_reported) > max(0.05, elapsed * 0.25)
            or snap.position_sec > self._clock_position_sec + 0.05
        )
        if reported_moved:
            self._clock_position_sec = max(0.0, snap.position_sec)
            self._clock_estimated = False
            return snap

        self._clock_position_sec += elapsed
        if snap.duration_sec is not None:
            self._clock_position_sec = min(self._clock_position_sec, snap.duration_sec)
        self._clock_estimated = True
        return replace(snap, position_sec=self._clock_position_sec)

    def _apply_error_only(self) -> None:
        err = self.query_one("#error", Static)
        meta = self.query_one("#meta", Static)
        lyrics = self.query_one("#lyrics", LyricView)
        src = self.query_one("#source", Static)
        if self._last_error:
            err.update(self._last_error)
            meta.update("")
            lyrics.show_message(self._last_error)
            src.update("")

    def _apply_lyrics(self, snap: PlaybackSnapshot) -> None:
        err = self.query_one("#error", Static)
        meta = self.query_one("#meta", Static)
        lyrics = self.query_one("#lyrics", LyricView)
        src = self.query_one("#source", Static)
        err.update("")

        bits = []
        if snap.artist:
            bits.append(snap.artist)
        if snap.title:
            bits.append(snap.title)
        adjusted_position_sec = max(0.0, snap.position_sec + self._sync_offset_sec)
        pos = f"{snap.position_sec:.1f}s"
        if snap.duration_sec is not None:
            pos += f" / {snap.duration_sec:.1f}s"
        if self._sync_offset_sec:
            pos += f" (lyrics {adjusted_position_sec:.1f}s)"
        state_label = "playing" if self._clock_estimated and snap.state == PlayState.STOPPED else snap.state.value
        bits.append(f"{state_label} · {pos}")
        meta.update(Text(" · ".join(bits), style=self._theme.meta))

        res = self._resolve
        if not res:
            lyrics.show_message("")
            src.update("")
            return

        src.update(Text(res.headline, style=self._theme.source))

        if not res.found or not res.lrc_text:
            lyrics.show_message(res.headline)
            return

        if not self._lines:
            lyrics.show_message("Lyrics file had no parseable synced [mm:ss] lines.")
            return

        idx = line_index_at(self._lines, adjusted_position_sec)
        lyrics.set_active(idx)

    def action_quit(self) -> None:
        self.exit()


def playback_track_key(
    snap: PlaybackSnapshot,
) -> tuple[str | None, str | None, str | None, str | None] | str | None:
    """
    Prefer stable backend identifiers when available so skips/ads/remasters do
    not get mistaken for the same track based only on title/artist text.
    """
    if snap.track_id:
        return f"track:{snap.track_id}"
    return (snap.player_name, snap.artist, snap.album, snap.title)
