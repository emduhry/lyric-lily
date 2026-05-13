from __future__ import annotations

from typing import Protocol

from lyric_lily.now_playing.types import PlaybackSnapshot


class NowPlayingBackend(Protocol):
    """Pluggable source for title/artist/position (Linux playerctl today; others later)."""

    def read(self) -> PlaybackSnapshot:
        """Return a snapshot or raise PlaybackUnavailableError with a helpful message."""
