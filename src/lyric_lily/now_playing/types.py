from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PlayState(str, Enum):
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class PlaybackSnapshot:
    """Single point-in-time view of what the desktop player reports."""

    title: str | None
    artist: str | None
    album: str | None
    position_sec: float
    duration_sec: float | None
    state: PlayState
    player_name: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "position_sec": self.position_sec,
            "duration_sec": self.duration_sec,
            "state": self.state.value,
            "player_name": self.player_name,
        }
