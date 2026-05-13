from __future__ import annotations

import sys

from lyric_lily.now_playing.backends.base import NowPlayingBackend
from lyric_lily.now_playing.backends.linux_playerctl import LinuxPlayerctlBackend
from lyric_lily.now_playing.errors import PlaybackUnavailableError
from lyric_lily.now_playing.types import PlaybackSnapshot, PlayState

__all__ = [
    "LinuxPlayerctlBackend",
    "NowPlayingBackend",
    "PlaybackSnapshot",
    "PlaybackUnavailableError",
    "PlayState",
    "default_backend",
]


def default_backend() -> NowPlayingBackend:
    """Return the platform default backend (Linux: playerctl)."""
    if sys.platform == "linux":
        return LinuxPlayerctlBackend()
    raise NotImplementedError(
        f"Now-playing is not implemented for {sys.platform!r} yet; Linux uses playerctl (M1)."
    )
