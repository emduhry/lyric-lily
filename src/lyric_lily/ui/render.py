from __future__ import annotations

from rich.text import Text

from lyric_lily.themes import ThemePalette

LyricLine = tuple[float, str]


def lyric_color_for_distance(distance: int, theme: ThemePalette) -> str:
    """Bare ``rgb(r,g,b)`` for Textual ``styles.color`` and Rich styling."""
    if distance == 0:
        return theme.active_lyric
    if distance in (1, 2):
        return theme.near_lyric
    return theme.far_lyric


def lyric_style_for_distance(distance: int, theme: ThemePalette) -> str:
    color = lyric_color_for_distance(distance, theme)
    return f"bold {color}" if distance == 0 else color


def visible_lyric_window(
    lines: list[LyricLine],
    active_index: int,
    *,
    margin: int = 6,
) -> tuple[int, int, int]:
    if active_index < 0:
        return 0, min(len(lines), 2 * margin + 1), -1
    return (
        active_index,
        min(len(lines), active_index + margin + 1),
        active_index,
    )


def render_lyrics_window(
    lines: list[LyricLine],
    active_index: int,
    *,
    theme: ThemePalette,
    margin: int = 6,
) -> Text:
    start, end, active = visible_lyric_window(lines, active_index, margin=margin)
    text = Text()
    for index in range(start, end):
        _, line = lines[index]
        distance = abs(index - active) if active >= 0 else margin + 1
        prefix = "  " if distance == 0 else ""
        suffix = "\n\n" if distance == 0 else "\n"
        text.append(prefix + line + suffix, style=lyric_style_for_distance(distance, theme))
    return text
