#!/usr/bin/env python3
"""Hook that tells each agent in a session when the computer runs on battery
power, and tells an agent that was told so when the computer is back on
wall power.

github-hookbar, in the contraptions repository, runs this file with
"battery" or "wall" as its argument whenever the power source changes,
once the power.run setting in github-hookbar's configuration names it. Run
that way, on wall power, it wakes the sessions that are blocked until wall
power returns.

The hook asks IOKit how long the current power source will last. IOKit
answers kIOPSTimeRemainingUnlimited (-2) when the computer draws power from
a wall outlet, which includes a computer that has no battery. On battery it
answers an estimate in seconds, or -1 while it is still estimating.

Whether an agent has been told about the battery is kept in a file in the
session's own directory next to its transcript, so it is deleted along with
the session. The main conversation's file is named "battery-notice", and a
subagent's is named "battery-notice-AGENT_ID", so each agent is told on its
own. An agent with no file has not been told. The file is locked while it
is compared and recorded, so hooks for parallel tool calls, and the hook
and github-hookbar's run of it, report each change once.

At UserPromptSubmit and PostToolUse, the hook adds the notice to the
agent's context when the power source differs from what the agent was last
told. At SessionStart, it is registered only for the moment after a
conversation is compacted or cleared, when the agent's context no longer
holds earlier notices, so the hook tells an agent on battery again and
tells an agent on wall power nothing.

An agent blocked until wall power returns says so with the state 🪫 in its
session title and footer line, and makes no prompt or tool call while it
waits. When the computer switches to wall power, "battery-notice.py wall"
finds each running Claude session that is idle with 🪫 in its title, and,
if the session was told about the battery, sends it the wall power notice
with send-claude-session. A session still working when wall power returns
is not idle then, so at Stop, when the agent's footer line says 🪫, the
computer draws wall power, and the agent was told about the battery, the
hook keeps the agent going with the wall power notice. Other sessions hear
about wall power at their next prompt or tool call.
"""

import ctypes
import fcntl
import functools
import glob
import importlib.util
import json
import os
import subprocess
import sys

BATTERY = ("This computer is running on battery power. Avoid running "
           "extensive test runs or other CPU-intensive long-running tasks. "
           "If you are blocked from progressing because of this, your state "
           "is 🪫.")
WALL = "We are now back on wall power. You may resume normal operations."

TIME_REMAINING_UNLIMITED = -2.0

CLAUDE_DIR = os.environ.get("CLAUDE_CONFIG_DIR",
                            os.path.expanduser("~/.claude"))
SEND_SESSION = os.path.expanduser("~/bin/send-claude-session")


def on_battery():
    iokit = ctypes.CDLL("/System/Library/Frameworks/IOKit.framework/IOKit")
    iokit.IOPSGetTimeRemainingEstimate.restype = ctypes.c_double
    return iokit.IOPSGetTimeRemainingEstimate() != TIME_REMAINING_UNLIMITED


def notice(transcript_path, battery, agent=None, forget=False):
    """Records whether the agent of the session whose transcript is
    TRANSCRIPT_PATH has been told that the computer is on battery, and
    returns what to tell it now, or None. AGENT is a subagent's ID, or None
    for the main conversation. FORGET treats the agent as told nothing."""
    session_dir = os.path.splitext(transcript_path)[0]
    os.makedirs(session_dir, exist_ok=True)
    name = "battery-notice" if agent is None else "battery-notice-" + agent
    current = "battery" if battery else ""
    fd = os.open(os.path.join(session_dir, name), os.O_RDWR | os.O_CREAT, 0o600)
    with open(fd, "r+", encoding="utf-8") as told:
        fcntl.flock(told, fcntl.LOCK_EX)
        recorded = told.read()
        if recorded != current:
            told.seek(0)
            told.truncate()
            told.write(current)
    if forget:
        recorded = ""
    if recorded == current:
        return None
    return BATTERY if battery else WALL


@functools.cache
def titles():
    """stop-title-state.py, the hook beside this one that reads session
    titles, footer lines, and session records."""
    spec = importlib.util.spec_from_file_location("stop_title_state", os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "stop-title-state.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wake_blocked_sessions(claude_dir=CLAUDE_DIR, send_session=SEND_SESSION):
    """Sends the wall power notice, with the program SEND_SESSION, to each
    running session that is idle with 🪫 in its title and was told about the
    battery. Returns whether every notice was sent."""
    sent = True
    for pid, record in titles().session_records(claude_dir):
        try:
            os.kill(int(pid), 0)
        except (ValueError, OSError):
            continue
        session = record.get("sessionId")
        if not session or record.get("status") != "idle" or not titles().title_has_state(
                record.get("name"), "🪫"):
            continue
        transcripts = glob.glob(os.path.join(claude_dir, "projects", "*",
                                             session + ".jsonl"))
        if len(transcripts) != 1 or not notice(transcripts[0], False):
            continue
        if subprocess.run([send_session, "battery-notice", session, WALL]).returncode:
            # The session was not told, so it is still owed the notice.
            notice(transcripts[0], True)
            sent = False
    return sent


def main():
    if sys.argv[1:] in (["battery"], ["wall"]):
        # The power source can switch again before this runs, so IOKit,
        # not the argument, says which it is.
        sys.exit(0 if on_battery() or wake_blocked_sessions() else 1)
    if sys.argv[1:]:
        sys.exit("usage: battery-notice.py [battery | wall]")
    payload = json.load(sys.stdin)
    if payload["hook_event_name"] == "Stop":
        if (titles().footer_state(payload.get("last_assistant_message")) == "🪫"
                and not on_battery() and notice(payload["transcript_path"], False)):
            json.dump({"decision": "block", "reason": WALL}, sys.stdout,
                      ensure_ascii=False)
        return
    context = notice(payload["transcript_path"], on_battery(),
                     payload.get("agent_id"),
                     payload["hook_event_name"] == "SessionStart")
    if context:
        json.dump({"hookSpecificOutput": {
            "hookEventName": payload["hook_event_name"],
            "additionalContext": context,
        }}, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
