from __future__ import annotations

import bisect
import re
from typing import Final

# [m:ss] or [m:ss.xx] or [mm:ss.xx] — lyric line (not [ar:...] metadata)
_SYNC_LINE: Final[re.Pattern[str]] = re.compile(
    r"^\[(\d{1,3}):(\d{2})(?:\.(\d{1,3}))?\]\s*(.*)\s*$"
)


def parse_synced_lrc(lrc_text: str) -> list[tuple[float, str]]:
    """Return ordered (seconds_from_start, lyric_text) for standard LRC timestamp lines."""
    out: list[tuple[float, str]] = []
    for raw in lrc_text.splitlines():
        m = _SYNC_LINE.match(raw.strip())
        if not m:
            continue
        mins, secs, frac, text = m.group(1), m.group(2), m.group(3), m.group(4)
        t = int(mins) * 60 + int(secs)
        if frac is not None:
            pad = frac.ljust(3, "0")[:3]
            t += int(pad) / 1000.0
        if text:
            out.append((float(t), text))
    return out


def line_index_at(lines: list[tuple[float, str]], position_sec: float) -> int:
    """
    Index of the line that should be highlighted at ``position_sec``
    (last line with timestamp <= position), or -1 if before the first timestamp.
    """
    if not lines:
        return -1
    times = [t for t, _ in lines]
    i = bisect.bisect_right(times, position_sec) - 1
    return i if i >= 0 else -1
