from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LyricResolveResult:
    """Outcome of resolving LRC text for a track."""

    found: bool
    lrc_text: str | None
    """One clear line for humans, e.g. 'Lyrics from: …' or 'No synced lyrics found …'."""
    headline: str
    """Extra context (paths checked, providers tried)."""
    detail: str

    def as_dict(self) -> dict[str, object]:
        return {
            "found": self.found,
            "lrc_text": self.lrc_text,
            "headline": self.headline,
            "detail": self.detail,
        }
