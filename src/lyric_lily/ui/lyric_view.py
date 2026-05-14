from __future__ import annotations

import os

from rich.text import Text
from textual.containers import Vertical
from textual.geometry import Offset
from textual.widgets import Static

from lyric_lily.themes import BUILTIN_THEMES, DEFAULT_THEME, ThemePalette
from lyric_lily.ui.render import lyric_color_for_distance, visible_lyric_window

LyricLineData = tuple[float, str]

_DEFAULT_MARGIN = 6
_DEFAULT_LINE_HEIGHT = 2  # one row of text + one row of breathing space
_POP_DURATION_SEC = 0.18
_DANCE_INTERVAL_SEC = 0.12
_SNAP_DELTA_THRESHOLD = 4  # skip slide for jumps larger than this


def compute_slide_offset(
    previous_index: int,
    new_index: int,
    *,
    line_height: int = _DEFAULT_LINE_HEIGHT,
    snap_threshold: int = _SNAP_DELTA_THRESHOLD,
) -> int:
    """Return the y-offset to animate from (negative = slide up).

    Returns ``0`` for backward seeks, large jumps, or when no previous index
    exists, signalling the caller to snap without animating.
    """
    if previous_index < 0 or new_index < 0:
        return 0
    delta = new_index - previous_index
    if delta <= 0 or delta > snap_threshold:
        return 0
    return -delta * line_height


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off", ""}


class LyricLine(Static):
    """One lyric row with smooth color transitions and a brief 'pop' effect."""

    DEFAULT_CSS = """
    LyricLine {
        height: 2;
        width: 100%;
        content-align: left middle;
        background: transparent;
        color: rgb(74, 68, 84);
        padding: 0 0;
        transition: color 220ms in_out_cubic;
    }
    LyricLine.-active {
        text-style: bold;
    }
    LyricLine.-pop {
        color: rgb(255, 248, 252);
    }
    """

    def set_line(
        self,
        text: str,
        *,
        distance: int,
        active: bool,
        theme: ThemePalette,
        dance_phase: int = 0,
    ) -> None:
        rendered = (
            _render_dancing_text(text, theme=theme, phase=dance_phase)
            if active
            else Text(f"\n{text}")
        )
        self.update(rendered)
        self.set_class(active, "-active")
        # Drive the color via inline style so the CSS transition kicks in.
        self.styles.color = lyric_color_for_distance(distance, theme)

    def pop(self) -> None:
        """Briefly flash brighter to emphasise a newly active line."""
        self.add_class("-pop")
        self.set_timer(_POP_DURATION_SEC, lambda: self.remove_class("-pop"))


def _render_dancing_text(text: str, *, theme: ThemePalette, phase: int) -> Text:
    rendered = Text()
    echo = Text()
    for index, char in enumerate(text):
        beat = (index + phase) % 6
        if char.isspace():
            echo.append(char)
        elif beat == 0:
            echo.append(char, style=f"bold {theme.active_lyric}")
        elif beat in (1, 5):
            echo.append(char, style=f"bold {theme.near_lyric}")
        else:
            echo.append(" ")
    rendered.append_text(echo)
    rendered.append("\n")
    rendered.append(text, style=f"bold {theme.active_lyric}")
    return rendered


class LyricView(Vertical):
    """Vertical column of lyric rows with active-line letter shimmer.

    The widget keeps a fixed pool of ``LyricLine`` rows mounted, then updates
    each row's text + distance on every ``set_active`` call. The pool stays
    stable so Textual's CSS color transitions can animate between states.
    """

    DEFAULT_CSS = """
    LyricView {
        height: auto;
        width: 100%;
        background: transparent;
    }
    """

    def __init__(
        self,
        *,
        margin: int = _DEFAULT_MARGIN,
        id: str | None = None,
        theme: ThemePalette = BUILTIN_THEMES[DEFAULT_THEME],
    ) -> None:
        super().__init__(id=id)
        self._margin = margin
        self._theme = theme
        self._lines: list[LyricLineData] = []
        self._active_index: int = -1
        self._message: str | None = None
        self._anim_enabled: bool = _env_flag("LYRIC_LILY_ANIM_ENABLED", True)
        self._dance_phase: int = 0
        # Pool of lyric rows, sized for one active line + ``margin`` upcoming.
        self._rows: list[LyricLine] = [LyricLine("") for _ in range(margin + 1)]
        self._message_row: Static = Static("")

    # ---- composition --------------------------------------------------------

    def compose(self):  # type: ignore[override]
        yield self._message_row
        for row in self._rows:
            yield row

    def on_mount(self) -> None:
        self._refresh_rows()
        if self._anim_enabled:
            self.set_interval(_DANCE_INTERVAL_SEC, self._dance_tick)

    # ---- public API used by LyricLilyApp ------------------------------------

    def set_lines(self, lines: list[LyricLineData]) -> None:
        """Replace the underlying lyric list (call on track change)."""
        self._lines = lines
        self._active_index = -1
        self._message = None
        if self.is_mounted:
            self.offset = Offset(0, 0)
            self._refresh_rows()

    def show_message(self, message: str, *, style: str = "yellow") -> None:
        """Render a single status message instead of lyric rows."""
        self._lines = []
        self._active_index = -1
        self._message = message
        if self.is_mounted:
            self.offset = Offset(0, 0)
            self._refresh_rows()

    def set_active(self, index: int) -> None:
        if not self._lines or self._message is not None:
            return
        if index == self._active_index:
            return
        self._active_index = index

        if not self.is_mounted:
            return

        self._refresh_active_line()

    # ---- internals ----------------------------------------------------------

    def _refresh_active_line(self) -> None:
        if not self.is_mounted:
            return
        self.offset = Offset(0, 0)
        self._refresh_rows()
        self._pop_active()

    def _refresh_rows(self) -> None:
        # Message mode: show the message row, blank everything else.
        if self._message is not None:
            self._message_row.update(Text(self._message, style="yellow"))
            self._message_row.display = True
            for row in self._rows:
                row.update("")
                row.display = False
            return

        self._message_row.update("")
        self._message_row.display = False

        if not self._lines:
            for row in self._rows:
                row.update("")
                row.display = False
            return

        start, end, active = visible_lyric_window(
            self._lines, self._active_index, margin=self._margin
        )
        visible = self._lines[start:end]
        for offset, row in enumerate(self._rows):
            if offset < len(visible):
                _, text = visible[offset]
                # When ``active`` is -1 the song hasn't started; everyone is faded.
                distance = abs((start + offset) - active) if active >= 0 else self._margin + 1
                row.set_line(
                    text,
                    distance=distance,
                    active=(distance == 0 and active >= 0),
                    theme=self._theme,
                    dance_phase=self._dance_phase,
                )
                row.display = True
            else:
                row.update("")
                row.display = False

    def _pop_active(self) -> None:
        if self._active_index < 0 or not self._rows:
            return
        # Active line is always the first row in the visible window.
        self._rows[0].pop()

    def _dance_tick(self) -> None:
        if not self._lines or self._message is not None or self._active_index < 0:
            return
        self._dance_phase = (self._dance_phase + 1) % 6
        self._refresh_rows()
