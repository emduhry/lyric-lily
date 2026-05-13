from __future__ import annotations

import argparse
import json
import sys
import time

from rich.console import Console
from rich.table import Table

from lyric_lily import __version__
from lyric_lily.lyrics import resolve_lyrics
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


def cmd_lyrics(*, full: bool, json_out: bool, local_only: bool) -> int:
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
        body = result.lrc_text if full else _lrc_preview(result.lrc_text)
        out_console.print(body)
    return 0 if result.found else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lyric-lily",
        description="Terminal lyrics — Linux MPRIS (playerctl) + local/synced lyric lookup (M2).",
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
            )
        )
    parser.error(f"unknown command {args.command!r}")


if __name__ == "__main__":
    main()
