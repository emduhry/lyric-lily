from __future__ import annotations

import os
import re
from collections.abc import Iterator
from pathlib import Path

_FS_UNSAFE = re.compile(r'[\0<>:"|?*\\/]+')
_LRC_TIME = re.compile(r"\[\s*\d{1,3}\s*:\s*\d{2}(?:\s*\.\s*\d+)?\s*\]")


def safe_filename_segment(s: str, max_len: int = 180) -> str:
    s = _FS_UNSAFE.sub(" ", s).strip()
    s = re.sub(r"\s+", " ", s)
    if not s:
        return "track"
    return s[:max_len]


def local_lrc_search_dirs() -> list[Path]:
    """Directories to look for ``*.lrc`` (search in order)."""
    out: list[Path] = []
    extra = os.environ.get("LYRIC_LILY_LRC_DIRS", "")
    if extra.strip():
        for part in extra.split(os.pathsep):
            p = Path(part).expanduser()
            if str(p).strip():
                out.append(p)
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    cfg_root = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    out.append(cfg_root / "lyric-lily" / "lrc")
    out.append(Path.cwd() / "lyrics")
    out.append(Path.cwd() / ".lyrics")

    seen: set[str] = set()
    uniq: list[Path] = []
    for p in out:
        key = str(p.expanduser().resolve(strict=False))
        if key not in seen:
            seen.add(key)
            uniq.append(p)
    return uniq


def candidate_filenames(artist: str | None, title: str | None) -> list[str]:
    if not title or not str(title).strip():
        return []
    t = title.strip()
    a = artist.strip() if artist else ""
    names: list[str] = []
    if a:
        names.append(f"{safe_filename_segment(a)} - {safe_filename_segment(t)}.lrc")
        names.append(f"{safe_filename_segment(f'{a} - {t}')}.lrc")
    names.append(f"{safe_filename_segment(t)}.lrc")

    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def is_probable_synced_lrc(text: str) -> bool:
    """True if text looks like synced LRC (has timestamp lines), not plain text."""
    if not text or not text.strip():
        return False
    return bool(_LRC_TIME.search(text))


def iter_local_lrc_paths(artist: str | None, title: str | None) -> Iterator[Path]:
    """Yield existing candidate ``.lrc`` paths in search order."""
    names = candidate_filenames(artist, title)
    if not names:
        return
    seen_paths: set[str] = set()
    for base in local_lrc_search_dirs():
        for name in names:
            path = (base / name).expanduser()
            try:
                if not path.is_file():
                    continue
                resolved = str(path.resolve())
                if resolved in seen_paths:
                    continue
                seen_paths.add(resolved)
                yield path.resolve()
            except OSError:
                continue
