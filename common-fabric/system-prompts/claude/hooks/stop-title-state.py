#!/usr/bin/env python3
"""Stop hook that keeps the session title's state emoji in step with the
footer line.

Reads the hook payload on stdin. The last line of the last assistant
message is the footer line, and its state emoji is everything on that line
before the first space. The session title takes the form "WORKTREES: STATE
SUMMARY", or "STATE SUMMARY" when no worktree is in play. When the two
state emoji differ, the hook blocks the stop and tells the agent to update
its title.

Only sessions run by the Claude desktop app are checked, since the title
tool exists only there. Hooks cannot set the title of a session when it
stops: the harness takes a title from UserPromptSubmit and SessionStart
hooks only.
"""

import glob
import json
import os
import re
import sys

CLAUDE_DIR = os.environ.get("CLAUDE_CONFIG_DIR",
                            os.path.expanduser("~/.claude"))

# The list of worktrees that opens a title, with its colon. Worktree
# identifiers are letters, digits, and hyphens, where letters include
# non-ASCII ones such as "ω" and "𝛌", so a list never contains an emoji.
TITLE_WORKTREES = re.compile(r"(?:[\w\s,#-]*:\s*)?")

# The variation selector that asks for an emoji to be drawn in color. Some
# emoji are written both with it and without it.
VARIATION_SELECTOR = "\ufe0f"

# The zero-width joiner that joins emoji such as "👩", "❤️", and "👩" into
# one. The session records under ~/.claude store it as a space.
JOINER = "\u200d"

REMINDER = "Update your session title. Do not tell the user you are doing this."


def normalized(text):
    return text.replace(VARIATION_SELECTOR, "").replace(JOINER, " ")


def footer_state(message):
    """The state emoji of the footer line of a message, or None when the
    message has no text."""
    lines = [line.strip() for line in (message or "").splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return None
    return lines[-1].split(" ", 1)[0]


def title_has_state(title, state):
    """Whether a title's state emoji is the given one.

    Joiners read as spaces on both sides, so a joined emoji is compared as
    the words it is made of.
    """
    title = title or ""
    rest = normalized(title[TITLE_WORKTREES.match(title).end():])
    return (rest + " ").startswith(normalized(state) + " ")


def session_record(session_id):
    """The newest record the harness keeps for a session, or None."""
    records = []
    for path in glob.glob(os.path.join(CLAUDE_DIR, "sessions", "*.json")):
        try:
            with open(path, encoding="utf-8") as handle:
                record = json.load(handle)
        except (OSError, ValueError):
            continue
        if isinstance(record, dict) and record.get("sessionId") == session_id:
            records.append(record)
    return max(records, key=lambda record: record.get("updatedAt") or 0,
               default=None)


def main():
    payload = json.load(sys.stdin)
    footer = footer_state(payload.get("last_assistant_message"))
    if footer is None:
        return
    record = session_record(payload.get("session_id"))
    if not record or record.get("entrypoint") != "claude-desktop":
        return
    if not title_has_state(record.get("name"), footer):
        json.dump({"decision": "block", "reason": REMINDER}, sys.stdout)


if __name__ == "__main__":
    main()
