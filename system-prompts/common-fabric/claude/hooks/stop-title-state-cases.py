#!/usr/bin/env python3
"""Cases for stop-title-state.py, the Stop hook that compares the footer
line's state emoji with the session title's.

Run it with no arguments. It writes a session record into a temporary
directory, points the hook at that directory with CLAUDE_CONFIG_DIR, hands
the hook a Stop payload on standard input, and reads the decision it
writes on standard output. It reports one line per case. The exit status
is 0 when every case decided the way it should and 1 otherwise.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "stop-title-state.py")
SESSION_ID = "stop-title-state-cases"

_spec = importlib.util.spec_from_file_location("hook", HOOK)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

FOOTER = "\n\n%s 0x94"

# (description, footer emoji or a whole message, title, entrypoint, whether
# the hook is to block)
CASES = [
    ("matching state, no worktrees", "🧱", "🧱 Fix the thing", "claude-desktop", False),
    ("matching state, worktrees", "🧱", "X3, 𝛌X3: 🧱 Fix the thing", "claude-desktop", False),
    ("matching state, summary with a colon", "💬", "💬 Review: the parser", "claude-desktop", False),
    ("matching state, one worktree with hyphen", "🐤", "labs-G7: 🐤 Fix it", "claude-desktop", False),
    ("matching state, weaver and loom worktrees", "🦚", "ωU3, λ3, 𝛌X3, INFRA2: 🦚 Fix", "claude-desktop", False),
    ("different state, weaver and loom worktrees", "🪻", "ωU3,λ3: 🦚 Fix", "claude-desktop", True),
    ("variation selector only in footer", "⚙️", "⚙ Starting", "claude-desktop", False),
    ("variation selector only in title", "⚙", "⚙️ Starting", "claude-desktop", False),
    ("different state, no worktrees", "🐤", "🧱 Fix the thing", "claude-desktop", True),
    ("different state, worktrees", "🪻", "G7: 🧱 Fix the thing", "claude-desktop", True),
    ("summary emoji is not the state", "🐤", "🧱 Make 🐤 happy", "claude-desktop", True),
    ("title without a state", "🧱", "Fix the thing", "claude-desktop", True),
    ("no title", "🧱", None, "claude-desktop", True),
    ("different state outside the desktop app", "🐤", "🧱 Fix", "cli", False),
    ("no session record", "🐤", "", None, False),
    ("joined emoji", "👩‍❤️‍👩", "👩‍❤️‍👩 Fix", "claude-desktop", False),
    ("joined emoji against its first part", "👩‍❤️‍👩", "👩 Fix", "claude-desktop", True),
    ("joined emoji after worktrees", "👩‍❤️‍👩", "G7: 👩‍❤️‍👩 Fix", "claude-desktop", False),
    ("different joined emoji", "👩‍❤️‍👩", "👨‍❤️‍👨 Fix", "claude-desktop", True),
    ("flag", "🇨🇭", "G7: 🇨🇭 Fix", "claude-desktop", False),
    ("pineapple", "🍍", "🍍 Fix", "claude-desktop", False),
]


def decide(message, title, entrypoint):
    """The hook's output, as parsed JSON, or None when it let the stop
    through, or a string when it failed."""
    with tempfile.TemporaryDirectory() as directory:
        os.mkdir(os.path.join(directory, "sessions"))
        if entrypoint is not None:
            record = {"sessionId": SESSION_ID, "entrypoint": entrypoint,
                      "updatedAt": 1}
            if title is not None:
                # The harness stores zero-width joiners as spaces.
                record["name"] = title.replace(hook.JOINER, " ")
            with open(os.path.join(directory, "sessions", "1.json"), "w",
                      encoding="utf-8") as handle:
                json.dump(record, handle)
        payload = {"hook_event_name": "Stop", "session_id": SESSION_ID,
                   "stop_hook_active": False,
                   "last_assistant_message": message}
        finished = subprocess.run(
            [sys.executable, HOOK], input=json.dumps(payload),
            capture_output=True, text=True,
            env=dict(os.environ, CLAUDE_CONFIG_DIR=directory))
    if finished.returncode != 0:
        return "ERROR: " + finished.stderr.strip()
    body = finished.stdout.strip()
    return json.loads(body) if body else None


def check(description, message, title, entrypoint, block):
    result = decide(message, title, entrypoint)
    if isinstance(result, str):
        return False, result
    if block:
        expected = {"decision": "block", "reason": hook.REMINDER}
        return result == expected, "blocked" if result else "let through"
    return result is None, "let through" if result is None else "blocked"


def main():
    cases = [(description, "Done." + FOOTER % emoji, title, entrypoint, block)
             for description, emoji, title, entrypoint, block in CASES]
    cases += [
        ("empty message", "", "🧱 Fix", "claude-desktop", False),
        ("trailing blank lines after the footer",
         "Done.\n\n🐤 0x94\n\n  \n", "🐤 Fix", "claude-desktop", False),
        ("stale emoji earlier in the message",
         "🧱 0x94\n\n🐤 0x94", "🧱 Fix", "claude-desktop", True),
    ]
    failures = 0
    for description, message, title, entrypoint, block in cases:
        passed, outcome = check(description, message, title, entrypoint, block)
        failures += not passed
        print("%s  %s: %s" % ("ok  " if passed else "FAIL", description,
                              outcome))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
