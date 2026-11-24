#!/usr/bin/env python3
"""Cases for reread-instructions.py, the hook that tells a compacted
conversation which instruction files it had read.

Run it with no arguments. Each case writes instruction files into a
temporary harness home directory named by CLAUDE_CONFIG_DIR, writes a
transcript, hands the hook a SessionStart payload, and checks which files
the added context names. It reports one line per case. The exit status is 0
when every case passed and 1 otherwise.
"""

import json
import os
import subprocess
import sys
import tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "reread-instructions.py")


def read(path):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Read", "input": {"file_path": path}}]}}


def run(home, entries, default_home=False):
    transcript = os.path.join(home, "transcript.jsonl")
    with open(transcript, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    result = subprocess.run(
        [sys.executable, HOOK], capture_output=True, text=True, check=True,
        env={key: value for key, value in os.environ.items()
             if key != "CLAUDE_CONFIG_DIR"} | (
            {"HOME": os.path.dirname(home)} if default_home
            else {"CLAUDE_CONFIG_DIR": home}),
        input=json.dumps({"hook_event_name": "SessionStart", "source": "compact",
                          "transcript_path": transcript}))
    if not result.stdout:
        return None
    output = json.loads(result.stdout)["hookSpecificOutput"]
    assert output["hookEventName"] == "SessionStart"
    return [line[2:] for line in output["additionalContext"].splitlines()
            if line.startswith("* ")]


def main():
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        home = os.path.realpath(os.path.join(tmp, "home", ".claude"))
        os.makedirs(os.path.join(home, "sub"))
        for name in ["a.md", "b.md", "CLAUDE.md", "notes.txt", "sub/c.md"]:
            with open(os.path.join(home, name), "w", encoding="utf-8") as f:
                f.write("rules\n")
        os.link(os.path.join(home, "CLAUDE.md"), os.path.join(home, "INDEX.md"))
        os.symlink(home, os.path.join(tmp, "link"))
        a, b = os.path.join(home, "a.md"), os.path.join(home, "b.md")
        cases = [
            ("files listed once each, in the order first read",
             [read(b), read(a), read(b)], [b, a], False),
            ("harness home directory defaults to ~/.claude",
             [read(a)], [a], True),
            ("path through a symbolic link resolves to the file",
             [read(os.path.join(tmp, "link", "a.md"))], [a], False),
            ("CLAUDE.md and hard links to it, other file types, subdirectories, missing files, and "
             "files elsewhere are not instruction files",
             [read(os.path.join(home, "CLAUDE.md")),
              read(os.path.join(home, "INDEX.md")),
              read(os.path.join(home, "notes.txt")),
              read(os.path.join(home, "sub", "c.md")),
              read(os.path.join(home, "missing.md")),
              read(os.path.join(tmp, "a.md"))], None, False),
            ("only the agent's Read calls count",
             [{"type": "user", "message": {"content": [
                 {"type": "tool_use", "name": "Read", "input": {"file_path": a}}]}},
              {"type": "assistant", "message": {"content": [
                  {"type": "tool_use", "name": "Bash",
                   "input": {"command": f"cat {a}"}},
                  {"type": "text", "text": a}]}},
              {"type": "summary", "summary": a}], None, False),
            ("reads from before an earlier compaction still count",
             [read(a), {"type": "system", "subtype": "compact_boundary"},
              read(b)], [a, b], False),
        ]
        for description, entries, expected, default_home in cases:
            actual = run(home, entries, default_home)
            ok = actual == expected
            failures += not ok
            print(f"{'PASS' if ok else 'FAIL'}: {description}"
                  + ("" if ok else f" (expected {expected}, got {actual})"))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
