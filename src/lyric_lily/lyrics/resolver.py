from __future__ import annotations

from pathlib import Path

from lyric_lily.lyrics.local_lrc import (
    candidate_filenames,
    is_probable_synced_lrc,
    iter_local_lrc_paths,
    local_lrc_search_dirs,
)
from lyric_lily.lyrics.remote import REMOTE_PROVIDERS, fetch_remote_lrc, search_term_from_snapshot
from lyric_lily.lyrics.types import LyricResolveResult
from lyric_lily.now_playing.types import PlaybackSnapshot


def resolve_lyrics(
    snap: PlaybackSnapshot,
    *,
    local_only: bool = False,
) -> LyricResolveResult:
    """
    Prefer a local ``.lrc`` file, then LRCLIB / other syncedlyrics providers (synced only).
    """
    term = search_term_from_snapshot(snap)
    if not term:
        return LyricResolveResult(
            found=False,
            lrc_text=None,
            headline="No synced lyrics found (missing track title/artist from player).",
            detail="playerctl did not report enough metadata to search.",
        )

    dirs = local_lrc_search_dirs()
    last_read_error: str | None = None
    for path in iter_local_lrc_paths(snap.artist, snap.title):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            last_read_error = f"{path}: {e}"
            continue
        if is_probable_synced_lrc(text):
            return LyricResolveResult(
                found=True,
                lrc_text=text,
                headline=f"Lyrics from: local file {path}",
                detail=f"Searched local dirs first: {_format_dirs(dirs)}",
            )

    if local_only:
        names = candidate_filenames(snap.artist, snap.title)
        extra = f" {last_read_error}" if last_read_error else ""
        return LyricResolveResult(
            found=False,
            lrc_text=None,
            headline="No synced lyrics found (local .lrc only; nothing usable on disk).",
            detail=(
                f"Searched: {_format_dirs(dirs)} for filenames like: "
                f"{', '.join(names) if names else '(none)'}.{extra}"
            ),
        )

    remote = fetch_remote_lrc(term)
    if remote:
        lrc_text, attribution = remote
        return LyricResolveResult(
            found=True,
            lrc_text=lrc_text,
            headline=f"Lyrics from: {attribution}",
            detail=(
                f"Query: {term!r}. Local dirs checked first: {_format_dirs(dirs)}. "
                f"Remote order: {', '.join(l for l, _ in REMOTE_PROVIDERS)}."
            ),
        )

    extra = f" Local read errors: {last_read_error}" if last_read_error else ""
    return LyricResolveResult(
        found=False,
        lrc_text=None,
        headline="No synced lyrics found.",
        detail=(
            f"Query: {term!r}. Searched local dirs: {_format_dirs(dirs)}; "
            f"then syncedlyrics providers: {', '.join(l for l, _ in REMOTE_PROVIDERS)}.{extra}"
        ),
    )


def _format_dirs(dirs: list[Path]) -> str:
    if not dirs:
        return "(none)"
    return ", ".join(str(d.expanduser()) for d in dirs)
