#!/usr/bin/env python3
"""Cases for allow-auto-mode.py, the PreToolUse hook that allows any session
to be switched to auto mode.

Run it with no arguments. It runs the hook on each payload below and reads
the decision it writes on standard output. It reports one line per case. The
exit status is 0 when every case decided the way it should and 1 otherwise.
"""

import json
import os
import subprocess
import sys

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "allow-auto-mode.py")


def call(session_id, mode):
    return json.dumps({
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__ccd_session_mgmt__set_session_permission_mode",
        "tool_input": {"session_id": session_id, "mode": mode},
        "permission_mode": "auto",
    })


OTHER = "local_00e966a2-72e9-4105-8b8c-1bfec2b1ae0b"

# (description, standard input, whether the hook is to allow the call)
CASES = [
    ("another session to auto", call(OTHER, "auto"), True),
    ("itself to auto", call("self", "auto"), True),
    ("another session to bypass", call(OTHER, "bypassPermissions"), False),
    ("another session to plan", call(OTHER, "plan"), False),
    ("another session to default", call(OTHER, "default"), False),
    ("another session to acceptEdits", call(OTHER, "acceptEdits"), False),
    ("mode spelled differently", call(OTHER, "Auto"), False),
    ("mode that is not a string", call(OTHER, ["auto"]), False),
    ("no mode", json.dumps({"tool_input": {"session_id": OTHER}}), False),
    ("input that is not an object", json.dumps({"tool_input": "auto"}),
     False),
    ("payload that is not an object", "[]", False),
    ("payload that is not JSON", "not json", False),
]


def main():
    failures = 0
    for description, text, allow in CASES:
        finished = subprocess.run([sys.executable, HOOK], input=text,
                                  capture_output=True, text=True)
        out = finished.stdout.strip()
        decision = (json.loads(out) if out else {}).get(
            "hookSpecificOutput", {}).get("permissionDecision")
        passed = finished.returncode == 0 and (decision == "allow") == allow \
            and (decision is None) == (not allow)
        failures += not passed
        print("%s  %s: %s" % ("ok  " if passed else "FAIL", description,
                              decision or "no decision"))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
