# lyric-lily

Terminal lyrics app for **Linux** first: sync with your local player (MPRIS / `playerctl`), resolve lyrics from reliable sources (LRCLIB, syncedlyrics, files), and show them in the terminal with Textual.

lyric-lily was inspired by tacos-terminal-lyrics, which I originally discovered through TikTok. The core idea is very similar — displaying synced lyrics in the terminal — but lyric-lily is more of a personal reinterpretation of the concept with a different UI style, architecture, and feature direction.

## Requirements

- **Python 3.12+** (on many distros the binary is `python3`, not `python`)
- **System tools** (install via your package manager):
  - **`playerctl`** — MPRIS “now playing” and position on Linux (core integration path)
  - **`ffmpeg`** — useful for future audio/metadata workflows; document early so beginners install once

Optional: **Spotify** desktop + **Spicetify** — supported stack; lyrics still come from LRCLIB / syncedlyrics / local files unless we explicitly add another source.

## Install (one path)

### Editable install (development)

```bash
cd ~/projects/lyric-lily
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -U pip
python3 -m pip install -e .
lyric-lily
```

**If `pip install` says “externally-managed-environment” (PEP 668)** while the prompt shows `(.venv)`, your shell is **not** using the venv’s Python (broken or stale venv — e.g. after renaming `my-lyrics-app` → `lyric-lily`). Check:

```bash
which python3    # should be .../lyric-lily/.venv/bin/python3
```

If it shows `/usr/bin/python3`, recreate the environment and reinstall:

```bash
cd ~/projects/lyric-lily
deactivate 2>/dev/null || true
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
which python3
python3 -m pip install -U pip
python3 -m pip install -e .
```

You can also call tools **without** activating, which avoids a broken `PATH`:

```bash
./.venv/bin/python -m pip install -e .
./.venv/bin/lyric-lily status
```

### Run tests (optional)

```bash
python3 -m pip install -e ".[dev]"
pytest -q
```

### pipx (when you publish or install from a VCS URL)

```bash
pipx install .
# or, once on PyPI:
# pipx install lyric-lily
```

After install, the CLI is **`lyric-lily`**.

### Commands

**Now playing (playerctl)**

```bash
lyric-lily status          # one Rich table snapshot
lyric-lily status --json   # JSON for scripts
lyric-lily watch           # poll until Ctrl+C (proves the sync loop)
```

**Live UI (M3 — Textual, synced highlight)**

```bash
lyric-lily ui                 # full-screen lyrics; q to quit
lyric-lily ui --local-only    # no network (local .lrc only)
lyric-lily ui --offset 0.75   # advance lyric timing by 0.75s
lyric-lily ui --theme vapor   # use a built-in or custom theme
```

Poll rate defaults to **5 Hz**; override with **`LYRIC_LILY_UI_POLL_HZ`** (e.g. `10` for snappier sync). If a lyric source is consistently early/late, calibrate with **`--offset SEC`** or **`LYRIC_LILY_SYNC_OFFSET_SEC`**. Positive values advance lyrics; negative values delay them.

Lyric transitions are animated by default with active-line pop, per-letter
shimmer/dance, and a fade gradient. Tweak with:

- **`LYRIC_LILY_ANIM_ENABLED`** — `0` disables the per-letter shimmer for slow terminals (pop + fade still apply).

**Themes**

Built-in themes ship with lyric-lily:

```bash
lyric-lily themes
lyric-lily ui --theme vapor
lyric-lily ui --theme mono
lyric-lily ui --theme ember
lyric-lily ui --theme tropic
lyric-lily ui --theme pastel_kiss
lyric-lily ui --theme lilys_pick
lyric-lily ui --theme cedar
lyric-lily ui --theme aero_sky
lyric-lily ui --theme beach_peace
lyric-lily ui --theme verbena
```

Set a default theme, or define custom themes, in
`~/.config/lyric-lily/config.toml`:

```toml
[theme]
active = "ember"

[theme.custom.ocean]
background = "#050E14"
active_lyric = "#00FFFF"
near_lyric = "#0099AA"
far_lyric = "#003344"
meta = "#4488AA"
source = "#224455"
```

`--theme NAME` overrides the config default for that run. Custom themes can use
any name; if a custom theme uses a built-in name, the custom values win. Theme
colors must be `#RRGGBB` hex values. `background` is optional; if omitted,
lyric-lily uses the default dark background. Terminal opacity is still controlled
by your terminal emulator, such as Ghostty's `background-opacity`.

**Lyrics (M2 — local `.lrc` first, then syncedlyrics / LRCLIB-style)**

```bash
lyric-lily lyrics                 # headline + short LRC preview
lyric-lily lyrics --full          # entire LRC
lyric-lily lyrics --json          # JSON (includes `lrc_text` when found)
lyric-lily lyrics --local-only    # no network; only disk
```

Local search looks for likely filenames (for example `Artist - Title.lrc`, `Title.lrc`) under, in order:

- Paths in **`LYRIC_LILY_LRC_DIRS`** (same separator as `PATH` on your OS),
- `$XDG_CONFIG_HOME/lyric-lily/lrc` (usually `~/.config/lyric-lily/lrc`),
- `./lyrics` and `./.lyrics` (relative to the current working directory).

Remote search uses the **[syncedlyrics](https://github.com/moehrenzahn/syncedlyrics)** package with **LRCLIB.net first**, then other built-in providers one at a time, so the app can say **“Lyrics from: …”** honestly. It does **not** use Spotify’s private in-client lyric API.

If several MPRIS clients are running, lyric-lily reads whichever one `playerctl`
selects by default. That can be Chrome/YouTube instead of Spotify, so the UI may
show a video title and "No synced lyrics found." List available players and pin
the one you want by name:

```bash
playerctl -l
export LYRIC_LILY_PLAYERCTL_PLAYER=spotify
lyric-lily ui
```

Use the exact name from `playerctl -l` if it differs, for example
`spotify`, `spotifyd`, or `chromium.instance1234`. The same setting also
applies to `lyric-lily status`, `lyric-lily watch`, and `lyric-lily lyrics`.

### Classic venv + `requirements.txt`

If you prefer a plain requirements file:

```bash
python3 -m venv .venv && source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m lyric_lily.main
```

Prefer **`pip install -e .`** so the `lyric-lily` entrypoint stays in sync with the repo.

## Transparency and terminal background

lyric-lily renders its Textual UI with transparent app backgrounds, but the
actual window color and opacity are owned by your **terminal emulator** and your
desktop compositor. If the UI appears as a solid black rectangle, that is the
terminal profile background showing through.

Recommended setup:

1. Pick a lyric-lily theme:

   ```bash
   lyric-lily ui --theme ember
   ```

2. Set your terminal profile background color to black (`#000000`) or to a dark
   color that matches the theme.
3. Set terminal opacity/transparency in the terminal profile or config.

Common terminal places to look:

- GNOME Terminal / Tilix / MATE Terminal: profile preferences, Colors,
  "Use transparent background" or transparency slider.
- KDE Konsole: Settings, Edit Current Profile, Appearance, edit color scheme,
  Background transparency.
- Xfce Terminal: Preferences, Appearance, Background, Transparent background.
- Kitty: set `background #000000` and `background_opacity 0.80` in
  `~/.config/kitty/kitty.conf`.
- Alacritty: set `window.opacity = 0.80` and theme colors in
  `~/.config/alacritty/alacritty.toml`.
- WezTerm: set `window_background_opacity = 0.80` and `colors.background`
  in `~/.wezterm.lua`.

lyric-lily themes control the app background plus current lyric, nearby lyrics,
faded lyrics, metadata, and source text. Terminal opacity is still handled by
the terminal.

## Project layout

- `src/lyric_lily/` — application package (`main` CLI, `now_playing/`, `lyrics/`)
- `src/lyric_lily/lrc_sync.py` — parse LRC timestamps, pick active line from playback position
- `src/lyric_lily/ui/` — Textual `lyric-lily ui`
- `pyproject.toml` — package metadata and the `lyric-lily` console script

## GitHub milestones and issues

If the repo has a GitHub remote and you use the [`gh` CLI](https://cli.github.com/):

```bash
sudo apt install gh   # Debian/Ubuntu example
gh auth login
# add origin, then:
./scripts/bootstrap_github_plan.sh
```

If you have not added a remote yet, point the script at the GitHub repo explicitly (replace `youruser` if needed):

```bash
GITHUB_REPOSITORY=youruser/lyric-lily ./scripts/bootstrap_github_plan.sh
```

The script creates milestones **M0–M6** and matching issues (skips duplicates if you re-run it). See the script header for `GITHUB_REPOSITORY` when `gh repo view` cannot infer the repo.

**Milestone issues (quick map):** **#1** M0 packaging, **#2** M1 playerctl, **#3** M2 lyric resolution, **#4** M3 Textual UI — use `Closes #N` in commit messages on `main` so the board stays accurate.

### Automation on GitHub

- **CI** (`.github/workflows/ci.yml`): on push/PR to `main`, installs with dev deps, runs **`pytest`**, **`lyric-lily --help`** / **`lyric-lily ui --help`**, and **`compileall`** on `src/lyric_lily`.
- **Dependabot** (`.github/dependabot.yml`): opens monthly PRs to bump GitHub Action versions and Python dependencies — optional hygiene, not urgent.
- **Auto-closing issues**: GitHub closes an issue for you when a merged PR **description** (or title, or a commit on the default branch) contains `Closes #2` or `Fixes #2` (use the real issue number). The PR template reminds you to type that.

## Name

Previously called **my-lyrics-app**; the directory is **lyric-lily**.
