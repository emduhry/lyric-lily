from lyric_lily.ui.render import (
    lyric_style_for_distance,
    render_lyrics_window,
    visible_lyric_window,
)


def test_visible_lyric_window_starts_with_active_line() -> None:
    lines = [(float(i), f"line {i}") for i in range(20)]
    assert visible_lyric_window(lines, 10, margin=2) == (10, 13, 10)


def test_visible_lyric_window_handles_before_first_line() -> None:
    lines = [(float(i), f"line {i}") for i in range(20)]
    assert visible_lyric_window(lines, -1, margin=2) == (0, 5, -1)


def test_lyric_styles_use_foreground_only_gradient() -> None:
    assert lyric_style_for_distance(0) == "bold rgb(255,236,246)"
    assert lyric_style_for_distance(1) == "rgb(214,188,210)"
    assert lyric_style_for_distance(2) == "rgb(154,137,164)"
    assert lyric_style_for_distance(3) == "rgb(104,96,118)"
    assert lyric_style_for_distance(4) == "rgb(74,68,84)"


def test_render_lyrics_window_marks_active_line() -> None:
    lines = [(0.0, "first"), (1.0, "second"), (2.0, "third")]
    rendered = render_lyrics_window(lines, 1, margin=1)
    assert rendered.plain == "  second\n\nthird\n"
    spans = rendered.spans
    assert spans[0].style == "bold rgb(255,236,246)"
    assert spans[1].style == "rgb(214,188,210)"
