from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass

from lyric_lily.now_playing.errors import PlaybackUnavailableError
from lyric_lily.now_playing.types import PlaybackSnapshot, PlayState

_NO_PLAYERS = re.compile(r"no players?\s+found", re.IGNORECASE)


def _strip_or_none(s: str | None) -> str | None:
    if s is None:
        return None
    t = s.strip()
    return t if t else None


def _parse_status(raw: str) -> PlayState:
    key = raw.strip().lower()
    if key == "playing":
        return PlayState.PLAYING
    if key == "paused":
        return PlayState.PAUSED
    if key == "stopped":
        return PlayState.STOPPED
    return PlayState.UNKNOWN


def _parse_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_duration_sec(raw: str | None) -> float | None:
    """mpris:length from playerctl is usually microseconds as an integer string."""
    us = _parse_float(raw)
    if us is None:
        return None
    if us > 1_000_000:  # treat as microseconds
        return us / 1_000_000.0
    if us > 0:  # already seconds (unusual but tolerate)
        return us
    return None


def _parse_metadata_fields(raw: str) -> tuple[str | None, str | None, str | None, float | None, str | None, str | None]:
    fields = raw.splitlines()
    title = _strip_or_none(fields[0] if len(fields) > 0 else None)
    artist = _strip_or_none(fields[1] if len(fields) > 1 else None)
    album = _strip_or_none(fields[2] if len(fields) > 2 else None)
    duration_sec = _parse_duration_sec(fields[3] if len(fields) > 3 else None)
    track_id = _strip_or_none(fields[4] if len(fields) > 4 else None)
    source_url = _strip_or_none(fields[5] if len(fields) > 5 else None)
    return title, artist, album, duration_sec, track_id, source_url


def _looks_like_spotify_ad(
    player_name: str | None,
    title: str | None,
    artist: str | None,
    album: str | None,
) -> bool:
    if player_name is None or "spotify" not in player_name.lower():
        return False
    title_key = (title or "").strip().lower()
    artist_key = (artist or "").strip().lower()
    album_key = (album or "").strip().lower()
    return title_key in {"advertisement", "spotify"} and not artist_key and not album_key


@dataclass(slots=True)
class LinuxPlayerctlBackend:
    """Linux MPRIS via the ``playerctl`` CLI (install from distro packages)."""

    player: str | None = None
    """If set, passed as ``playerctl -p <name>``. Defaults to ``LYRIC_LILY_PLAYERCTL_PLAYER``."""

    def __post_init__(self) -> None:
        if self.player is None:
            self.player = os.environ.get("LYRIC_LILY_PLAYERCTL_PLAYER") or None
        if self.player is None:
            listed = _list_players()
            if len(listed) == 1:
                self.player = listed[0]

    def _cmd(self, *args: str) -> list[str]:
        out = ["playerctl"]
        if self.player:
            out += ["-p", self.player]
        out.extend(args)
        return out

    def _run_text(self, *args: str) -> str:
        if not shutil.which("playerctl"):
            raise PlaybackUnavailableError(
                "playerctl was not found in PATH. On Debian/Ubuntu install with:\n"
                "  sudo apt install playerctl"
            )
        try:
            proc = subprocess.run(
                self._cmd(*args),
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except subprocess.TimeoutExpired as e:
            raise PlaybackUnavailableError("playerctl timed out — try again.") from e
        except OSError as e:
            raise PlaybackUnavailableError(f"could not run playerctl: {e}") from e

        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        if proc.returncode != 0:
            combined = f"{err}\n{out}".strip()
            if _NO_PLAYERS.search(combined) or proc.returncode == 1 and not out:
                hint = (
                    " No MPRIS player reported tracks (start Spotify/your player, or set "
                    "LYRIC_LILY_PLAYERCTL_PLAYER=spotify if multiple players are running)."
                )
                raise PlaybackUnavailableError(
                    "No MPRIS players found for playerctl." + (hint if not self.player else "")
                )
            raise PlaybackUnavailableError(
                f"playerctl failed (exit {proc.returncode}): {combined or 'no output'}"
            )
        return out

    def read(self) -> PlaybackSnapshot:
        status_raw = self._run_text("status")
        state = _parse_status(status_raw)

        metadata_raw = self._run_text(
            "metadata",
            "--format",
            "{{title}}\n{{artist}}\n{{album}}\n{{mpris:length}}\n{{mpris:trackid}}\n{{xesam:url}}",
        )
        title, artist, album, duration_sec, track_id, source_url = _parse_metadata_fields(metadata_raw)
        if _looks_like_spotify_ad(self.player, title, artist, album):
            raise PlaybackUnavailableError(
                "Spotify is reporting an advertisement instead of a track; lyrics will resume after playback returns to music."
            )

        pos_raw = self._run_text("position")
        position_sec = _parse_float(pos_raw) or 0.0

        return PlaybackSnapshot(
            title=title,
            artist=artist,
            album=album,
            position_sec=position_sec,
            duration_sec=duration_sec,
            state=state,
            player_name=self.player,
            track_id=track_id,
            source_url=source_url,
        )


def _list_players() -> list[str]:
    if not shutil.which("playerctl"):
        return []
    try:
        proc = subprocess.run(
            ["playerctl", "-l"],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    return [p.strip() for p in (proc.stdout or "").splitlines() if p.strip()]
