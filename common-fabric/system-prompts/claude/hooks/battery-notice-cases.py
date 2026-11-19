#!/usr/bin/env python3
"""Cases for battery-notice.py, the hook that tells each agent in a session
when the computer runs on battery power and when it is back on wall power.

Run it with no arguments. Most cases load the hook as a module and give its
notice function a transcript and a power source for each step, checking
what it says to tell the agent. The rest run the hook as a program: as
Claude Code does, on the power source that "pmset -g ps" reports, and as
github-hookbar does when the power source changes, with made-up session
records and a stand-in for send-claude-session that records what it is
asked to send. It reports one line per case. The exit status is 0 when
every case passed and 1 otherwise.
"""

import importlib.util
import json
import multiprocessing
import os
import subprocess
import sys
import tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "battery-notice.py")
spec = importlib.util.spec_from_file_location("battery_notice", HOOK)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

BATTERY, WALL = hook.BATTERY, hook.WALL

PROMPT, TOOL, START = "UserPromptSubmit", "PostToolUse", "SessionStart"

# (description, session, subagent or None for the main conversation, hook
# event, whether the computer is on battery, what to tell the agent or None)
STEPS = [
    ("cleared on wall power", "one", None, START, False, None),
    ("first prompt on wall power", "one", None, PROMPT, False, None),
    ("tool call on wall power", "one", None, TOOL, False, None),
    ("unplugged", "one", None, TOOL, True, BATTERY),
    ("still on battery", "one", None, TOOL, True, None),
    ("subagent on battery", "one", "a", TOOL, True, BATTERY),
    ("same subagent still on battery", "one", "a", TOOL, True, None),
    ("main conversation after the subagent", "one", None, PROMPT, True, None),
    ("compacted on battery", "one", None, START, True, BATTERY),
    ("tool call after compacting on battery", "one", None, TOOL, True, None),
    ("new session cleared on battery", "two", None, START, True, BATTERY),
    ("first prompt of that session", "two", None, PROMPT, True, None),
    ("first prompt of a new session", "three", None, PROMPT,
     True, BATTERY),
    ("plugged in", "one", None, TOOL, False, WALL),
    ("still on wall power", "one", None, PROMPT, False, None),
    ("subagent told about the battery, on wall power", "one", "a", TOOL, False,
     WALL),
    ("subagent never told about the battery, on wall power", "one", "b", TOOL,
     False, None),
    ("unplugged again", "one", None, TOOL, True, BATTERY),
    ("compacted after being plugged in", "two", None, START, False, None),
    ("tool call after compacting on wall power", "two", None, TOOL, False, None),
    ("unplugged after compacting", "two", None, TOOL, True, BATTERY),
]


def transcript(directory, session):
    return os.path.join(directory, session + ".jsonl")


def step_notice(directory, session, subagent, event, battery):
    return hook.notice(transcript(directory, session), battery, subagent,
                       event == START)


def battery_notice(directory):
    return hook.notice(transcript(directory, "parallel"), True)


def parallel_notices(count):
    """Asks for the notice from COUNT processes at once, as for parallel tool
    calls in a new session on battery, and returns how many of them said to
    tell the agent."""
    with tempfile.TemporaryDirectory() as directory:
        with multiprocessing.get_context("spawn").Pool(count) as pool:
            results = pool.map(battery_notice, [directory] * count, 1)
    return sum(1 for result in results if result)


def record_path(transcript_path):
    return os.path.join(os.path.splitext(transcript_path)[0], "battery-notice")


def record(transcript_path, told):
    """Records that the main conversation of the session whose transcript is
    TRANSCRIPT_PATH was told TOLD ("battery", "", or None for nothing
    recorded)."""
    if told is not None:
        os.makedirs(os.path.dirname(record_path(transcript_path)), exist_ok=True)
        with open(record_path(transcript_path), "w", encoding="utf-8") as f:
            f.write(told)


def recorded(transcript_path):
    """What is recorded for the main conversation of the session whose
    transcript is TRANSCRIPT_PATH, or None when nothing is."""
    if not os.path.exists(record_path(transcript_path)):
        return None
    with open(record_path(transcript_path), encoding="utf-8") as f:
        return f.read()


def run_program(data, told=None):
    """Runs the hook as Claude Code does with the payload DATA, after
    recording that the agent was told TOLD, and returns the exit status,
    standard output and standard error, and what is recorded afterwards."""
    record(data["transcript_path"], told)
    run = subprocess.run([sys.executable, HOOK], input=json.dumps(data),
                         capture_output=True, text=True)
    return run.returncode, run.stdout, run.stderr, recorded(data["transcript_path"])


def context_output(event, context):
    return json.dumps({"hookSpecificOutput": {
        "hookEventName": event, "additionalContext": context,
    }}, ensure_ascii=False)


def check(description, expected, actual):
    print("%s %s" % ("PASS" if expected == actual else "FAIL", description))
    if expected != actual:
        print("  expected %r, got %r" % (expected, actual))
    return expected == actual


def program_cases(battery):
    """Checks the hook run as Claude Code runs it, on the current power
    source, BATTERY."""
    passed = True
    now = "battery" if battery else ""
    with tempfile.TemporaryDirectory() as directory:
        data = {"session_id": "change", "hook_event_name": PROMPT,
                "transcript_path": transcript(directory, "change")}
        passed &= check(
            "program at a prompt after the power source changed",
            (0, context_output(PROMPT, BATTERY if battery else WALL), "", now),
            run_program(data, "" if battery else "battery"))
        data = {"session_id": "same", "hook_event_name": PROMPT,
                "transcript_path": transcript(directory, "same")}
        passed &= check("program at a prompt with no change", (0, "", "", now),
                        run_program(data, now))
    return passed


# (session, whether its process runs, status, title, what it was told,
# whether it is to be sent the wall power notice on wall power, what it is
# told afterwards on wall power)
SESSIONS = [
    ("blocked", True, "idle", "X1, 𝛌X1: 🪫 Wait for power", "battery", True, ""),
    ("blocked-alone", True, "idle", "🪫 Wait for power", "battery", True, ""),
    ("never-told", True, "idle", "X2: 🪫 Wait for power", "", False, ""),
    ("busy", True, "busy", "X3: 🪫 Wait for power", "battery", False, "battery"),
    ("other-state", True, "idle", "X4: 🐤 Look at this", "battery", False,
     "battery"),
    ("in-summary", True, "idle", "X5: 🐤 Explain 🪫", "battery", False, "battery"),
    ("stopped", False, "idle", "X6: 🪫 Wait for power", "battery", False,
     "battery"),
]


def sessions_home(home, send_status=0):
    """Makes, in the home directory HOME, the sessions in SESSIONS, two
    records that cannot be read, and a stand-in for send-claude-session that
    exits with SEND_STATUS and records what it is asked to send. Returns the
    processes standing in for the sessions' processes, which the caller
    ends, and the sessions' transcripts."""
    claude = os.path.join(home, ".claude")
    os.makedirs(os.path.join(claude, "sessions"))
    os.makedirs(os.path.join(home, "bin"))
    with open(os.path.join(home, "bin", "send-claude-session"), "w") as f:
        f.write('#!/bin/sh\nprintf "%%s|%%s|%%s\\n" "$1" "$2" "$3" >> %s\n'
                "exit %d\n" % (os.path.join(home, "sent"), send_status))
    os.chmod(os.path.join(home, "bin", "send-claude-session"), 0o755)
    processes = []
    transcripts = []
    contents = [{"sessionId": session, "status": status, "name": title}
                for session, _, status, title, _, _, _ in SESSIONS]
    for content in contents + ["{", {"status": "idle", "name": "🪫 No ID"}]:
        process = subprocess.Popen(["cat"], stdin=subprocess.PIPE)
        processes.append(process)
        with open(os.path.join(claude, "sessions", "%d.json" % process.pid),
                  "w", encoding="utf-8") as f:
            f.write(content if isinstance(content, str) else json.dumps(content))
    for (session, running, _, _, told, _, _), process in zip(SESSIONS, processes):
        if not running:
            process.stdin.close()
            process.wait()
        transcripts.append(os.path.join(claude, "projects", "p", session + ".jsonl"))
        os.makedirs(os.path.dirname(transcripts[-1]), exist_ok=True)
        open(transcripts[-1], "w").close()
        record(transcripts[-1], told)
    return processes, transcripts


def end(processes):
    for process in processes:
        if process.poll() is None:
            process.stdin.close()
            process.wait()


def sent(home):
    """What the stand-in for send-claude-session was asked to send, one line
    for each, in order."""
    if not os.path.exists(os.path.join(home, "sent")):
        return []
    with open(os.path.join(home, "sent"), encoding="utf-8") as f:
        return sorted(f.read().splitlines())


def wake(send_status=0):
    """Runs wake_blocked_sessions among the sessions in SESSIONS. Returns
    whether it says every notice was sent, what it sent, and what each
    session is told afterwards."""
    with tempfile.TemporaryDirectory() as home:
        processes, transcripts = sessions_home(home, send_status)
        try:
            result = hook.wake_blocked_sessions(
                os.path.join(home, ".claude"),
                os.path.join(home, "bin", "send-claude-session"))
        finally:
            end(processes)
        return result, sent(home), [recorded(path) for path in transcripts]


def run_hookbar(argument):
    """Runs the hook as github-hookbar does, with ARGUMENT, among the
    sessions in SESSIONS. Returns the exit status, what it sent, and what
    each session is told afterwards."""
    with tempfile.TemporaryDirectory() as home:
        processes, transcripts = sessions_home(home)
        try:
            run = subprocess.run(
                [sys.executable, HOOK, argument], capture_output=True,
                env={**os.environ, "HOME": home,
                     "CLAUDE_CONFIG_DIR": os.path.join(home, ".claude")})
        finally:
            end(processes)
        return run.returncode, sent(home), [recorded(path) for path in transcripts]


def hookbar_cases(battery):
    """Checks waking blocked sessions, and the hook run as github-hookbar
    runs it on the current power source, BATTERY."""
    passed = True
    woken = sorted("battery-notice|%s|%s" % (entry[0], WALL)
                   for entry in SESSIONS if entry[5])
    told_before = [entry[4] for entry in SESSIONS]
    told_after = [entry[6] for entry in SESSIONS]
    passed &= check("waking wakes only idle running sessions blocked and told",
                    (True, woken, told_after), wake())
    passed &= check("a session that send-claude-session cannot reach is still "
                    "owed the notice", (False, woken, told_before), wake(1))
    for argument in ["wall", "battery"]:
        passed &= check(
            "%s on %s power" % (argument, "battery" if battery else "wall"),
            (0, [], told_before) if battery else (0, woken, told_after),
            run_hookbar(argument))
    run = subprocess.run([sys.executable, HOOK, "sideways"], capture_output=True)
    passed &= check("another argument is refused", 1, run.returncode)
    return passed


def stop_cases(battery):
    """Checks the hook run as Claude Code runs it at Stop, on the current
    power source, BATTERY."""
    passed = True
    block = json.dumps({"decision": "block", "reason": WALL}, ensure_ascii=False)
    with tempfile.TemporaryDirectory() as directory:
        for description, footer, told, wall_result in [
                ("blocked and told", "Blocked.\n\n🪫 0xE8", "battery", (0, block, "", "")),
                ("blocked and never told", "Blocked.\n🪫 0xE8", "", (0, "", "", "")),
                ("in another state and told", "Done.\n🐤 0xE8", "battery",
                 (0, "", "", "battery")),
                ("with 🪫 above the last line", "Was 🪫.\n🐤 0xE8", "battery",
                 (0, "", "", "battery")),
        ]:
            data = {"session_id": description, "hook_event_name": "Stop",
                    "transcript_path": transcript(directory, description),
                    "last_assistant_message": footer}
            passed &= check(
                "program at a stop %s, on %s power"
                % (description, "battery" if battery else "wall"),
                (0, "", "", told) if battery else wall_result,
                run_program(data, told))
    return passed


def main():
    passed = True
    with tempfile.TemporaryDirectory() as directory:
        for description, session, subagent, event, battery, expected in STEPS:
            actual = step_notice(directory, session, subagent, event, battery)
            passed &= check(description, expected, actual)
    passed &= check("parallel tool calls report a change once", 1,
                    parallel_notices(16))
    pmset = subprocess.run(["pmset", "-g", "ps"], capture_output=True,
                           text=True, check=True).stdout
    battery = "'Battery Power'" in pmset
    passed &= check("IOKit reports the power source pmset reports", battery,
                    hook.on_battery())
    passed &= program_cases(battery)
    passed &= hookbar_cases(battery)
    passed &= stop_cases(battery)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
