from __future__ import annotations

import pytest

from lyric_lily.config import AppConfig
from lyric_lily.themes import BUILTIN_THEMES, load_theme, list_themes


def test_load_theme_returns_builtin() -> None:
    assert load_theme("vapor") == BUILTIN_THEMES["vapor"]


def test_load_theme_uses_config_default() -> None:
    cfg = AppConfig(theme_active="ember", theme_custom={})

    assert load_theme(None, cfg) == BUILTIN_THEMES["ember"]


def test_custom_theme_overrides_builtin_name() -> None:
    cfg = AppConfig(
        theme_active=None,
        theme_custom={
            "ember": {
                "background": "#001122",
                "active_lyric": "#00FFFF",
                "near_lyric": "#0099AA",
                "far_lyric": "#003344",
                "meta": "#4488AA",
                "source": "#224455",
            }
        },
    )

    theme = load_theme("ember", cfg)

    assert theme.background == "#001122"
    assert theme.active_lyric == "#00FFFF"
    assert theme.source == "#224455"


def test_custom_theme_background_is_optional() -> None:
    cfg = AppConfig(
        theme_active=None,
        theme_custom={
            "ocean": {
                "active_lyric": "#00FFFF",
                "near_lyric": "#0099AA",
                "far_lyric": "#003344",
                "meta": "#4488AA",
                "source": "#224455",
            }
        },
    )

    theme = load_theme("ocean", cfg)

    assert theme.background == BUILTIN_THEMES["ember"].background
    assert theme.active_lyric == "#00FFFF"


def test_load_theme_rejects_bad_hex_with_slot_name() -> None:
    cfg = AppConfig(
        theme_active=None,
        theme_custom={
            "bad": {
                "active_lyric": "nope",
            }
        },
    )

    with pytest.raises(ValueError, match="active_lyric"):
        load_theme("bad", cfg)


def test_missing_theme_lists_available_names() -> None:
    with pytest.raises(ValueError, match="available themes"):
        load_theme("missing", AppConfig(theme_active=None, theme_custom={}))


def test_list_themes_includes_builtins_and_custom() -> None:
    names = list_themes()

    assert {
        "vapor",
        "mono",
        "ember",
        "tropic",
        "pastel_kiss",
        "lilys_pick",
        "cedar",
        "aero_sky",
        "beach_peace",
        "verbena",
    }.issubset(names)
