from lyric_lily.lrc_sync import line_index_at, parse_synced_lrc


def test_parse_synced_lrc_basic() -> None:
    text = "[0:04.82] first\n[0:06.74] second\n[ar:foo]\n"
    lines = parse_synced_lrc(text)
    assert len(lines) == 2
    assert abs(lines[0][0] - 4.82) < 0.001
    assert lines[0][1] == "first"
    assert abs(lines[1][0] - 6.74) < 0.001


def test_line_index_at_before_first() -> None:
    lines = [(1.0, "a"), (5.0, "b")]
    assert line_index_at(lines, 0.5) == -1


def test_line_index_at_boundaries() -> None:
    lines = [(1.0, "a"), (5.0, "b")]
    assert line_index_at(lines, 1.0) == 0
    assert line_index_at(lines, 3.0) == 0
    assert line_index_at(lines, 5.0) == 1
    assert line_index_at(lines, 99.0) == 1


def test_parse_empty() -> None:
    assert parse_synced_lrc("") == []
    assert line_index_at([], 1.0) == -1
