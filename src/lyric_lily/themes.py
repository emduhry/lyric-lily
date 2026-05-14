from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping

from lyric_lily.config import AppConfig, load_config


@dataclass(frozen=True, slots=True)
class ThemePalette:
    """Resolved terminal colors for a lyric-lily theme.

    All fields are Rich/Textual style foreground strings (e.g. ``"rgb(255,236,246)"``).
    """

    active_lyric: str
    near_lyric: str
    far_lyric: str
    meta: str
    source: str


DEFAULT_THEME = "lily"


BUILTIN_THEMES: Dict[str, ThemePalette] = {
    # Current pink/purple gradient.
    "lily": ThemePalette(
        active_lyric="rgb(255,236,246)",
        near_lyric="rgb(214,188,210)",
        far_lyric="rgb(74,68,84)",
        meta="rgb(145,136,158)",
        source="rgb(84,78,96)",
    ),
}


def _hex_to_rgb(style: str) -> str:
    """Convert ``#RRGGBB`` (or ``RRGGBB``) hex to ``rgb(r,g,b)``.

    If the string already looks like a Rich color (e.g. ``"rgb(..."``), it is
    returned unchanged.
    """

    s = style.strip()
    if not s:
        raise ValueError("empty color value")
    lower = s.lower()
    if lower.startswith("rgb("):
        return s
    if lower.startswith("#"):
        lower = lower[1:]
    if len(lower) != 6 or any(c not in "0123456789abcdef" for c in lower):
        raise ValueError(f"invalid hex color {style!r}; expected #RRGGBB")
    r = int(lower[0:2], 16)
    g = int(lower[2:4], 16)
    b = int(lower[4:6], 16)
    return f"rgb({r},{g},{b})"


def _config_or_default(cfg: AppConfig | None = None) -> AppConfig:
    return cfg if cfg is not None else load_config()


def available_theme_names(cfg: AppConfig | None = None) -> list[str]:
    """Return all known theme names (built-in + custom)."""

    c = _config_or_default(cfg)
    names: set[str] = set(BUILTIN_THEMES.keys()) | set(c.theme_custom.keys())
    return sorted(names)


def _resolve_theme_source(name: str, cfg: AppConfig) -> Mapping[str, str] | None:
    if name in cfg.theme_custom:
        return cfg.theme_custom[name]
    if name in BUILTIN_THEMES:
        # Represent built-ins in the same slot->style mapping shape.
        t = BUILTIN_THEMES[name]
        return {
            "active_lyric": t.active_lyric,
            "near_lyric": t.near_lyric,
            "far_lyric": t.far_lyric,
            "meta": t.meta,
            "source": t.source,
        }
    return None


def load_theme(name: str | None, cfg: AppConfig | None = None) -> ThemePalette:
    """Load a theme by name, consulting config then built-ins.

    ``None`` means: use config's ``theme.active`` or the default theme.
    """

    c = _config_or_default(cfg)
    effective_name = name or c.theme_active or DEFAULT_THEME

    raw = _resolve_theme_source(effective_name, c)
    if raw is None:
        raise ValueError(f"unknown theme {effective_name!r}")

    def slot(key: str, fallback: str) -> str:
        value = raw.get(key, fallback)
        return _hex_to_rgb(value)

    # When a custom theme overrides a built-in, start from built-in colors.
    base = BUILTIN_THEMES.get(effective_name, BUILTIN_THEMES[DEFAULT_THEME])

    return ThemePalette(
        active_lyric=slot("active_lyric", base.active_lyric),
        near_lyric=slot("near_lyric", base.near_lyric),
        far_lyric=slot("far_lyric", base.far_lyric),
        meta=slot("meta", base.meta),
        source=slot("source", base.source),
    )


def iter_themes_with_default(cfg: AppConfig | None = None) -> Iterable[tuple[str, bool]]:
    """Yield ``(name, is_default)`` for all known themes.

    Useful for ``lyric-lily themes`` listing.
    """

    c = _config_or_default(cfg)
    default_name = c.theme_active or DEFAULT_THEME
    for name in available_theme_names(c):
        yield name, name == default_name
