from __future__ import annotations

import argparse
import json
import os
import sys
import time

from rich.console import Console
from rich.table import Table

from lyric_lily import __version__
from lyric_lily.lyrics import resolve_lyrics
from lyric_lily.lrc_sync import line_index_at, parse_synced_lrc
from lyric_lily.now_playing import (
    PlaybackUnavailableError,
    PlaybackSnapshot,
    default_backend,
)

err_console = Console(stderr=True)
out_console = Console()


def _snapshot_table(snap: PlaybackSnapshot) -> Table:
    t = Table(show_header=False, box=None, padding=(0, 1))
    t.add_column(style="dim")
    t.add_column()
    t.add_row("state", snap.state.value)
    t.add_row("title", snap.title or "—")
    t.add_row("artist", snap.artist or "—")
    t.add_row("album", snap.album or "—")
    pos = f"{snap.position_sec:.1f}s"
    if snap.duration_sec is not None:
        pos += f" / {snap.duration_sec:.1f}s"
    t.add_row("position", pos)
    t.add_row("player", snap.player_name or "(playerctl default)")
    return t


def cmd_status(json_out: bool) -> int:
    try:
        snap = default_backend().read()
    except NotImplementedError as e:
        err_console.print(f"[red]{e}[/]")
        return 2
    except PlaybackUnavailableError as e:
        err_console.print(f"[red]{e}[/]")
        return 1
    if json_out:
        print(json.dumps(snap.as_dict(), indent=2))
        return 0
    out_console.print(_snapshot_table(snap))
    return 0


def cmd_watch(interval: float) -> int:
    try:
        backend = default_backend()
    except NotImplementedError as e:
        err_console.print(f"[red]{e}[/]")
        return 2
    out = Console()
    try:
        while True:
            try:
                snap = backend.read()
            except PlaybackUnavailableError as e:
                err_console.print(f"[dim]{e}[/]")
            else:
                line = " · ".join(
                    p
                    for p in (
                        snap.state.value.upper(),
                        snap.artist or "?",
                        snap.title or "?",
                        f"{snap.position_sec:.1f}s",
                    )
                    if p
                )
                out.print(line, end="\r")
            time.sleep(max(0.1, interval))
    except KeyboardInterrupt:
        out.print()
        return 0


def _lrc_preview(text: str, max_lines: int = 20) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    tail = len(lines) - max_lines
    return "\n".join(lines[:max_lines]) + f"\n… ({tail} more lines; use --full)"


def _sync_debug_table(
    snap: PlaybackSnapshot,
    lrc_text: str,
    *,
    sync_offset_sec: float,
) -> Table:
    lines = parse_synced_lrc(lrc_text)
    adjusted_position_sec = max(0.0, snap.position_sec + sync_offset_sec)
    active = line_index_at(lines, adjusted_position_sec)
    t = Table(show_header=False, box=None, padding=(0, 1))
    t.add_column(style="dim")
    t.add_column()
    t.add_row("player position", f"{snap.position_sec:.3f}s")
    t.add_row("lyric position", f"{adjusted_position_sec:.3f}s")
    t.add_row("offset", f"{sync_offset_sec:+.3f}s")
    t.add_row("parsed lines", str(len(lines)))
    if active >= 0:
        ts, text = lines[active]
        t.add_row("active", f"{active}: [{ts:.2f}s] {text}")
    else:
        t.add_row("active", "(before first parsed line)")
    for index in range(max(0, active + 1), min(len(lines), max(0, active + 1) + 5)):
        ts, text = lines[index]
        t.add_row("next", f"{index}: [{ts:.2f}s] {text}")
    return t


def cmd_lyrics(
    *,
    full: bool,
    json_out: bool,
    local_only: bool,
    sync_debug: bool,
    sync_offset_sec: float,
) -> int:
    try:
        snap = default_backend().read()
    except NotImplementedError as e:
        err_console.print(f"[red]{e}[/]")
        return 2
    except PlaybackUnavailableError as e:
        err_console.print(f"[red]{e}[/]")
        return 1

    result = resolve_lyrics(snap, local_only=local_only)
    if json_out:
        print(json.dumps(result.as_dict(), indent=2))
        return 0 if result.found else 1

    style = "green bold" if result.found else "yellow"
    out_console.print(result.headline, style=style)
    out_console.print(result.detail, style="dim")
    if result.lrc_text:
        if sync_debug:
            out_console.print(_sync_debug_table(snap, result.lrc_text, sync_offset_sec=sync_offset_sec))
        body = result.lrc_text if full else _lrc_preview(result.lrc_text)
        out_console.print(body)
    return 0 if result.found else 1


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{name} must be a number, got {raw!r}")


def cmd_ui(local_only: bool, sync_offset_sec: float, theme_name: str | None) -> int:
    from lyric_lily.ui.app import run_ui

    try:
        return run_ui(
            local_only=local_only,
            sync_offset_sec=sync_offset_sec,
            theme_name=theme_name,
        )
    except ValueError as e:
        err_console.print(f"[red]{e}[/]")
        return 2


def cmd_themes() -> int:
    from lyric_lily.themes import iter_themes_with_default

    t = Table(show_header=True)
    t.add_column("theme")
    t.add_column("default", justify="center")
    for name, is_default in iter_themes_with_default():
        t.add_row(name, "yes" if is_default else "")
    out_console.print(t)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lyric-lily",
        description="Terminal lyrics — Linux MPRIS (playerctl), lyric lookup, Textual UI.",
        epilog="Tip: run `lyric-lily ui` for the live synced-lyrics screen (press q to quit).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    p_status = sub.add_parser("status", help="print one playback snapshot (playerctl)")
    p_status.add_argument(
        "--json",
        action="store_true",
        help="machine-readable JSON",
    )

    p_watch = sub.add_parser(
        "watch",
        help="poll playerctl and print a one-line status (Ctrl+C to stop)",
    )
    p_watch.add_argument(
        "-n",
        "--interval",
        type=float,
        default=1.0,
        metavar="SEC",
        help="poll interval in seconds (default: 1.0)",
    )

    p_lyrics = sub.add_parser(
        "lyrics",
        help="resolve synced LRC for the current track (local .lrc first, then syncedlyrics)",
    )
    p_lyrics.add_argument(
        "--full",
        action="store_true",
        help="print the entire LRC (default: first lines only)",
    )
    p_lyrics.add_argument(
        "--json",
        action="store_true",
        help="machine-readable JSON (includes lrc_text when found)",
    )
    p_lyrics.add_argument(
        "--local-only",
        action="store_true",
        help="only search local .lrc files (no network)",
    )
    p_lyrics.add_argument(
        "--sync-debug",
        action="store_true",
        help="show parsed LRC timing around the current playback position",
    )
    p_lyrics.add_argument(
        "--offset",
        type=float,
        default=_env_float("LYRIC_LILY_SYNC_OFFSET_SEC", 0.0),
        metavar="SEC",
        help="debug lyric timing with the same offset used by the UI",
    )

    p_ui = sub.add_parser(
        "ui",
        help="Textual synced lyrics view (polls playerctl; q to quit)",
    )
    p_ui.add_argument(
        "--local-only",
        action="store_true",
        help="only load local .lrc files (no network)",
    )
    p_ui.add_argument(
        "--offset",
        type=float,
        default=_env_float("LYRIC_LILY_SYNC_OFFSET_SEC", 0.0),
        metavar="SEC",
        help="shift lyric timing by seconds; positive advances lyrics, negative delays them",
    )
    p_ui.add_argument(
        "--theme",
        metavar="NAME",
        help="use a built-in or custom theme; overrides config default",
    )

    sub.add_parser(
        "themes",
        help="list built-in and custom themes",
    )

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(0)
    if args.command == "status":
        sys.exit(cmd_status(args.json))
    if args.command == "watch":
        sys.exit(cmd_watch(args.interval))
    if args.command == "lyrics":
        sys.exit(
            cmd_lyrics(
                full=args.full,
                json_out=args.json,
                local_only=args.local_only,
                sync_debug=args.sync_debug,
                sync_offset_sec=args.offset,
            )
        )
    if args.command == "ui":
        sys.exit(cmd_ui(args.local_only, args.offset, args.theme))
    if args.command == "themes":
        sys.exit(cmd_themes())
    parser.error(f"unknown command {args.command!r}")


if __name__ == "__main__":
    main()
