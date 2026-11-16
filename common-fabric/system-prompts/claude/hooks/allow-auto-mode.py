#!/usr/bin/env python3
"""PreToolUse hook that allows any session to be switched to auto mode.

Reads the hook payload of a mcp__ccd_session_mgmt__set_session_permission_mode
call on stdin, and allows the call when the mode it asks for is "auto". It
makes no decision on any other call.
"""

import json
import sys

ALLOW = {
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
        "permissionDecisionReason": "Switching a session to auto mode.",
    }
}


def decide(payload):
    """The hook's output for a payload, or None to make no decision."""
    call = payload.get("tool_input") if isinstance(payload, dict) else None
    if isinstance(call, dict) and call.get("mode") == "auto":
        return ALLOW
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return
    decision = decide(payload)
    if decision:
        json.dump(decision, sys.stdout)


if __name__ == "__main__":
    main()
