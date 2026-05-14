import subprocess
from types import SimpleNamespace

import pytest

from lyric_lily.now_playing.backends.linux_playerctl import (
    LinuxPlayerctlBackend,
    _list_players,
    _looks_like_spotify_ad,
    _parse_metadata_fields,
)
from lyric_lily.now_playing.errors import PlaybackUnavailableError


def test_parse_metadata_fields_from_playerctl_format() -> None:
    title, artist, album, duration_sec = _parse_metadata_fields(
        "Song\nArtist\nAlbum\n123456000"
    )
    assert title == "Song"
    assert artist == "Artist"
    assert album == "Album"
    assert duration_sec == 123.456


def test_parse_metadata_fields_tolerates_missing_values() -> None:
    title, artist, album, duration_sec = _parse_metadata_fields("Song\n\n")
    assert title == "Song"
    assert artist is None
    assert album is None
    assert duration_sec is None


def test_spotify_ad_detection_matches_sparse_spotify_metadata() -> None:
    assert _looks_like_spotify_ad("spotify", "Advertisement", None, None)
    assert _looks_like_spotify_ad("spotifyd", "Spotify", "", "")


def test_spotify_ad_detection_does_not_match_regular_tracks() -> None:
    assert not _looks_like_spotify_ad("spotify", "Song", "Artist", "Album")
    assert not _looks_like_spotify_ad("vlc", "Advertisement", None, None)


def test_backend_read_reports_spotify_ads_as_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = LinuxPlayerctlBackend(player="spotify")

    def fake_run_text(self: LinuxPlayerctlBackend, *args: str) -> str:
        if args == ("status",):
            return "Playing"
        if args == (
            "metadata",
            "--format",
            "{{title}}\n{{artist}}\n{{album}}\n{{mpris:length}}",
        ):
            return "Advertisement\n\n\n30000000"
        if args == ("position",):
            return "1.0"
        raise AssertionError(args)

    monkeypatch.setattr(LinuxPlayerctlBackend, "_run_text", fake_run_text)

    with pytest.raises(PlaybackUnavailableError, match="advertisement"):
        backend.read()


def test_run_text_reports_missing_playerctl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("lyric_lily.now_playing.backends.linux_playerctl.shutil.which", lambda name: None)
    backend = LinuxPlayerctlBackend(player="spotify")

    with pytest.raises(PlaybackUnavailableError, match="playerctl was not found"):
        backend._run_text("status")


def test_run_text_reports_no_players_with_hint_when_unpinned(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("lyric_lily.now_playing.backends.linux_playerctl.shutil.which", lambda name: "/usr/bin/playerctl")
    monkeypatch.setattr("lyric_lily.now_playing.backends.linux_playerctl._list_players", lambda: [])

    def fake_run(*args: object, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=1, stdout="", stderr="No players found")

    monkeypatch.setattr("lyric_lily.now_playing.backends.linux_playerctl.subprocess.run", fake_run)
    backend = LinuxPlayerctlBackend()

    with pytest.raises(PlaybackUnavailableError, match="LYRIC_LILY_PLAYERCTL_PLAYER=spotify"):
        backend._run_text("status")


def test_run_text_reports_no_players_without_hint_when_pinned(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("lyric_lily.now_playing.backends.linux_playerctl.shutil.which", lambda name: "/usr/bin/playerctl")

    def fake_run(*args: object, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=1, stdout="", stderr="No players found")

    monkeypatch.setattr("lyric_lily.now_playing.backends.linux_playerctl.subprocess.run", fake_run)
    backend = LinuxPlayerctlBackend(player="spotify")

    with pytest.raises(PlaybackUnavailableError) as exc:
        backend._run_text("status")
    assert "No MPRIS players found" in str(exc.value)
    assert "LYRIC_LILY_PLAYERCTL_PLAYER=spotify" not in str(exc.value)


def test_run_text_reports_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("lyric_lily.now_playing.backends.linux_playerctl.shutil.which", lambda name: "/usr/bin/playerctl")

    def fake_run(*args: object, **kwargs: object) -> SimpleNamespace:
        raise subprocess.TimeoutExpired(cmd=["playerctl", "status"], timeout=5)

    monkeypatch.setattr("lyric_lily.now_playing.backends.linux_playerctl.subprocess.run", fake_run)
    backend = LinuxPlayerctlBackend(player="spotify")

    with pytest.raises(PlaybackUnavailableError, match="timed out"):
        backend._run_text("status")


def test_run_text_reports_generic_playerctl_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("lyric_lily.now_playing.backends.linux_playerctl.shutil.which", lambda name: "/usr/bin/playerctl")

    def fake_run(*args: object, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=2, stdout="", stderr="bad player")

    monkeypatch.setattr("lyric_lily.now_playing.backends.linux_playerctl.subprocess.run", fake_run)
    backend = LinuxPlayerctlBackend(player="spotify")

    with pytest.raises(PlaybackUnavailableError, match="playerctl failed \\(exit 2\\): bad player"):
        backend._run_text("status")


def test_list_players_returns_clean_player_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("lyric_lily.now_playing.backends.linux_playerctl.shutil.which", lambda name: "/usr/bin/playerctl")

    def fake_run(*args: object, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=0, stdout="spotify\n\nvlc\n", stderr="")

    monkeypatch.setattr("lyric_lily.now_playing.backends.linux_playerctl.subprocess.run", fake_run)

    assert _list_players() == ["spotify", "vlc"]


def test_backend_auto_selects_only_player(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("lyric_lily.now_playing.backends.linux_playerctl._list_players", lambda: ["spotify"])

    assert LinuxPlayerctlBackend().player == "spotify"
