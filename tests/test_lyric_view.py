import asyncio

import pytest

from textual.app import App, ComposeResult

from lyric_lily.ui.lyric_view import LyricLine, LyricView, compute_slide_offset


def test_compute_slide_offset_forward_step() -> None:
    assert compute_slide_offset(10, 11, line_height=2) == -2


def test_compute_slide_offset_multi_step_within_threshold() -> None:
    assert compute_slide_offset(10, 13, line_height=2, snap_threshold=4) == -6


def test_compute_slide_offset_large_jump_snaps() -> None:
    assert compute_slide_offset(0, 20, line_height=2, snap_threshold=4) == 0


def test_compute_slide_offset_backward_seek_snaps() -> None:
    assert compute_slide_offset(10, 8, line_height=2) == 0


def test_compute_slide_offset_no_previous_active_snaps() -> None:
    assert compute_slide_offset(-1, 5, line_height=2) == 0


def test_compute_slide_offset_unchanged_index_snaps() -> None:
    assert compute_slide_offset(5, 5, line_height=2) == 0


class _Harness(App[None]):
    def compose(self) -> ComposeResult:
        yield LyricView(id="lyrics")


def _visible_rows(view: LyricView) -> list[LyricLine]:
    return [row for row in view.query(LyricLine) if row.display]


def test_lyric_view_set_active_advances_window() -> None:
    async def scenario() -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            view = app.query_one("#lyrics", LyricView)
            view.set_lines([(float(i), f"line {i}") for i in range(10)])
            await pilot.pause()

            view.set_active(0)
            await pilot.pause(0.05)
            rows = _visible_rows(view)
            assert str(rows[0].render()).strip() == "line 0"
            assert rows[0].has_class("-active")

            view.set_active(2)
            for _ in range(20):
                await pilot.pause(0.05)
            rows = _visible_rows(view)
            assert str(rows[0].render()).strip() == "line 2"
            assert rows[0].has_class("-active")
            assert not rows[1].has_class("-active")

    asyncio.run(scenario())


def test_lyric_view_show_message_hides_lyric_rows() -> None:
    async def scenario() -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            view = app.query_one("#lyrics", LyricView)
            view.set_lines([(float(i), f"line {i}") for i in range(5)])
            await pilot.pause()
            view.show_message("no lyrics")
            await pilot.pause()
            assert _visible_rows(view) == []

    asyncio.run(scenario())


def test_lyric_view_respects_anim_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LYRIC_LILY_ANIM_ENABLED", "0")

    async def scenario() -> None:
        app = _Harness()
        async with app.run_test() as pilot:
            view = app.query_one("#lyrics", LyricView)
            assert view._anim_enabled is False
            view.set_lines([(float(i), f"line {i}") for i in range(5)])
            await pilot.pause()
            view.set_active(0)
            view.set_active(1)
            await pilot.pause()
            rows = _visible_rows(view)
            assert str(rows[0].render()).strip() == "line 1"

    asyncio.run(scenario())
