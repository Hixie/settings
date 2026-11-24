#!/usr/bin/env python3
"""Hook that tells a compacted conversation which instruction files it had
read.

CLAUDE.md links to further instruction files in the harness home directory
and tells the agent to read each one when it becomes relevant. Compaction
replaces the conversation with a summary, which keeps at most a paraphrase
of those files. Claude Code adds CLAUDE.md back after compaction, along with
the last few files the agent read, but not the instruction files the agent
read earlier in the conversation.

Registered for SessionStart with the "compact" matcher, the hook reads the
conversation's transcript, which keeps every message from before every
compaction, and finds each instruction file the agent opened with the Read
tool. It lists those files in the order the agent first read them, and
tells the agent to read again at once each one still relevant to its work,
and the others when they become relevant. An instruction file is a Markdown file
directly in the harness home directory, other than CLAUDE.md and any hard
link to it, such as INDEX.md.

The hook names the files rather than adding their text, because Claude Code
moves any added context longer than 10,000 characters into a file and leaves
the agent only a preview.
"""

import json
import os
import sys

CLAUDE_DIR = os.path.realpath(os.environ.get(
    "CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude")))

HEADER = ("You have been compacted. Before compaction, you had read the "
          "following files, which you have now forgotten as a result of "
          "compaction:")
FOOTER = ("Immediately read, in full, any of these files that are still "
          "relevant to your work. The summary does not count as having read "
          "them; when in doubt, read the file. Read any of the others as soon "
          "as it becomes relevant again.")


def is_claude_md(path):
    claude_md = os.path.join(CLAUDE_DIR, "CLAUDE.md")
    return os.path.exists(claude_md) and os.path.samefile(path, claude_md)


def instruction_file(path):
    path = os.path.realpath(os.path.expanduser(path))
    if (os.path.dirname(path) == CLAUDE_DIR and path.endswith(".md")
            and os.path.isfile(path) and not is_claude_md(path)):
        return path
    return None


def files_read(transcript_path):
    found = {}
    with open(transcript_path, encoding="utf-8") as transcript:
        for line in transcript:
            entry = json.loads(line)
            message = entry.get("message")
            if entry.get("type") != "assistant" or not isinstance(message, dict):
                continue
            for block in message.get("content") or []:
                if (isinstance(block, dict) and block.get("type") == "tool_use"
                        and block.get("name") == "Read"):
                    path = instruction_file(block["input"].get("file_path", ""))
                    if path:
                        found.setdefault(path, None)
    return list(found)


def main():
    payload = json.load(sys.stdin)
    paths = files_read(payload["transcript_path"])
    if not paths:
        return
    json.dump({"hookSpecificOutput": {
        "hookEventName": payload["hook_event_name"],
        "additionalContext": "\n".join(
            [HEADER, ""] + [f"* {p}" for p in paths] + ["", FOOTER]),
    }}, sys.stdout)


if __name__ == "__main__":
    main()
