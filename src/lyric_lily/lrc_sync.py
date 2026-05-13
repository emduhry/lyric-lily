from __future__ import annotations

import bisect
import re
from typing import Final

# [m:ss] or [m:ss.xx] or [mm:ss.xx] — lyric line (not [ar:...] metadata)
_SYNC_LINE: Final[re.Pattern[str]] = re.compile(
    r"\[(\d{1,3}):(\d{2})(?:\.(\d{1,3}))?\]"
)
_OFFSET_LINE: Final[re.Pattern[str]] = re.compile(
    r"^\[offset:\s*([+-]?\d+(?:\.\d+)?)\s*\]\s*$",
    re.IGNORECASE,
)


def parse_synced_lrc(lrc_text: str) -> list[tuple[float, str]]:
    """Return ordered (seconds_from_start, lyric_text) for standard LRC timestamp lines."""
    out: list[tuple[float, str]] = []
    offset_sec = 0.0
    for raw in lrc_text.splitlines():
        line = raw.strip()
        offset_match = _OFFSET_LINE.match(line)
        if offset_match:
            offset_sec = float(offset_match.group(1)) / 1000.0
            continue

        matches = list(_SYNC_LINE.finditer(line))
        if not matches:
            continue

        text = line[matches[-1].end() :].strip()
        if text:
            for m in matches:
                mins, secs, frac = m.group(1), m.group(2), m.group(3)
                t = int(mins) * 60 + int(secs) + offset_sec
                if frac is not None:
                    pad = frac.ljust(3, "0")[:3]
                    t += int(pad) / 1000.0
                out.append((max(0.0, float(t)), text))
    return sorted(out, key=lambda item: item[0])


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
