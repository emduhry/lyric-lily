# lyric-lily

Terminal lyrics app for **Linux** first: sync with your local player (MPRIS / `playerctl`), resolve lyrics from reliable sources (LRCLIB, syncedlyrics, files), and show them in the terminal with Textual.

This is **not** a fork of [tacos-terminal-lyrics](https://github.com/tacosontitan/tacos-terminal-lyrics) (TTL). TTL is fine to skim for ideas (LRC handling, MPRIS patterns); lyric-lily aims for simpler onboarding, clearer errors, and room to grow.

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

If several MPRIS clients are running, pin one by name (as reported by `playerctl -l`):

```bash
export LYRIC_LILY_PLAYERCTL_PLAYER=spotify
lyric-lily status
```

### Classic venv + `requirements.txt`

If you prefer a plain requirements file:

```bash
python3 -m venv .venv && source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m lyric_lily.main
```

Prefer **`pip install -e .`** so the `lyric-lily` entrypoint stays in sync with the repo.

## Transparency and theming

Wallpaper and window transparency are owned by your **terminal emulator**. lyric-lily can still offer **lyric colors** (ANSI / truecolor), fonts (planned), and layout padding — without claiming OS-level background control.

## Project layout

- `src/lyric_lily/` — application package (`main` CLI, `now_playing/`, `lyrics/`)
- `src/lyric_lily/lyrics/` — resolve local `.lrc` then syncedlyrics (LRCLIB first)
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

### Automation on GitHub

- **CI** (`.github/workflows/ci.yml`): when you open a PR or push to `main`, GitHub runs a small check: install the package, run `lyric-lily --help`, and byte-compile sources. If something breaks, the PR shows a failed check so you notice before merging.
- **Dependabot** (`.github/dependabot.yml`): opens monthly PRs to bump GitHub Action versions and Python dependencies — optional hygiene, not urgent.
- **Auto-closing issues**: GitHub closes an issue for you when a merged PR **description** (or title, or a commit on the default branch) contains `Closes #2` or `Fixes #2` (use the real issue number). The PR template reminds you to type that.

## Name

Previously called **my-lyrics-app**; the directory is **lyric-lily**.
