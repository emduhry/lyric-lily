from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Mapping

from lyric_lily.config import AppConfig, load_config


@dataclass(frozen=True, slots=True)
class ThemePalette:
    """Resolved terminal colors for a lyric-lily theme.

    All fields are Rich/Textual-compatible ``#RRGGBB`` color strings.
    """

    background: str
    active_lyric: str
    near_lyric: str
    far_lyric: str
    meta: str
    source: str


DEFAULT_THEME = "ember"


BUILTIN_THEMES: Dict[str, ThemePalette] = {
    "vapor": ThemePalette(
        background="#2D1B4E",
        active_lyric="#7DF9FF",
        near_lyric="#FF71CE",
        far_lyric="#2D1B4E",
        meta="#01CDFE",
        source="#B967FF",
    ),
    "mono": ThemePalette(
        background="#080808",
        active_lyric="#F5F5F5",
        near_lyric="#B8B8B8",
        far_lyric="#555555",
        meta="#A0A0A0",
        source="#707070",
    ),
    "ember": ThemePalette(
        background="#5C2F1A",
        active_lyric="#FFE1A8",
        near_lyric="#FFB347",
        far_lyric="#5C2F1A",
        meta="#D98A3D",
        source="#8A4B2A",
    ),
    "tropic": ThemePalette(
        background="#0D2926",
        active_lyric="#B2E8DF",
        near_lyric="#1DB39E",
        far_lyric="#0F4A40",
        meta="#F5A623",
        source="#3A5E58",
    ),
    "pastel_kiss": ThemePalette(
        background="#1A1220",
        active_lyric="#F5C8D8",
        near_lyric="#D9637A",
        far_lyric="#4A2535",
        meta="#A8D8D8",
        source="#2E3040",
    ),
    "lilys_pick": ThemePalette(
        background="#1A1018",
        active_lyric="#F4C9B0",
        near_lyric="#C8808A",
        far_lyric="#3D2535",
        meta="#E8A090",
        source="#302030",
    ),
    "cedar": ThemePalette(
        background="#1A1E12",
        active_lyric="#C0C48A",
        near_lyric="#5E6B40",
        far_lyric="#2D3820",
        meta="#A89060",
        source="#252A18",
    ),
    "aero_sky": ThemePalette(
        background="#0E1A2E",
        active_lyric="#C8E8F8",
        near_lyric="#88B8D8",
        far_lyric="#1A2A5A",
        meta="#BEE8B8",
        source="#0E1E30",
    ),
    "beach_peace": ThemePalette(
        background="#050E14",
        active_lyric="#7ADBF0",
        near_lyric="#20A8C8",
        far_lyric="#0A2A38",
        meta="#1A7898",
        source="#071820",
    ),
    "verbena": ThemePalette(
        background="#120A1C",
        active_lyric="#D0B0E8",
        near_lyric="#A878C8",
        far_lyric="#2A1040",
        meta="#F0B8D8",
        source="#200C35",
    ),
}


def _validate_hex(style: str) -> str:
    """Validate and normalize ``#RRGGBB`` colors."""

    s = style.strip().upper()
    if not s:
        raise ValueError("empty color value")
    if s.startswith("#"):
        raw = s[1:]
    else:
        raw = s
    if len(raw) != 6 or any(c not in "0123456789ABCDEF" for c in raw):
        raise ValueError(f"invalid hex color {style!r}; expected #RRGGBB")
    return f"#{raw}"


def _config_or_default(
    cfg: AppConfig | None = None,
    *,
    config_path: Path | None = None,
) -> AppConfig:
    return cfg if cfg is not None else load_config(config_path)


def available_theme_names(
    cfg: AppConfig | None = None,
    *,
    config_path: Path | None = None,
) -> list[str]:
    """Return all known theme names (built-in + custom)."""

    c = _config_or_default(cfg, config_path=config_path)
    names: set[str] = set(BUILTIN_THEMES.keys()) | set(c.theme_custom.keys())
    return sorted(names)


def _resolve_theme_source(name: str, cfg: AppConfig) -> Mapping[str, str] | None:
    if name in cfg.theme_custom:
        return cfg.theme_custom[name]
    if name in BUILTIN_THEMES:
        # Represent built-ins in the same slot->style mapping shape.
        t = BUILTIN_THEMES[name]
        return {
            "background": t.background,
            "active_lyric": t.active_lyric,
            "near_lyric": t.near_lyric,
            "far_lyric": t.far_lyric,
            "meta": t.meta,
            "source": t.source,
        }
    return None


def load_theme(
    name: str | None,
    config_path: Path | AppConfig | None = None,
    *,
    cfg: AppConfig | None = None,
) -> ThemePalette:
    """Load a theme by name, consulting config then built-ins.

    ``None`` means: use config's ``theme.active`` or the default theme.
    """

    if isinstance(config_path, AppConfig):
        cfg = config_path
        config_path = None
    c = _config_or_default(cfg, config_path=config_path)
    effective_name = name or c.theme_active or DEFAULT_THEME

    raw = _resolve_theme_source(effective_name, c)
    if raw is None:
        choices = ", ".join(available_theme_names(c))
        raise ValueError(f"unknown theme {effective_name!r}; available themes: {choices}")

    def slot(key: str, fallback: str) -> str:
        value = raw.get(key, fallback)
        try:
            return _validate_hex(value)
        except ValueError as e:
            raise ValueError(f"theme {effective_name!r} slot {key!r}: {e}") from e

    # When a custom theme overrides a built-in, start from built-in colors.
    base = BUILTIN_THEMES.get(effective_name, BUILTIN_THEMES[DEFAULT_THEME])

    return ThemePalette(
        background=slot("background", base.background),
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


def list_themes(config_path: Path | None = None) -> list[str]:
    """Return names of all built-in and user-defined themes."""

    return available_theme_names(config_path=config_path)
