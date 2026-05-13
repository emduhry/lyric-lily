from __future__ import annotations

import logging
from typing import Sequence

import syncedlyrics

from lyric_lily.lyrics.local_lrc import is_probable_synced_lrc
from lyric_lily.now_playing.types import PlaybackSnapshot

# (message label, syncedlyrics provider filter). LRCLIB first.
REMOTE_PROVIDERS: Sequence[tuple[str, list[str]]] = (
    ("LRCLIB.net", ["lrclib"]),
    ("Musixmatch", ["musixmatch"]),
    ("NetEase", ["netease"]),
    ("Megalobiz", ["megalobiz"]),
    ("Genius", ["genius"]),
)


def _quiet_syncedlyrics_loggers() -> None:
    logging.getLogger("syncedlyrics").setLevel(logging.WARNING)
    for name in (
        "syncedlyrics",
        "Lrclib",
        "Musixmatch",
        "NetEase",
        "Megalobiz",
        "Genius",
        "urllib3",
    ):
        logging.getLogger(name).setLevel(logging.WARNING)


def search_term_from_snapshot(snap: PlaybackSnapshot) -> str | None:
    parts = [snap.artist, snap.title]
    q = " ".join(p.strip() for p in parts if p and str(p).strip())
    return q if q else None


def fetch_remote_lrc(search_term: str) -> tuple[str, str] | None:
    """
    Try syncedlyrics providers in order. Returns ``(lrc_text, 'Label (syncedlyrics package)')`` or None.
    """
    _quiet_syncedlyrics_loggers()
    for label, providers in REMOTE_PROVIDERS:
        try:
            text = syncedlyrics.search(
                search_term,
                synced_only=True,
                save_path=None,
                providers=providers,
            )
        except Exception:
            continue
        if text and is_probable_synced_lrc(text):
            return text.strip(), f"{label} (syncedlyrics package)"
    return None
