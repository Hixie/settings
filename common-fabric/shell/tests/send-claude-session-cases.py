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


def app_record(mode, last_activity=1, session="s1"):
    """A Claude app record of SESSION in permission mode MODE, written as the
    app writes it: one line of JSON with no newline at its end."""
    return compact({"cliSessionId": session, "permissionMode": mode,
                    "lastActivityAt": last_activity})


def send(arguments, app_mode=None, transcript_modes=(), running=True,
         host="local_1", app_records=(), has_socket=True, neighbour=None,
         with_error=False):
    """Runs send-claude-session with ARGUMENTS for a made-up session "s1" whose
    record names its socket if HAS_SOCKET and the Claude app's ID for it,
    HOST, if any, whose app record has the permission mode APP_MODE, if any,
    whose transcript records TRANSCRIPT_MODES in turn, and whose process is
    RUNNING. APP_RECORDS adds further app records, each a folder under the
    app's folder of records, a file name, and the file's text, or None for a
    file that cannot be read. With NEIGHBOUR, another running process has a
    record that comes first in the list of records and mentions "s1": one
    that cannot be read if NEIGHBOUR is "unreadable", or that of a session
    that "s1" was once part of if NEIGHBOUR is "former".
    Returns the exit status and the lines that arrived on the session's
    socket, each read as JSON, and, WITH_ERROR, what it printed to standard
    error."""
    with tempfile.TemporaryDirectory() as home:
        sessions = os.path.join(home, ".claude", "sessions")
        os.makedirs(sessions)
        processes = sorted((subprocess.Popen(["cat"], stdin=subprocess.PIPE)
                            for _ in range(2 if neighbour else 1)),
                           key=lambda process: str(process.pid))
        process = processes[-1]
        if neighbour:
            record = os.path.join(sessions, "%d.json" % processes[0].pid)
            with open(record, "w") as f:
                json.dump({"sessionId": "s1"} if neighbour == "unreadable" else
                          {"sessionId": "s10", "hostSessionId": "local_1",
                           "messagingSocketPath": os.path.join(home, "other"),
                           "formerNames": [{"sessionId": "s1"}]}, f)
            if neighbour == "unreadable":
                os.chmod(record, 0)
        if not running:
            process.stdin.close()
            process.wait()
        path = os.path.join(home, "s")
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(path)
        listener.listen()
        with open(os.path.join(sessions, "%d.json" % process.pid), "w") as f:
            json.dump({"sessionId": "s1",
                       **({"messagingSocketPath": path} if has_socket else {}),
                       **({"hostSessionId": host} if host else {})}, f)
        with open(os.path.join(sessions, "%d.%s.key" % (process.pid, "a" * 64)),
                  "w") as f:
            json.dump({"peerToken": "secret"}, f)
        transcript = os.path.join(home, ".claude", "projects", "p", "s1.jsonl")
        os.makedirs(os.path.dirname(transcript))
        with open(transcript, "w") as f:
            for mode in transcript_modes:
                f.write(compact({"type": "user", "permissionMode": mode}) + "\n")
        if app_mode:
            app_records = [("account/org", "local_1.json", app_record(app_mode))
                           ] + list(app_records)
        for folder, name, text in app_records:
            records = os.path.join(home, "Library", "Application Support", "Claude",
                                   "claude-code-sessions", folder)
            os.makedirs(records, exist_ok=True)
            with open(os.path.join(records, name), "w") as f:
                f.write(text or "")
            if text is None:
                os.chmod(os.path.join(records, name), 0)
        environment = {key: value for key, value in os.environ.items()
                       if key != "CLAUDE_CONFIG_DIR"}
        try:
            run = subprocess.run([SEND_SESSION] + arguments, capture_output=True,
                                 env={**environment, "HOME": home})
        finally:
            for each in processes:
                if each.poll() is None:
                    each.stdin.close()
                    each.wait()
        listener.setblocking(False)
        try:
            connection, _ = listener.accept()
        except BlockingIOError:
            received = b""
        else:
            connection.setblocking(True)
            with connection:
                received = b"".join(iter(lambda: connection.recv(4096), b""))
        result = (run.returncode, [json.loads(line) for line in received.splitlines()])
        return result + (run.stderr.decode(),) if with_error else result


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
    passed &= check("the app's record of a session the app did not start is unused",
                    (0, message("prompting")),
                    send(arguments, "bypassPermissions", ["default"], host=None))
    passed &= check("an app record that the session's record does not name is unused",
                    (0, message("prompting")),
                    send(arguments, None, ["default"], app_records=[
                        ("account/org", "local_2.json", app_record("bypassPermissions"))]))
    passed &= check("an app record named for the session but of another session is unused",
                    (0, message("prompting")),
                    send(arguments, None, ["default"], app_records=[
                        ("account/org", "local_1.json",
                         app_record("bypassPermissions", session="s2"))]))
    passed &= check("the newer of two copies of the app's record, in bypass mode",
                    (0, message("bypass")),
                    send(arguments, None, [], app_records=[
                        ("a1/o1", "local_1.json", app_record("default", 1)),
                        ("a2/o2", "local_1.json", app_record("bypassPermissions", 2))]))
    passed &= check("the newer of two copies of the app's record, in another mode",
                    (0, message("prompting")),
                    send(arguments, None, [], app_records=[
                        ("a1/o1", "local_1.json", app_record("default", 2)),
                        ("a2/o2", "local_1.json", app_record("bypassPermissions", 1))]))
    passed &= check("a damaged copy of the app's record spoils only itself",
                    (0, message("bypass")),
                    send(arguments, None, ["default"], app_records=[
                        ("a1/o1", "local_1.json", app_record("default", 2)[:-5]),
                        ("a2/o2", "local_1.json", app_record("bypassPermissions", 1))]))
    passed &= check("an unreadable copy of the app's record spoils only itself",
                    (0, message("bypass")),
                    send(arguments, None, ["default"], app_records=[
                        ("a1/o1", "local_1.json", None),
                        ("a2/o2", "local_1.json", app_record("bypassPermissions"))]))
    passed &= check("a copy of the app's record that the app set aside is unused",
                    (0, message("prompting")),
                    send(arguments, None, ["default"], app_records=[
                        ("a1.old/o1", "local_1.json", app_record("bypassPermissions"))]))
    passed &= check("a message with quotes and lines",
                    (0, message("prompting", 'say "hi"\nthen go')),
                    send(["tester", "s1", 'say "hi"\nthen go']))
    passed &= check("an unknown session", (1, []), send(["tester", "s2", "hello"]))
    passed &= check("a session whose record names no socket",
                    (1, [], "send-claude-session: no running Claude session s1 "
                     "can receive messages\n"),
                    send(arguments, "bypassPermissions", has_socket=False,
                         with_error=True))
    passed &= check("an unreadable record of another session is skipped",
                    (0, message("bypass")),
                    send(arguments, "bypassPermissions", neighbour="unreadable"))
    passed &= check("another session's record that mentions the session is skipped",
                    (0, message("bypass")),
                    send(arguments, "bypassPermissions", neighbour="former"))
    passed &= check("a session whose process has stopped", (1, []),
                    send(arguments, running=False))
    passed &= check("too few arguments", (2, []), send(["tester", "s1"]))
    sys.exit(0 if passed else 1)


main()
