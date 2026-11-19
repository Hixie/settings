#!/usr/bin/env python3
"""Hook that tells the session when the dashboard announcement changes.

Reads the current announcement from ~/.cache/dashboard-message.txt while
holding a shared flock(2) lock on it, so it never sees the file half
written, and compares it, with surrounding whitespace removed, to the
announcement this session last saw. A missing file counts as a blank
announcement, and so does a session that has seen nothing yet. The
last-seen value is kept in a file in the session's own directory next to
its transcript, so it is deleted along with the session. The hook holds a
lock on that file while it compares and records, so hooks for parallel
tool calls report each change once.

At UserPromptSubmit and PostToolUse, when the announcement differs from
the last-seen one, the hook adds "New dashboard announcement: MESSAGE" to
the session's context, or "(The dashboard announcement has been
cleared.)" when it is now blank, and records the new value. At
SessionStart, it is registered only for the moment after a conversation
is compacted or cleared, when the session's context no longer holds
earlier announcements, so the hook treats the session as having seen
nothing: it tells the session the current announcement again, and tells
it nothing when there is none. Tool calls made by subagents are skipped,
so the announcement reaches the main conversation.
"""

import fcntl
import json
import os
import sys

MESSAGE = os.path.expanduser("~/.cache/dashboard-message.txt")


def main():
    payload = json.load(sys.stdin)
    if "agent_id" in payload:
        return
    try:
        with open(MESSAGE, encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            current = f.read().strip()
    except FileNotFoundError:
        current = ""
    session_dir = os.path.splitext(payload["transcript_path"])[0]
    os.makedirs(session_dir, exist_ok=True)
    fd = os.open(os.path.join(session_dir, "dashboard-announcement"),
                 os.O_RDWR | os.O_CREAT, 0o600)
    with open(fd, "r+", encoding="utf-8") as seen:
        fcntl.flock(seen, fcntl.LOCK_EX)
        last = seen.read()
        if last != current:
            seen.seek(0)
            seen.truncate()
            seen.write(current)
    if payload["hook_event_name"] == "SessionStart":
        last = ""
    if last == current:
        return
    if current:
        context = "New dashboard announcement: " + current
    else:
        context = "(The dashboard announcement has been cleared.)"
    json.dump({"hookSpecificOutput": {
        "hookEventName": payload["hook_event_name"],
        "additionalContext": context,
    }}, sys.stdout, ensure_ascii=False)


main()
