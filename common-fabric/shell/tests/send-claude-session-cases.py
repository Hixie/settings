#!/usr/bin/env python3
"""Cases for send-claude-session, which sends a message as the next prompt
of a running Claude session through the session's messaging socket.

Run it with no arguments. Each case makes a home directory with made-up
session records, transcripts and Claude app records, and a socket standing
in for the session's, runs send-claude-session there, and checks what
arrived on the socket. It reports one line per case. The exit status is 0 when every
case passed and 1 otherwise.
"""

import json
import os
import socket
import subprocess
import sys
import tempfile

SEND_SESSION = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "bin", "send-claude-session")


def compact(value):
    """VALUE as JSON without spaces, as Claude writes its records."""
    return json.dumps(value, separators=(",", ":"))


def message(mode, text="hello"):
    return [{"type": "auth", "token": "secret"},
            {"type": "user", "priority": "next", "message": {"content":
             '<cross-session-message from-name="tester" from-mode="%s">\n%s\n'
             "</cross-session-message>" % (mode, text)}}]


def send(arguments, app_mode=None, transcript_modes=(), running=True):
    """Runs send-claude-session with ARGUMENTS for a made-up session "s1" whose
    Claude app record has the permission mode APP_MODE, if any, whose
    transcript records TRANSCRIPT_MODES in turn, and whose process is
    RUNNING. Returns the exit status and the lines that arrived on the
    session's socket, each read as JSON."""
    with tempfile.TemporaryDirectory() as home:
        sessions = os.path.join(home, ".claude", "sessions")
        os.makedirs(sessions)
        process = subprocess.Popen(["cat"], stdin=subprocess.PIPE)
        if not running:
            process.stdin.close()
            process.wait()
        path = os.path.join(home, "s")
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(path)
        listener.listen()
        with open(os.path.join(sessions, "%d.json" % process.pid), "w") as f:
            json.dump({"sessionId": "s1", "messagingSocketPath": path}, f)
        with open(os.path.join(sessions, "%d.%s.key" % (process.pid, "a" * 64)),
                  "w") as f:
            json.dump({"peerToken": "secret"}, f)
        transcript = os.path.join(home, ".claude", "projects", "p", "s1.jsonl")
        os.makedirs(os.path.dirname(transcript))
        with open(transcript, "w") as f:
            for mode in transcript_modes:
                f.write(compact({"type": "user", "permissionMode": mode}) + "\n")
        if app_mode:
            records = os.path.join(home, "Library", "Application Support", "Claude",
                                   "claude-code-sessions", "account", "org")
            os.makedirs(records)
            with open(os.path.join(records, "local_x.json"), "w") as f:
                f.write(compact({"cliSessionId": "s1", "permissionMode": app_mode,
                                 "lastActivityAt": 1}) + "\n")
        environment = {key: value for key, value in os.environ.items()
                       if key != "CLAUDE_CONFIG_DIR"}
        try:
            run = subprocess.run([SEND_SESSION] + arguments, capture_output=True,
                                 env={**environment, "HOME": home})
        finally:
            if process.poll() is None:
                process.stdin.close()
                process.wait()
        listener.setblocking(False)
        try:
            connection, _ = listener.accept()
        except BlockingIOError:
            return run.returncode, []
        connection.setblocking(True)
        with connection:
            received = b"".join(iter(lambda: connection.recv(4096), b""))
        return run.returncode, [json.loads(line) for line in received.splitlines()]


def check(description, expected, actual):
    print("%s %s" % ("PASS" if expected == actual else "FAIL", description))
    if expected != actual:
        print("  expected %r, got %r" % (expected, actual))
    return expected == actual


def main():
    arguments = ["tester", "s1", "hello"]
    passed = True
    passed &= check("the app's record of bypass mode",
                    (0, message("bypass")),
                    send(arguments, "bypassPermissions", ["default"]))
    passed &= check("the app's record of another mode wins over the transcript",
                    (0, message("prompting")),
                    send(arguments, "default", ["bypassPermissions"]))
    passed &= check("the last mode in the transcript, with no app record",
                    (0, message("bypass")),
                    send(arguments, None, ["default", "bypassPermissions"]))
    passed &= check("no mode anywhere", (0, message("prompting")), send(arguments))
    passed &= check("a message with quotes and lines",
                    (0, message("prompting", 'say "hi"\nthen go')),
                    send(["tester", "s1", 'say "hi"\nthen go']))
    passed &= check("an unknown session", (1, []), send(["tester", "s2", "hello"]))
    passed &= check("a session whose process has stopped", (1, []),
                    send(arguments, running=False))
    passed &= check("too few arguments", (2, []), send(["tester", "s1"]))
    sys.exit(0 if passed else 1)


main()
