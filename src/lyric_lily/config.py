from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

try:  # Python 3.11+
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover - runtime guard
    tomllib = None  # type: ignore[assignment]


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Application configuration loaded from TOML.

    Currently only covers theming but can grow over time.
    """

    theme_active: str | None
    theme_custom: Dict[str, Dict[str, str]]


def _default_config() -> AppConfig:
    return AppConfig(theme_active=None, theme_custom={})


def _config_path() -> Path:
    """Return the default config file path.

    Uses XDG_CONFIG_HOME if set, otherwise ~/.config.
    """

    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        root = Path(base)
    else:
        root = Path.home() / ".config"
    return root / "lyric-lily" / "config.toml"


def load_config(path: Path | None = None) -> AppConfig:
    """Load configuration from TOML, or return defaults if missing/invalid."""

    cfg_path = path or _config_path()
    if tomllib is None:
        return _default_config()
    try:
        with cfg_path.open("rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        return _default_config()
    except OSError:
        return _default_config()
    except tomllib.TOMLDecodeError:
        return _default_config()

    theme_table = data.get("theme") or {}
    if not isinstance(theme_table, dict):
        theme_table = {}
    active = theme_table.get("active")
    if active is not None and not isinstance(active, str):
        active = None

    custom_root = theme_table.get("custom") or {}
    if not isinstance(custom_root, dict):
        custom_root = {}

    theme_custom: Dict[str, Dict[str, str]] = {}
    for name, table in custom_root.items():
        if isinstance(table, dict):
            # Shallow copy and string-coerce values.
            theme_custom[str(name)] = {str(k): str(v) for k, v in table.items()}

    return AppConfig(theme_active=active, theme_custom=theme_custom)
