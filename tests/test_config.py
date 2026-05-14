from __future__ import annotations

from pathlib import Path

from lyric_lily.config import load_config


def test_load_config_missing_file_returns_defaults(tmp_path: Path) -> None:
    cfg = load_config(tmp_path / "missing.toml")

    assert cfg.theme_active is None
    assert cfg.theme_custom == {}


def test_load_config_reads_theme_settings(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        """
[theme]
active = "ocean"

[theme.custom.ocean]
active_lyric = "#00FFFF"
near_lyric = "#0099AA"
far_lyric = "#003344"
meta = "#4488AA"
source = "#224455"
""".strip(),
        encoding="utf-8",
    )

    cfg = load_config(path)

    assert cfg.theme_active == "ocean"
    assert cfg.theme_custom["ocean"]["active_lyric"] == "#00FFFF"


def test_load_config_bad_toml_returns_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text("[theme\nactive = ", encoding="utf-8")

    cfg = load_config(path)

    assert cfg.theme_active is None
    assert cfg.theme_custom == {}
