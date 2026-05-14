from lyric_lily.now_playing.types import PlaybackSnapshot, PlayState
from lyric_lily.ui.app import playback_track_key


def test_playback_track_key_prefers_track_id() -> None:
    snap = PlaybackSnapshot(
        title="Song",
        artist="Artist",
        album="Album",
        position_sec=1.0,
        duration_sec=2.0,
        state=PlayState.PLAYING,
        player_name="spotify",
        track_id="spotify:track:abc123",
    )
    assert playback_track_key(snap) == "track:spotify:track:abc123"


def test_playback_track_key_falls_back_to_metadata_tuple() -> None:
    snap = PlaybackSnapshot(
        title="Song",
        artist="Artist",
        album="Album",
        position_sec=1.0,
        duration_sec=2.0,
        state=PlayState.PLAYING,
        player_name="spotify",
    )
    assert playback_track_key(snap) == ("spotify", "Artist", "Album", "Song")
