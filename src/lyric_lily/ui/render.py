from __future__ import annotations

from rich.text import Text

LyricLine = tuple[float, str]


def lyric_style_for_distance(distance: int) -> str:
    if distance == 0:
        return "bold rgb(255,236,246)"
    if distance == 1:
        return "rgb(214,188,210)"
    if distance == 2:
        return "rgb(154,137,164)"
    if distance == 3:
        return "rgb(104,96,118)"
    return "rgb(74,68,84)"


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
    margin: int = 6,
) -> Text:
    start, end, active = visible_lyric_window(lines, active_index, margin=margin)
    text = Text()
    for index in range(start, end):
        _, line = lines[index]
        distance = abs(index - active) if active >= 0 else margin + 1
        prefix = "  " if distance == 0 else ""
        suffix = "\n\n" if distance == 0 else "\n"
        text.append(prefix + line + suffix, style=lyric_style_for_distance(distance))
    return text
