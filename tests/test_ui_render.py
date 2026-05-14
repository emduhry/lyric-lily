from lyric_lily.themes import BUILTIN_THEMES
from lyric_lily.ui.render import (
    lyric_color_for_distance,
    lyric_style_for_distance,
    render_lyrics_window,
    visible_lyric_window,
)


_EMBER = BUILTIN_THEMES["ember"]


def test_lyric_color_for_distance_returns_theme_colors() -> None:
    assert lyric_color_for_distance(0, _EMBER) == _EMBER.active_lyric
    assert lyric_color_for_distance(1, _EMBER) == _EMBER.near_lyric
    assert lyric_color_for_distance(2, _EMBER) == _EMBER.near_lyric
    assert lyric_color_for_distance(3, _EMBER) == _EMBER.far_lyric
    assert lyric_color_for_distance(99, _EMBER) == _EMBER.far_lyric


def test_lyric_style_uses_color_helper() -> None:
    for distance in range(5):
        color = lyric_color_for_distance(distance, _EMBER)
        assert color in lyric_style_for_distance(distance, _EMBER)


def test_visible_lyric_window_starts_with_active_line() -> None:
    lines = [(float(i), f"line {i}") for i in range(20)]
    assert visible_lyric_window(lines, 10, margin=2) == (10, 13, 10)


def test_visible_lyric_window_handles_before_first_line() -> None:
    lines = [(float(i), f"line {i}") for i in range(20)]
    assert visible_lyric_window(lines, -1, margin=2) == (0, 5, -1)


def test_lyric_styles_use_theme_palette() -> None:
    assert lyric_style_for_distance(0, _EMBER) == f"bold {_EMBER.active_lyric}"
    assert lyric_style_for_distance(1, _EMBER) == _EMBER.near_lyric
    assert lyric_style_for_distance(2, _EMBER) == _EMBER.near_lyric
    assert lyric_style_for_distance(3, _EMBER) == _EMBER.far_lyric
    assert lyric_style_for_distance(4, _EMBER) == _EMBER.far_lyric


def test_render_lyrics_window_marks_active_line() -> None:
    lines = [(0.0, "first"), (1.0, "second"), (2.0, "third")]
    rendered = render_lyrics_window(lines, 1, theme=_EMBER, margin=1)
    assert rendered.plain == "  second\n\nthird\n"
    spans = rendered.spans
    assert spans[0].style == f"bold {_EMBER.active_lyric}"
    assert spans[1].style == _EMBER.near_lyric
