#!/usr/bin/env bash
# Create GitHub milestones M0–M6 and one tracking issue per milestone for lyric-lily.
#
# Prerequisites:
#   - gh CLI: https://cli.github.com/ (e.g. sudo apt install gh)
#   - gh auth login
#   - Git remote "origin" pointing at GitHub, OR export GITHUB_REPOSITORY=owner/repo
#
# Idempotency: skips milestones/issues that already exist (matched by title).
set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "error: gh not found. Install it (e.g. sudo apt install gh) and run gh auth login." >&2
  exit 1
fi

REPO="${GITHUB_REPOSITORY:-}"
if [[ -z "$REPO" ]]; then
  REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)"
fi
if [[ -z "$REPO" ]]; then
  echo "error: could not resolve which GitHub repo to use." >&2
  if ! git remote | grep -q .; then
    echo "hint: this clone has no git remotes. gh cannot infer the repo from the folder alone." >&2
  fi
  login="$(gh api user -q .login 2>/dev/null || true)"
  base="$(basename "$(git rev-parse --show-toplevel)" 2>/dev/null || true)"
  if [[ -n "$login" && -n "$base" ]]; then
    echo "hint: if the repo on GitHub is ${login}/${base}, run:" >&2
    echo "  GITHUB_REPOSITORY=${login}/${base} ./scripts/bootstrap_github_plan.sh" >&2
    echo "or add origin and re-run:" >&2
    echo "  git remote add origin https://github.com/${login}/${base}.git" >&2
  else
    echo "fix: export GITHUB_REPOSITORY=owner/repo   OR   git remote add origin https://github.com/OWNER/REPO.git" >&2
  fi
  exit 1
fi

echo "Using repository: $REPO" >&2

milestone_number() {
  local title="$1"
  local t n
  while IFS=$'\t' read -r t n; do
    [[ "$t" == "$title" ]] || continue
    echo "$n"
    return 0
  done < <(gh api "repos/${REPO}/milestones" --paginate --jq -r '.[] | "\(.title)\t\(.number)"')
}

ensure_milestone() {
  local title="$1"
  local desc="$2"
  local num
  num="$(milestone_number "$title")"
  if [[ -n "$num" ]]; then
    echo "  milestone exists: $title (#$num)" >&2
    echo "$num"
    return
  fi
  num="$(gh api "repos/${REPO}/milestones" -f title="$title" -f description="$desc" --jq .number)"
  echo "  created milestone: $title (#$num)" >&2
  echo "$num"
}

issue_exists() {
  local title="$1"
  gh issue list --repo "$REPO" --state all --limit 500 --json title --jq '.[].title' | grep -Fxq "$title"
}

create_issue() {
  local title="$1"
  local body="$2"
  local milestone_title="$3"
  if issue_exists "$title"; then
    echo "  issue exists: $title" >&2
    return
  fi
  gh issue create --repo "$REPO" --title "$title" --body "$body" --milestone "$milestone_title" >/dev/null
  echo "  created issue: $title" >&2
}

M0_TITLE="M0 — Skeleton & packaging"
M0_BODY="$(cat <<'EOF'
## Goal
Ship a minimal install story: `pyproject.toml`, README, and a single CLI entrypoint so `pip install -e .` / pipx works.

## Acceptance
- [ ] `lyric-lily` console script runs (stub is fine)
- [ ] README documents Python 3.12+, `python3`, system deps (playerctl, ffmpeg), venv and pipx paths
- [ ] No false claims about Spotify-internal lyrics unless implemented

## Notes
Project was briefly **my-lyrics-app**; repo folder **lyric-lily**.
EOF
)"

M1_TITLE="M1 — Linux now playing (MPRIS / playerctl)"
M1_BODY="$(cat <<'EOF'
## Goal
Read **title, artist, position, play state** from the local player on Linux via MPRIS / `playerctl`.

## Acceptance
- [ ] Module boundary so Windows/macOS can add other “now playing” backends later
- [ ] Clear errors when dbus/playerctl is missing or the player is not running
- [ ] No lyrics requirement yet — prove the sync loop and config

## Context
Design Linux-first; abstract transport so other OSes are not blocked forever.
EOF
)"

M2_TITLE="M2 — Lyric resolution (files + LRCLIB / syncedlyrics)"
M2_BODY="$(cat <<'EOF'
## Goal
Pluggable lyric sources: local `.lrc` / on-disk files first, then LRCLIB / **syncedlyrics** (already a dependency).

## Acceptance
- [ ] Deterministic source order and logging of which source supplied the lyric file
- [ ] Do not promise “Spotify’s internal lyric API” unless actually integrated

## Context
Lyrics should come from **reliable** external/file sources; Spotify desktop + Spicetify remains the playback stack via MPRIS.
EOF
)"

M3_TITLE="M3 — Timing + Textual UI v1"
M3_BODY="$(cat <<'EOF'
## Goal
Textual UI: highlight or scroll the active line from LRC timestamps; basic theming from config.

## Acceptance
- [ ] More accurate timing than “good enough” hacks where feasible; document known limits
- [ ] **Empty state**: message matches the real outcome (e.g. “no synced lyrics found”), not a generic “Spotify” blame unless Spotify was queried
- [ ] Configurable lyric colors (ANSI / truecolor)

## Context
Quality bar: fewer bugs, clearer errors than ad-hoc terminal lyric tools.
EOF
)"

M4_TITLE="M4 — Spotify desktop + Spicetify polish"
M4_BODY="$(cat <<'EOF'
## Goal
Tune edge cases for **Spotify desktop + Spicetify** on Linux: ads, skips, seeks, client quirks.

## Acceptance
- [ ] Optional Spotipy only where it adds real value; document auth if used
- [ ] Playback sync remains anchored to MPRIS/playerctl for local client truth

## Context
Avoid expanding scope to mirror TTL; focus on solid behavior for your stack.
EOF
)"

M5_TITLE="M5 — Fonts: presets + extensible definitions"
M5_BODY="$(cat <<'EOF'
## Goal
Several **font presets** and an extensible way to define synced on-screen lyric typography within terminal/Textual constraints.

## Acceptance
- [ ] Multiple presets shipped; config overrides documented
- [ ] Honest limits: terminal + emulator capabilities cap what “fonts” can mean

## Context
Go further than TTL UX-wise where it makes sense — without copying TTL wholesale.
EOF
)"

M6_TITLE="M6 — Power-user config + advanced LRC"
M6_BODY="$(cat <<'EOF'
## Goal
Layered configuration: simple defaults, depth for power users; optional WLRC / advanced LRC handling **after** core path is stable.

## Acceptance
- [ ] Defaults work out of the box; advanced keys documented
- [ ] Advanced format support does not regress the simple case

## Context
Product shape: **simple defaults, depth in config** — keep changes focused as the repo grows.
EOF
)"

echo "Ensuring milestones..." >&2
ensure_milestone "$M0_TITLE" "Packaging, README, single CLI entrypoint." >/dev/null
ensure_milestone "$M1_TITLE" "MPRIS/playerctl now playing + position on Linux." >/dev/null
ensure_milestone "$M2_TITLE" "File + LRCLIB/syncedlyrics resolution pipeline." >/dev/null
ensure_milestone "$M3_TITLE" "Textual UI, timing, colors, honest empty states." >/dev/null
ensure_milestone "$M4_TITLE" "Spotify + Spicetify edge cases and polish." >/dev/null
ensure_milestone "$M5_TITLE" "Font presets and extensible definitions." >/dev/null
ensure_milestone "$M6_TITLE" "Layered config; advanced LRC when stable." >/dev/null

echo "Creating issues (if missing)..." >&2
create_issue "Track: $M0_TITLE" "$M0_BODY" "$M0_TITLE"
create_issue "Track: $M1_TITLE" "$M1_BODY" "$M1_TITLE"
create_issue "Track: $M2_TITLE" "$M2_BODY" "$M2_TITLE"
create_issue "Track: $M3_TITLE" "$M3_BODY" "$M3_TITLE"
create_issue "Track: $M4_TITLE" "$M4_BODY" "$M4_TITLE"
create_issue "Track: $M5_TITLE" "$M5_BODY" "$M5_TITLE"
create_issue "Track: $M6_TITLE" "$M6_BODY" "$M6_TITLE"

echo "Done. Milestones: https://github.com/${REPO}/milestones" >&2
