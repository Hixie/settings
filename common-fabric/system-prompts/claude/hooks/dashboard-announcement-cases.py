#!/usr/bin/env python3
"""Cases for dashboard-announcement.py, the hook that tells the session when
the dashboard announcement changes.

Run it with no arguments. It points the hook at a temporary home directory
with HOME, writes the message file there, hands the hook one payload per
step, and checks the context each step adds. It reports one line per case.
The exit status is 0 when every case passed and 1 otherwise.
"""

import fcntl
import json
import os
import subprocess
import sys
import tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "dashboard-announcement.py")

NEW = "New dashboard announcement: "
CLEARED = "(The dashboard announcement has been cleared.)"

# (description, message file contents or None for no file, hook event,
# whether a subagent made the tool call, context the step is to add or None
# for none)
STEPS = [
    ("no message file in a new session", None, "UserPromptSubmit", False, None),
    ("blank message", "", "PostToolUse", False, None),
    ("whitespace-only message", " \n", "PostToolUse", False, None),
    ("message appears after a tool call", "Main is red.\n", "PostToolUse", False,
     NEW + "Main is red."),
    ("same message", "Main is red.", "PostToolUse", False, None),
    ("same message at a prompt", "  Main is red.\n\n", "UserPromptSubmit", False, None),
    ("message changes at a prompt", "Main is green.", "UserPromptSubmit", False,
     NEW + "Main is green."),
    ("subagent tool call after a change", "Main is red.", "PostToolUse", True, None),
    ("main tool call after the subagent's", "Main is red.", "PostToolUse", False,
     NEW + "Main is red."),
    ("multi-line and non-ASCII message", "Déploiement\nlundi 🚀", "PostToolUse", False,
     NEW + "Déploiement\nlundi 🚀"),
    ("message file removed", None, "PostToolUse", False, CLEARED),
    ("still cleared", "", "PostToolUse", False, None),
    ("message reappears", "Main is red.", "PostToolUse", False, NEW + "Main is red."),
]


def start_hook(home, event="PostToolUse", subagent=False):
    payload = {"session_id": "cases",
               "transcript_path": os.path.join(home, "session.jsonl"),
               "hook_event_name": event}
    if subagent:
        payload["agent_id"] = "subagent"
    hook = subprocess.Popen([sys.executable, HOOK], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, env={**os.environ, "HOME": home})
    hook.stdin.write(json.dumps(payload))
    hook.stdin.close()
    return hook


def finish_hook(hook, event="PostToolUse"):
    stdout, stderr = hook.stdout.read(), hook.stderr.read()
    if hook.wait() != 0:
        return "exit status %d: %s" % (hook.returncode, stderr)
    if not stdout:
        return None
    output = json.loads(stdout)["hookSpecificOutput"]
    if output["hookEventName"] != event:
        return "wrong hookEventName: %r" % output["hookEventName"]
    return output["additionalContext"]


def message_path(home):
    return os.path.join(home, ".cache", "dashboard-message.txt")


def write_message(home, contents):
    path = message_path(home)
    if contents is None:
        if os.path.exists(path):
            os.remove(path)
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(contents)


def waits_for_writer():
    """Holds an exclusive lock on a half-written message file while the hook
    starts, then finishes the message and releases the lock. Returns whether
    the hook was still running a second after it started, and the context it
    added."""
    with tempfile.TemporaryDirectory() as home:
        write_message(home, "")
        with open(message_path(home), "r+", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write("Half")
            f.flush()
            hook = start_hook(home)
            try:
                hook.wait(1)
                waited = False
            except subprocess.TimeoutExpired:
                waited = True
            f.write(" and whole")
        return waited, finish_hook(hook)


def parallel_hooks(count):
    """Runs the hook for COUNT parallel tool calls after a change and
    returns how many of them added context."""
    with tempfile.TemporaryDirectory() as home:
        write_message(home, "Parallel")
        hooks = [start_hook(home) for _ in range(count)]
        return sum(1 for hook in hooks if finish_hook(hook))


def check(description, expected, actual):
    print("%s %s" % ("PASS" if expected == actual else "FAIL", description))
    if expected != actual:
        print("  expected %r, got %r" % (expected, actual))
    return expected == actual


def main():
    passed = True
    with tempfile.TemporaryDirectory() as home:
        for description, contents, event, subagent, expected in STEPS:
            write_message(home, contents)
            actual = finish_hook(start_hook(home, event, subagent), event)
            passed &= check(description, expected, actual)
    passed &= check("waits for a writer holding the lock",
                    (True, NEW + "Half and whole"), waits_for_writer())
    passed &= check("parallel tool calls report a change once", 1,
                    parallel_hooks(16))
    sys.exit(0 if passed else 1)


main()
