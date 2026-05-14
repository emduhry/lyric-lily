# AGENTS.md — Lyric-Lily Project Knowledge Base

This document serves as the single source of truth for all AI agents working on the **lyric-lily** project.

## 1. Project Overview
**lyric-lily** is a terminal-based lyrics application designed primarily for Linux users. It synchronizes with local media players via MPRIS/`playerctl` to display real-time, synced lyrics in the terminal using the Textual TUI framework.

- **Purpose:** Provide a lightweight, beautiful, and reliable lyrics viewer for the terminal.
- **Target Users:** Linux enthusiasts, terminal users, and music listeners who want a high-quality "vibe" without leaving their CLI environment.
- **Philosophy:** Simple onboarding, clear error messages, and a focus on "vibe coding" (beautiful animations and themes).

## 2. Tech Stack
- **Python Version:** 3.12+
- **Core Libraries:**
  - `textual`: TUI framework for building the UI and animations.
  - `rich`: For terminal formatting and snapshot tables.
  - `playerctl` (System tool): Core integration path for MPRIS playback and position data.
  - `syncedlyrics`: Package used to resolve lyrics from various remote providers.
  - `spotipy`: Used for optional Spotify-specific enhancements.
  - `pytest`: For unit and integration testing.

## 3. Repository Structure
```
/home/emduhry/projects/lyric-lily/
├── pyproject.toml           # Package metadata and entry points.
├── README.md                # Project documentation and setup guide.
├── AGENTS.md                # (This file) Central knowledge base for AI agents.
├── requirements.txt         # Plain dependency list.
├── src/
│   └── lyric_lily/
│       ├── __init__.py      # Package version and initialization.
│       ├── main.py          # CLI entry point and command routing.
│       ├── config.py        # Configuration loading (TOML) and management.
│       ├── themes.py        # Theme registry and palette resolution.
│       ├── lrc_sync.py      # LRC timestamp parsing and active line logic.
│       ├── lyrics/          # Lyric resolution subsystem.
│       │   ├── local_lrc.py # Local .lrc file searching logic.
│       │   ├── remote.py    # Remote lyric fetching (syncedlyrics).
│       │   ├── resolver.py  # Orchestrates local vs remote lyric lookups.
│       │   └── types.py     # Data classes for lyric resolution results.
│       ├── now_playing/     # Playback state subsystem.
│       │   ├── types.py     # Data classes for playback snapshots.
│       │   ├── errors.py    # Playback-related error definitions.
│       │   └── backends/    # Pluggable backends (Linux playerctl first).
│       └── ui/              # Textual TUI implementation.
│           ├── app.py       # Main Textual App class and poll loop.
│           ├── lyric_view.py# Custom widget for synced lyric scrolling.
│           └── render.py    # Logic for lyric line styling and windows.
├── tests/                   # Comprehensive test suite (pytest).
└── scripts/
    └── bootstrap_github_plan.sh # Automation for GitHub milestones/issues.
```

## 4. Architecture Overview
1. **Player Detection:** The `now_playing` subsystem uses `playerctl` (via `LinuxPlayerctlBackend`) to poll the current media player for title, artist, playback state, and position.
2. **Lyric Fetching:** The `lyrics` subsystem (orchestrated by `resolve_lyrics`) first searches local directories for `.lrc` files. If not found, it uses `syncedlyrics` to fetch from remote providers like LRCLIB.
3. **UI Rendering:** The `LyricLilyApp` (Textual) runs a high-frequency poll loop (5Hz+). It updates a local clock to ensure smooth movement even when player updates are infrequent. The `LyricView` widget scrolls and highlights the active line based on current playback position.

## 5. Current Implementation Status
- **Works:** MPRIS/playerctl integration, local/remote lyric resolution, theme loading, synced UI with animations, local position clock.
- **In Progress:** Custom theme testing on Linux UI (verified via CLI).
- **Missing/Future:** Advanced WLRC support, power-user config depth, font presets (M5), complex Spotify edge case handling (M4).

## 6. Open GitHub Issues Summary
- **#1 M0 — Skeleton & packaging:** Minimal install story via `pyproject.toml`.
- **#2 M1 — Linux now playing:** MPRIS/playerctl integration.
- **#3 M2 — Lyric resolution:** Local/remote resolution pipeline.
- **#4 M3 — Timing + Textual UI v1:** Core Textual UI and timing logic.

## 7. Color Themes
| Theme | Background | Active Lyric | Near Lyric | Far Lyric | Meta | Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **tropic** | `#0D2926` | `#B2E8DF` | `#1DB39E` | `#0F4A40` | `#F5A623` | `#3A5E58` |
| **pastel_kiss**| `#1A1220` | `#F5C8D8` | `#D9637A` | `#4A2535` | `#A8D8D8` | `#2E3040` |
| **lilys_pick** | `#1A1018` | `#F4C9B0` | `#C8808A` | `#3D2535` | `#E8A090` | `#302030` |
| **cedar** | `#1A1E12` | `#C0C48A` | `#5E6B40` | `#2D3820` | `#A89060` | `#252A18` |
| **aero_sky** | `#0E1A2E` | `#C8E8F8` | `#88B8D8` | `#1A2A5A` | `#B8E8B8` | `#0E1E30` |
| **beach_peace**| `#050E14` | `#7AD8F0` | `#20A8C8` | `#0A2A38` | `#1A7898` | `#071820` |
| **verbena** | `#120A1C` | `#D0B0E8` | `#A878C8` | `#2A1040` | `#F0B8D8` | `#200C35` |

*(Note: Other built-ins like `vapor`, `mono`, and `ember` are also available.)*

## 8. Agent Roster
- **Delia:** Lead Architect (Open WebUI on Mac). Handles high-level design and structure.
- **Flora:** UI and Theme Specialist (Open WebUI on Mac). Focuses on TUI aesthetics and animations.
- **Reed:** Sync Specialist (Open WebUI on Mac). Expert in playerctl and LRC timing.
- **Sage:** QA and Testing Specialist (Latitude Terminal). Runs tests and verifies Linux behavior.
- **Ivy:** Git and Documentation Specialist (Latitude Terminal). Manages the repo and AGENTS.md.

## 9. Dev Environment
- **Hardware:** MacBook Air (Powerhouse), Latitude E5470 (Linux Testing).
- **OS:** macOS (Dev), Linux Mint (Test).
- **Terminal:** Ghostty.
- **Workflow:**
  - Create and refactor code on Mac using Ollama + Qwen 2.5 7B.
  - Push to GitHub.
  - Pull and test on Latitude using the local venv: `./.venv/bin/lyric-lily ui`.

## 10. Conventions
- **Modular Backends:** All "now playing" logic must stay behind the `NowPlayingBackend` interface.
- **Clean Fallbacks:** If a theme or lyric is missing, provide a clear, helpful message in the UI.
- **Surgical Edits:** Favor precise code modifications that respect existing style.

## 11. Next Priorities
- **M4 Polish:** Tuning for Spotify + Spicetify edge cases.
- **M5 Fonts:** Exploring extensible typography within terminal constraints.
- **M6 Config:** Expanding `config.toml` to support power-user settings.
