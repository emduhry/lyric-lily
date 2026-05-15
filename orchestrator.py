#!/usr/bin/env python3
"""
lyric-lily orchestrator
Takes a plan from Delia, assigns tasks to agents, runs Aider autonomously,
pushes to GitHub, and posts results to Discord via the agent server.

Run on your Mac:
    python3 orchestrator.py --plan "improve lyric sync accuracy"
    python3 orchestrator.py --plan "implement the cedar theme in Textual UI"
    python3 orchestrator.py --interactive  # ask Delia for a plan first
"""

import argparse
import json
import os
import subprocess
import requests
import time
from datetime import datetime

# ── config ────────────────────────────────────────────────────────────────────
REPO_PATH = os.path.expanduser("~/projects/lyric-lily")
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5-coder:7b"
LATITUDE_IP = os.environ.get("LATITUDE_TAILSCALE_IP", "100.79.109.80")
LATITUDE_USER = "emduhry"
AGENT_SERVER = f"http://{LATITUDE_IP}:5555"
AUTO_PUSH = True   # set False if you want to review before pushing
AUTO_COMMIT = True

# agent → Discord channel mapping for status updates
AGENTS = {
    "delia":   "delia",
    "flora":   "flora",
    "reed":    "reed",
    "saffron": "saffron",
    "blythe":  "blythe",
}


# ── discord helpers ────────────────────────────────────────────────────────────
def post_to_agent_server(endpoint, data):
    try:
        resp = requests.post(f"{AGENT_SERVER}{endpoint}", json=data, timeout=5)
        return resp.status_code in (200, 204)
    except Exception as e:
        print(f"⚠️  Agent server unreachable: {e}")
        return False


def notify(agent, message, sender=None):
    """Post a status message to an agent's Discord channel."""
    post_to_agent_server("/reply", {
        "from": sender or agent,
        "channel": agent,
        "message": message,
    })


def broadcast(message, sender="orchestrator"):
    """Broadcast a message to all Discord channels."""
    post_to_agent_server("/broadcast", {
        "from": sender,
        "message": message,
    })


# ── ollama helpers ─────────────────────────────────────────────────────────────
def ask_ollama(system_prompt, user_message, max_tokens=2000):
    """Send a prompt to local Ollama and return the response text."""
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/chat", json={
            "model": OLLAMA_MODEL,
            "stream": False,
            "options": {"num_predict": max_tokens},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }, timeout=120)
        return resp.json()["message"]["content"].strip()
    except Exception as e:
        print(f"❌ Ollama error: {e}")
        return None


# ── git helpers ────────────────────────────────────────────────────────────────
def git(args, cwd=REPO_PATH):
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def git_status():
    _, out, _ = git(["status", "--porcelain"])
    return out


def git_commit_and_push(message):
    code, _, err = git(["add", "-A"])
    if code != 0:
        return False, err

    code, _, err = git(["commit", "-m", message])
    if code != 0:
        return False, err

    if AUTO_PUSH:
        code, _, err = git(["push"])
        if code != 0:
            return False, err

    return True, None


# ── aider helper ──────────────────────────────────────────────────────────────
def run_aider(task, files=None):
    """
    Run Aider autonomously with a task description.
    Returns (success, output).
    """
    cmd = [
        "aider",
        "--model", f"ollama/{OLLAMA_MODEL}",
        "--yes",
        "--no-pretty",
        "--message", task,
    ]

    if files:
        cmd.extend(files)

    print(f"\n🤖 Running Aider: {task[:80]}...")
    notify("delia", f"🤖 Aider starting task:\n_{task[:200]}_", sender="orchestrator")

    try:
        result = subprocess.run(
            cmd,
            cwd=REPO_PATH,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout per task
            env={**os.environ, "OLLAMA_API_BASE": "http://localhost:11434"},
        )
        success = result.returncode == 0
        output = result.stdout + result.stderr
        return success, output
    except subprocess.TimeoutExpired:
        return False, "Aider timed out after 5 minutes"
    except FileNotFoundError:
        return False, "Aider not found — run: pip install aider-chat"


# ── pytest helper ─────────────────────────────────────────────────────────────
def run_tests():
    """SSH to Latitude and run pytest there, where Linux deps are available."""
    print("🧪 Running tests on Latitude via SSH...")
    notify("saffron", "🧪 Running pytest on Latitude...", sender="orchestrator")

    try:
        result = subprocess.run(
            [
                "ssh", f"{LATITUDE_USER}@{LATITUDE_IP}",
                "cd ~/projects/lyric-lily && git pull && python3 -m pytest tests/ -v --tb=short 2>&1 | tail -30"
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        passed = result.returncode == 0
        output = result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout
        return passed, output
    except Exception as e:
        return False, str(e)


# ── delia: plan generator ──────────────────────────────────────────────────────
def ask_delia_for_plan(goal):
    """Ask Delia to break down a goal into specific aider tasks."""
    print(f"\n🌸 Asking Delia to plan: {goal}")
    notify("delia", f"📋 Planning task:\n_{goal}_", sender="orchestrator")

    system = """You are Delia, lead architect for lyric-lily, a terminal lyrics app
built in Python using Textual UI, MPRIS/playerctl, and LRCLIB/syncedlyrics.
Repo structure: src/lyric_lily/ contains all source files.

When given a goal, respond with a JSON array of 1-3 tasks for Aider to execute.

STRICT RULES:
- Every task MUST modify actual Python files in src/lyric_lily/
- NO Figma, Sketch, mockups, diagrams, or design tools
- NO vague tasks — every description must say exactly what code to write or change
- NO documentation-only tasks
- Every task must be completable by a code editor with zero human input
- files[] must contain real file paths that exist in the repo

Respond with ONLY valid JSON, no markdown fences, no explanation.

Example output:
[
  {
    "agent": "reed",
    "description": "In src/lyric_lily/lyrics.py, modify the fetch_lyrics function to add a try/except around the LRCLIB API call and retry once with syncedlyrics if it raises an exception or returns an empty list",
    "files": ["src/lyric_lily/lyrics.py"]
  }
]"""

    response = ask_ollama(system, f"Goal: {goal}")
    if not response:
        return None

    # strip markdown fences if present
    response = response.strip()
    if response.startswith("```"):
        lines = response.split("\n")
        response = "\n".join(lines[1:-1])

    try:
        plan = json.loads(response)
        return plan
    except json.JSONDecodeError:
        print(f"⚠️  Delia's plan wasn't valid JSON:\n{response}")
        return None


# ── main orchestration loop ────────────────────────────────────────────────────
def run_orchestration(goal):
    start_time = datetime.now()
    print(f"\n{'='*60}")
    print(f"🌸 lyric-lily orchestrator starting")
    print(f"   Goal: {goal}")
    print(f"   Time: {start_time.strftime('%H:%M:%S')}")
    print(f"{'='*60}\n")

    broadcast(f"🚀 **Orchestrator starting**\nGoal: _{goal}_", sender="orchestrator")

    # step 1 — get plan from delia
    plan = ask_delia_for_plan(goal)
    if not plan:
        broadcast("❌ Orchestrator failed: could not generate a plan", sender="orchestrator")
        return False

    print(f"📋 Delia's plan: {len(plan)} tasks")
    plan_summary = "\n".join([f"• **{t['agent'].upper()}**: {t['description'][:80]}" for t in plan])
    notify("delia", f"📋 **Plan ready — {len(plan)} tasks:**\n{plan_summary}", sender="delia")

    # step 2 — execute each task with aider
    results = []
    for i, task in enumerate(plan):
        agent = task.get("agent", "general")
        description = task.get("description", "")
        files = task.get("files", [])

        print(f"\n[{i+1}/{len(plan)}] {agent.upper()}: {description[:60]}...")
        notify(agent, f"⚙️ **Working on task {i+1}/{len(plan)}:**\n{description}", sender=agent)

        success, output = run_aider(description, files)

        result = {
            "agent": agent,
            "task": description,
            "success": success,
            "output": output[-500:] if len(output) > 500 else output,
        }
        results.append(result)

        if success:
            changes = git_status()
            if changes:
                notify(agent, f"✅ **Task complete.** Files changed:\n```\n{changes}\n```", sender=agent)
            else:
                notify(agent, f"✅ **Task complete.** No file changes needed.", sender=agent)
        else:
            notify(agent, f"⚠️ **Task had issues:**\n```\n{output[-300:]}\n```", sender=agent)

        time.sleep(2)  # brief pause between tasks

    # step 3 — commit changes
    changes = git_status()
    if changes and AUTO_COMMIT:
        print("\n📦 Committing changes...")
        commit_msg = f"feat: {goal[:60]} (orchestrated by lyric-lily agents)"
        success, err = git_commit_and_push(commit_msg)
        if success:
            broadcast(f"📦 **Changes committed and pushed:**\n_{commit_msg}_", sender="blythe")
        else:
            broadcast(f"⚠️ **Commit failed:** {err}", sender="blythe")
    elif not changes:
        print("\nℹ️  No file changes to commit")

    # step 4 — run tests on Latitude via SSH
    print("\n🧪 Running tests...")
    tests_passed, test_output = run_tests()
    if tests_passed:
        notify("saffron", f"✅ **All tests passed!**\n```\n{test_output[-400:]}\n```", sender="saffron")
    else:
        notify("saffron", f"❌ **Some tests failed:**\n```\n{test_output[-400:]}\n```", sender="saffron")

    # step 5 — final summary
    elapsed = (datetime.now() - start_time).seconds
    passed = sum(1 for r in results if r["success"])
    summary = f"""🌸 **Orchestration complete** ({elapsed}s)
Goal: _{goal}_
Tasks: {passed}/{len(results)} succeeded
Tests: {"✅ passing" if tests_passed else "❌ failing"}"""

    broadcast(summary, sender="delia")
    print(f"\n{'='*60}")
    print(f"✅ Done in {elapsed}s — {passed}/{len(results)} tasks succeeded")
    print(f"{'='*60}\n")

    return tests_passed


# ── cli ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="lyric-lily autonomous orchestrator")
    parser.add_argument("--plan", "-p", help="Goal to work on")
    parser.add_argument("--interactive", "-i", action="store_true", help="Enter goal interactively")
    parser.add_argument("--no-push", action="store_true", help="Don't push to GitHub")
    parser.add_argument("--no-commit", action="store_true", help="Don't commit changes")
    args = parser.parse_args()

    if args.no_push:
        AUTO_PUSH = False
    if args.no_commit:
        AUTO_COMMIT = False

    if args.interactive:
        print("🌸 lyric-lily orchestrator")
        goal = input("What should the crew work on? > ").strip()
    elif args.plan:
        goal = args.plan
    else:
        parser.print_help()
        exit(1)

    run_orchestration(goal)
