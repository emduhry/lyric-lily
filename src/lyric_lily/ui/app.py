from __future__ import annotations

import os
from typing import ClassVar

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.widgets import Footer, Static

from lyric_lily.lyrics import resolve_lyrics
from lyric_lily.lyrics.types import LyricResolveResult
from lyric_lily.lrc_sync import line_index_at, parse_synced_lrc
from lyric_lily.now_playing import (
    NowPlayingBackend,
    PlaybackUnavailableError,
    PlaybackSnapshot,
    default_backend,
)


def run_ui(*, local_only: bool) -> int:
    LyricLilyApp(local_only=local_only).run()
    return 0


class LyricLilyApp(App[None]):
    """Minimal synced-lyrics view: poll playerctl, resolve LRC, highlight active line."""

    TITLE = "lyric-lily"
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "Quit"),
    ]

    CSS = """
    Screen { align: center middle; }
    #panel {
        width: 90%;
        max-width: 100;
        height: 90%;
        border: round $accent;
        padding: 1 2;
        background: $surface;
    }
    #meta { margin-bottom: 1; color: $text-muted; }
    #source { margin-top: 1; color: $text-muted; height: auto; }
    #error { color: $error; margin-bottom: 1; }
    """

    def __init__(self, *, local_only: bool) -> None:
        super().__init__()
        self._local_only = local_only
        self._backend: NowPlayingBackend | None = None
        self._backend_error: str | None = None
        self._track_key: tuple[str | None, str | None] | None = None
        self._resolve: LyricResolveResult | None = None
        self._lines: list[tuple[float, str]] = []
        self._last_snap: PlaybackSnapshot | None = None
        self._last_error: str | None = None

    def compose(self) -> ComposeResult:
        with Container(id="panel"):
            yield Static("", id="error")
            yield Static("", id="meta")
            with VerticalScroll(id="scroll"):
                yield Static("", id="lyrics")
            yield Static("", id="source")
        yield Footer()

    def on_mount(self) -> None:
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

        self._last_error = None
        self._last_snap = snap
        key = (snap.artist, snap.title)
        if key != self._track_key:
            self._track_key = key
            self._resolve = resolve_lyrics(snap, local_only=self._local_only)
            if self._resolve.found and self._resolve.lrc_text:
                self._lines = parse_synced_lrc(self._resolve.lrc_text)
            else:
                self._lines = []
        self._apply_lyrics(snap)

    def _apply_error_only(self) -> None:
        err = self.query_one("#error", Static)
        meta = self.query_one("#meta", Static)
        lyrics = self.query_one("#lyrics", Static)
        src = self.query_one("#source", Static)
        if self._last_error:
            err.update(self._last_error)
            meta.update("")
            lyrics.update("")
            src.update("")

    def _apply_lyrics(self, snap: PlaybackSnapshot) -> None:
        err = self.query_one("#error", Static)
        meta = self.query_one("#meta", Static)
        lyrics = self.query_one("#lyrics", Static)
        src = self.query_one("#source", Static)
        err.update("")

        bits = [snap.state.value.upper()]
        if snap.artist:
            bits.append(snap.artist)
        if snap.title:
            bits.append(snap.title)
        pos = f"{snap.position_sec:.1f}s"
        if snap.duration_sec is not None:
            pos += f" / {snap.duration_sec:.1f}s"
        bits.append(pos)
        meta.update(" · ".join(bits))

        res = self._resolve
        if not res:
            lyrics.update("")
            src.update("")
            return

        src.update(res.headline + "\n" + res.detail)

        if not res.found or not res.lrc_text:
            lyrics.update(Text(res.headline, style="yellow"))
            return

        if not self._lines:
            lyrics.update(
                Text(
                    "Lyrics file had no parseable synced [mm:ss] lines.",
                    style="yellow",
                )
            )
            return

        idx = line_index_at(self._lines, snap.position_sec)
        text = Text()
        margin = 6
        if idx < 0:
            start, end = 0, min(len(self._lines), 2 * margin + 1)
            active = -1
        else:
            start = max(0, idx - margin)
            end = min(len(self._lines), idx + margin + 1)
            active = idx
        for j in range(start, end):
            _, line = self._lines[j]
            if j == active:
                text.append(line + "\n", style="bold bright_magenta")
            else:
                text.append(line + "\n", style="dim")
        lyrics.update(text)

    def action_quit(self) -> None:
        self.exit()
