#!/usr/bin/env python3
"""Cases for agent-sessions, which answers questions about the Claude and
Codex sessions on this machine from the files those programs keep on disk.

Run it with no arguments. It builds a made-up home directory with sessions,
transcripts, worktrees and a Codex database, runs agent-sessions against it,
and reports one line per case. The exit status is 0 when every case passed
and 1 otherwise.

The home directory holds the spawn gate from this repository, so these cases
also check that agent-sessions and the gate agree. Sessions that the gate
counts as running have real processes: cat, run through a link whose name
contains "claude", reading from a pipe that closes when the cases end, so
they end with the cases however the cases end.
"""

import argparse
import atexit
import contextlib
import datetime
import importlib.machinery
import importlib.util
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

TESTS = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(TESTS), "bin", "agent-sessions")
REAL_GATE = os.path.join(os.path.dirname(os.path.dirname(TESTS)), "system-prompts", "claude",
                         "hooks", "spawn-task-gate.py")
HOME = tempfile.mkdtemp(prefix="agent-sessions-test-")
ACCOUNT, ORG = "a23bb978-92b8-47e3-9506-13ebf22aa322", "1fa7757f-90cc-4983-affb-240281cd95d2"
OTHER_ACCOUNT = "b23bb978-92b8-47e3-9506-13ebf22aa322"
SUPPORT = os.path.join(HOME, "Library", "Application Support", "Claude", "claude-code-sessions")
LABS = os.path.join(HOME, "dev", "commonfabric", "labs")
NOW = datetime.datetime.now(datetime.timezone.utc)
NOW_MS = int(NOW.timestamp() * 1000)
HOUR_MS = 3600 * 1000
PROCESSES = []


@atexit.register
def clean_up():
    """End the fixture processes and remove the made-up home directory,
    however the cases end."""
    for child in PROCESSES:
        child.stdin.close()
        child.wait()
    shutil.rmtree(HOME)


def write(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False)


def uuid(n):
    return "%08x-0000-4000-8000-%012x" % (n, n)


def stamp(minutes_ago):
    moment = NOW - datetime.timedelta(minutes=minutes_ago)
    return moment.isoformat().replace("+00:00", "Z")


def user(content, minutes_ago=5, **extra):
    return {"type": "user", "timestamp": stamp(minutes_ago),
            "message": {"role": "user", "content": content}, **extra}


def assistant(text, stop="end_turn", minutes_ago=4, **extra):
    return {"type": "assistant", "timestamp": stamp(minutes_ago),
            "message": {"role": "assistant", "stop_reason": stop,
                        "content": [{"type": "text", "text": text}]}, **extra}


def queue(operation, minutes_ago=3, content=None):
    return {"type": "queue-operation", "operation": operation, "timestamp": stamp(minutes_ago),
            "content": content}


def subagent(agent, minutes_ago):
    return launched(agent, minutes_ago, "agentId")


def absorbed(message, minutes_ago):
    """A message delivered in the middle of a turn."""
    return {"type": "attachment", "timestamp": stamp(minutes_ago), "attachment": {
        "type": "queued_command", "prompt": message["message"]["content"]}}


def launched(task, minutes_ago, field="backgroundTaskId"):
    """A tool result saying a background task, subagent or monitor started."""
    return user([{"type": "tool_result", "tool_use_id": "t", "content": "started %s" % task}],
                minutes_ago, toolUseResult={field: task, **(
                    {"status": "async_launched"} if field == "agentId" else {})})


def notice(task, minutes_ago=2, status="completed"):
    return user("<task-notification>\n<task-id>%s</task-id>\n<status>%s</status>\n"
                "</task-notification>" % (task, status), minutes_ago)


def message_of(record):
    return record["message"]["content"]


def hand_back(agent, minutes_ago=2):
    return user('Another Claude session sent a message:\n<agent-message from="%s">\nreport\n'
                "</agent-message>" % agent, minutes_ago, isMeta=True)


def monitor_event(task, minutes_ago=2):
    return user("<task-notification>\n<task-id>%s</task-id>\n<summary>Monitor event: "
                "line</summary>\n</task-notification>" % task, minutes_ago)


FINISHED = [user("do it"), assistant("done")]
KILLED_NOTICE = ("<task-notification>\n<task-id>bw1</task-id>\n<status>killed</status>\n"
                 "</task-notification>")


def transcript(cli, records):
    path = os.path.join(HOME, ".claude", "projects", "-x", cli + ".jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.writelines(json.dumps(record) + "\n" for record in records)
    return path


def desktop(n, title, folder=ORG, account=ACCOUNT, records=None, **fields):
    sid = "local_" + uuid(n)
    write(os.path.join(SUPPORT, account, folder, sid + ".json"), {
        "sessionId": sid, "cliSessionId": uuid(1000 + n), "title": title,
        "cwd": os.path.join(HOME, "dev", "commonfabric"), "isArchived": False,
        "permissionMode": "auto", "model": "claude-opus-5-5",
        "createdAt": NOW_MS - 48 * HOUR_MS, "lastActivityAt": NOW_MS - HOUR_MS, **fields})
    if records is not None:
        transcript(uuid(1000 + n), records)
    return sid


def process(n, sid, title, cwd, status="idle"):
    """A running process for a session, and Claude Code's file for it."""
    child = subprocess.Popen([os.path.join(HOME, "bin", "claude-fixture")],
                             stdin=subprocess.PIPE, stdout=subprocess.DEVNULL)
    PROCESSES.append(child)
    write(os.path.join(HOME, ".claude", "sessions", "%d.json" % child.pid), {
        "pid": child.pid, "sessionId": uuid(1000 + n), "hostSessionId": sid,
        "cwd": cwd, "name": title, "status": status, "startedAt": NOW_MS - 30 * 60 * 1000,
        "updatedAt": NOW_MS - 20 * 60 * 1000})


def running(n, title, cwd=None, status="idle", records=FINISHED, **fields):
    """A desktop session with a running process, by default with a
    finished turn."""
    cwd = cwd or os.path.join(HOME, "dev", "commonfabric")
    sid = desktop(n, title, cwd=cwd, records=records, **fields)
    process(n, sid, title, cwd, status)
    return sid


def rollout(tid, ending, hours_ago, said=None, replied=None):
    """A Codex thread's transcript, whose last turn ends with `ending`
    `hours_ago`, and in which the user said `said` and the agent replied
    `replied`, if given."""
    path = os.path.join(HOME, ".codex", "sessions", tid + ".jsonl")
    events = [{"type": "task_started"}, {"type": "item_completed", "item": {
        "type": "UserMessage", "content": [{"type": "text", "text": said or "go"}]}},
        {"type": "item_completed", "item": {"type": "AgentMessage", "content": [
            {"type": "Text", "text": replied or "done"}]}}, {"type": ending}]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.writelines(json.dumps({"timestamp": stamp(hours_ago * 60 + 3 - index),
                                      "type": "event_msg", "payload": event}) + "\n"
                          for index, event in enumerate(events))
    return path


def git(*arguments):
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
                    "-c", "commit.gpgsign=false", *arguments], check=True, capture_output=True)


def repository(parent, remote, worktrees):
    """A repository in parent/root whose `remote` main branch, if any, is its
    first commit, with a worktree on that commit for each code given."""
    root = os.path.join(parent, "root")
    git("init", "-q", "-b", "main", root)
    git("-C", root, "commit", "-q", "--allow-empty", "-m", "first")
    if remote:
        git("-C", root, "update-ref", "refs/remotes/%s/main" % remote, "HEAD")
    for code in worktrees:
        git("-C", root, "worktree", "add", "-q", "-b", code.lower(), os.path.join(parent, code))


def build():
    """Worktrees: labs EF, 1A, 2B and EQ on upstream's main, EA and EH one
    commit past it, EK with uncommitted changes, and VA to VH and EZ, which
    are not repositories;
    cfs EM on origin's main and EJ; infra EP on a repository with no remote,
    and E0; contraptions. Not on disk: cfs FG and EG."""
    commonfabric = os.path.join(HOME, "dev", "commonfabric")
    repository(LABS, "upstream", ["EF", "1A", "2B", "EA", "EH", "EK", "EQ"])
    for code in ("EA", "EH"):
        git("-C", os.path.join(LABS, code), "commit", "-q", "--allow-empty", "-m", "unlanded")
    # An origin whose main branch has EH's commit, which upstream's does not.
    git("-C", os.path.join(LABS, "root"), "update-ref", "refs/remotes/origin/main", "eh")
    write(os.path.join(LABS, "EK", "scratch.txt"), "uncommitted")
    repository(os.path.join(commonfabric, "cfs"), "origin", ["EM"])
    repository(os.path.join(commonfabric, "infra"), None, ["EP"])
    for path in ("labs/VA", "labs/VB", "labs/V5", "labs/VC", "labs/VD", "labs/VE/src",
                 "labs/VF", "labs/VG", "labs/VH", "labs/EZ",
                 "cfs/EJ", "infra/E0", "../contraptions"):
        os.makedirs(os.path.join(commonfabric, path))
    hooks = os.path.join(HOME, ".claude", "hooks")
    os.makedirs(hooks)
    os.symlink(REAL_GATE, os.path.join(hooks, "spawn-task-gate.py"))
    os.makedirs(os.path.join(HOME, "bin"))
    os.symlink("/bin/cat", os.path.join(HOME, "bin", "claude-fixture"))
    os.symlink("/bin/cat", os.path.join(HOME, "bin", "codex"))
    PROCESSES.append(subprocess.Popen([os.path.join(HOME, "bin", "codex")],
                                      stdin=subprocess.PIPE, stdout=subprocess.DEVNULL))

    idle = NOW_MS - 13 * HOUR_MS
    ids = {
        "vb": running(1, "VB: 🟠 #10235 Highlight Jinja templates"),
        "va": running(2, "VA: 📚 (VB) Terraform templates in cf view",
                      spawnedFrom={"sessionId": "local_parent", "taskId": "task_1"}),
        "stacked-dangling": running(3, "ℂEJ: 📚 (ℂFG, ℂEG) Split the scheduler"),
        "infra-1": running(4, "INFRAE0: 🧱 Move the runners"),
        "infra-2": running(5, "INFRAE0, V5: 🐤 Rotate keys"),
        "dormant": desktop(6, "VA, V5: ⏸️ Paused work", permissionMode="bypassPermissions",
                           lastActivityAt=idle, records=FINISHED),
        "unguarded": desktop(7, "contraptions: ✅ Finished tool", lastActivityAt=idle,
                             postTurnSummary={"status_detail": "merged the gizmo"},
                             records=FINISHED),
        "archived": desktop(8, "ℂFG, 𝛌Q1: 📚 Old scheduler work", isArchived=True),
        "strange": running(9, "𝛌G3, #12: 🧱 Unknown prefix"),
        "merged": running(10, "VC: 🪻 #77 Landed work"),
        "waiting": running(11, "VD: 📚 (VC) Waits on landed work"),
        "digit": running(12, "1A: 🧱 Holds a digit worktree"),
        "by-directory": running(13, "🧱 Works by directory",
                                cwd=os.path.join(LABS, "VE", "src")),
        "limit": desktop(14, "🧱 Hit the limit", records=[
            user("go"), assistant("You've hit your limit", isApiErrorMessage=True)]),
        "no-transcript": desktop(15, "🧱 Never started"),
        "busy": running(16, "🧱 Busy now", status="busy",
                        records=[user("go"), assistant("running", stop="tool_use")]),
        "unlisted": running(17, "📚 Android photos"),
        "moved": desktop(18, "🧱 Moved away", cwd=os.path.join(HOME, "dev", "gone"),
                         lastActivityAt=idle, records=FINISHED),
        "long-tail": desktop(21, "🧱 Long tail", records=FINISHED + [
            user("a subagent's message", 1, isSidechain=True),
            {"type": "custom-title", "timestamp": stamp(1), "padding": "x" * 100000}]),
        "archived-moved": desktop(22, "🧱 Archived and moved", isArchived=True,
                                  cwd=os.path.join(HOME, "dev", "gone")),
        "gone-worktree": running(23, "VZ: 🧱 Gone worktree"),
        "restarted": desktop(24, "🧱 Restarted", cliSessionId=uuid(2024),
                             priorCliSessionIds=[uuid(3024), uuid(4024)]),
        "stacked-two": running(25, "VH: 📚 (EQ, V5) Waits on EQ"),
        "empty": desktop(27, "🧱 Empty transcript", records=[
            {"type": "custom-title", "timestamp": stamp(1), "customTitle": "x"}]),
        "replayed-then-shell": desktop(28, "🧱 Replayed notice, then a shell command", records=[
            user("go", 40), hand_back("a9", 30), assistant("seen", minutes_ago=29),
            {"type": "custom-title", "timestamp": stamp(20), "padding": "x" * 100000},
            user("more", 10), assistant("done", minutes_ago=9), notice("a9", 2),
            user("<bash-input>ls</bash-input>", 1)]),
        "replayed-twice": desktop(29, "🧱 Two replayed notices", records=[
            user("go", 40), hand_back("a9", 30), assistant("seen", minutes_ago=29),
            {"type": "custom-title", "timestamp": stamp(20), "padding": "x" * 100000},
            user("more", 10), hand_back("a8", 9), assistant("done", minutes_ago=8),
            notice("a9", 2), notice("a8", 1)]),
        "old-launch": desktop(36, "🧱 Launched long before the end", records=[
            user("go", 50), launched("b8", 49), assistant("running", minutes_ago=48),
            {"type": "custom-title", "timestamp": stamp(20), "padding": "x" * 100000},
            user("more", 10), assistant("still running", minutes_ago=9)]),
        "old-subagent": desktop(39, "🧱 Subagent started long before the end", records=[
            user("go", 50), subagent("a8", 49), assistant("running", minutes_ago=48),
            {"type": "custom-title", "timestamp": stamp(20), "padding": "x" * 100000},
            user("more", 10), assistant("still running", minutes_ago=9)]),
        "old-launch-ended": desktop(37, "🧱 Launched and ended long before the end", records=[
            user("go", 50), launched("b7", 49), notice("b7", 40),
            assistant("it ended", minutes_ago=39),
            {"type": "custom-title", "timestamp": stamp(20), "padding": "x" * 100000},
            user("more", 10), assistant("done", minutes_ago=9)]),
        "early-ends": desktop(38, "🧱 Tasks that ended long before the end", records=[
            user("go", 60), subagent("a6", 59),
            launched("m6", 58, "taskId"),
            launched("b6", 57), hand_back("a6", 50),
            user("<task-notification>\n<task-id>m6</task-id>\n<event>[Monitor expired after "
                 "5m with no events delivered.]</event>\n</task-notification>", 49),
            {**assistant("stopping"), "message": {"role": "assistant", "stop_reason": "end_turn",
                                                  "content": [{"type": "tool_use", "id": "s",
                                                               "name": "TaskStop",
                                                               "input": {"task_id": "b6"}}]}},
            {"type": "custom-title", "timestamp": stamp(20), "padding": "x" * 100000},
            user("more", 10), assistant("done", minutes_ago=9), notice("a6", 1)]),
        "queued-replay": desktop(35, "🧱 Queued replay", records=[
            user("go", 40), hand_back("a7", 30), assistant("seen", minutes_ago=29),
            {"type": "custom-title", "timestamp": stamp(20), "padding": "x" * 100000},
            user("more", 10), assistant("done", minutes_ago=9),
            queue("enqueue", 1, notice("a7")["message"]["content"])]),
        "stopped-long-ago": desktop(30, "🧱 Stopped long ago", lastActivityAt=idle, records=[
            user("go"), user("[Request interrupted by user]")]),
        "unanswered": desktop(31, "🧱 Unanswered notice", records=FINISHED + [notice("zz")]),
        "absorbed": desktop(32, "🧱 Absorbed report", records=[
            user("go", 70), subagent("a5", 60), absorbed(hand_back("a5"), 30),
            absorbed(notice("a5"), 30), assistant("done", minutes_ago=29)]),
        "merged-killed": desktop(33, "🪻 Merged, and its watcher was killed",
                                 records=FINISHED + [queue("enqueue", 1, KILLED_NOTICE)]),
        "watching-killed": desktop(34, "🦚 Watching, and its watcher was killed",
                                   records=FINISHED + [queue("enqueue", 1, KILLED_NOTICE)]),
        "zebra": desktop(40, "🧱 Zebra hunt", records=[
            user("find the zebra please", 30),
            user([{"type": "tool_result", "tool_use_id": "t", "content": "zebra.txt"}], 29),
            user("a zebra a subagent saw", 28, isSidechain=True),
            assistant("found the Zebra in the stable", minutes_ago=27),
            user('the keeper said "stripes"\tthen\nleft', 26), assistant("noted", minutes_ago=25),
            user("Stop hook feedback: zebra", 24, isMeta=True),
            user("<task-notification>\n<summary>zebra done</summary>\n</task-notification>", 23),
            user("<system-reminder>a zebra</system-reminder>", 22),
            user("Summary of the conversation: a zebra", 21, isCompactSummary=True),
            assistant("ok", minutes_ago=20)]),
        "replayed": desktop(26, "🧱 Replayed notice", records=[
            user("go", 40), hand_back("a9", 30), assistant("seen", minutes_ago=29),
            {"type": "custom-title", "timestamp": stamp(20), "padding": "x" * 100000},
            user("more", 10), assistant("done", minutes_ago=9), notice("a9", 1)]),
    }
    # Two sessions started in a terminal, which the desktop app does not know.
    for n, title in ((19, "VF: 🧱 Terminal one"), (20, "VG: 🧱 Terminal two")):
        process(n, None, title, os.path.join(HOME, "dev", "commonfabric"))
        transcript(uuid(1000 + n), FINISHED)
    ids["terminal-1"], ids["terminal-2"] = uuid(1019), uuid(1020)
    transcript(uuid(3024), [user("go"), assistant("running", stop="tool_use")])
    transcript(uuid(4024), FINISHED)
    # A second process naming the same session as the first.
    process(1, ids["vb"], "VB: 🟠 #10235 Highlight Jinja templates",
            os.path.join(HOME, "dev", "commonfabric"))
    # Copies of a session file set aside beside the real directory.
    desktop(1, "VB: 🧱 Stale backup title", folder=ORG + ".before-recover.abcd1234")
    desktop(99, "ℂFG: 🧱 Superseded copy", folder=ORG + ".superseded.Ab12Cd")
    # The same session in a second account, and a file that is not JSON.
    desktop(2, "VA: 🧱 An older copy", account=OTHER_ACCOUNT, lastActivityAt=idle)
    with open(os.path.join(SUPPORT, ACCOUNT, ORG, "local_broken.json"), "w") as handle:
        handle.write("{")
    # A file deleted between listing the directory and reading it.
    os.symlink(os.path.join(HOME, "nowhere"),
               os.path.join(SUPPORT, ACCOUNT, ORG, "local_deleted.json"))

    os.makedirs(os.path.join(HOME, ".codex"))
    database = sqlite3.connect(os.path.join(HOME, ".codex", "state_5.sqlite"))
    database.execute("CREATE TABLE threads (id TEXT, cwd TEXT, name TEXT, archived INTEGER, "
                     "source TEXT, rollout_path TEXT, model TEXT, updated_at_ms INTEGER, "
                     "created_at_ms INTEGER, reasoning_effort TEXT)")
    database.executemany("INSERT INTO threads VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [
        (tid, "/w", name, archived, source,
         rollout(tid, ending, hours, *{"codex-open": ("where is the zebra?", None),
                                       "codex-archived": ("an old zebra", None),
                                       "1a2b3c4d-codex": (None, "a zebra crossing")}.get(
                                           tid, ())), "gpt",
         NOW_MS - hours * HOUR_MS, NOW_MS - (hours + 1) * HOUR_MS, "high")
        for tid, name, archived, source, ending, hours in [
            ("codex-open", "ℂEJ: 🐤 Codex takes EJ too", 0, "vscode", "task_complete", 1),
            ("codex-archived", "VB: 🪻 Old", 1, "vscode", "task_complete", 14),
            ("codex-sub", "VB: helper", 0, '{"subagent": "review"}', "task_complete", 15),
            ("1a2b3c4d-codex", "🐤 Unrelated thread", 0, "vscode", "turn_aborted", 13),
            ("codex-untitled", "", 0, "vscode", "task_complete", 16),
            ("codex-paused", "⏸️ Paused Codex work", 0, "vscode", "task_complete", 17),
            # A quit aborts every thread's turn in the same second.
            ("codex-quit-a", "🧱 Working when Codex quit", 0, "vscode", "turn_aborted", 20),
            ("codex-quit-b", "🧱 Also working when Codex quit", 0, "vscode", "turn_aborted", 20),
        ]])
    database.commit()
    database.close()
    return ids


IDS = build()
os.environ["HOME"] = HOME
sys.dont_write_bytecode = True
_loader = importlib.machinery.SourceFileLoader("agent_sessions", TOOL)
agent_sessions = importlib.util.module_from_spec(
    importlib.util.spec_from_loader("agent_sessions", _loader))
_loader.exec_module(agent_sessions)

gate = agent_sessions.gate


def ref(sid):
    """How JSON output names a fixture session."""
    harness = ("claude-desktop" if sid.startswith("local_")
               else "codex" if "codex" in sid else "claude-cli")
    return {"harness": harness, "id": sid}


def invoke(*argv):
    """The tool's standard output, standard error, and exit status."""
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            agent_sessions.main(list(argv))
        except SystemExit as exit:
            code = exit.code
    return out.getvalue(), err.getvalue(), code


def run(*argv):
    """The tool's JSON output and exit status for a command line."""
    out, _, code = invoke("--json", *argv)
    return json.loads(out) if out else None, code


def text(*argv):
    return invoke(*argv)[0]


class Titles(unittest.TestCase):
    def test_worktrees_state_and_bases(self):
        title = agent_sessions.parse_title("ℂEJ, VA: 📚 (ℂFG, labs-VB) Split it")
        self.assertEqual(title.worktrees, {("cfs", "EJ"), ("labs", "VA")})
        self.assertEqual(title.state, "📚")
        self.assertEqual(title.bases, [("cfs", "FG"), ("labs", "VB")])
        self.assertEqual(title.unrecognised, [])

    def test_no_worktrees(self):
        title = agent_sessions.parse_title("⏸️ Owner attestation (draft)")
        self.assertEqual((title.worktrees, title.state, title.bases), (set(), "⏸️", []))

    def test_parentheses_only_list_bases_when_stacked(self):
        title = agent_sessions.parse_title("VA: 🧱 (VB) not stacked")
        self.assertEqual((title.state, title.bases), ("🧱", []))
        self.assertEqual(agent_sessions.parse_title("📚 Android photos").bases, [])

    def test_no_state(self):
        for title in ("VA: #12 fix it", "Plain words", "<>: odd", "VA: , list"):
            self.assertEqual(agent_sessions.parse_title(title).state, "", title)

    def test_unrecognised_items(self):
        title = agent_sessions.parse_title("𝛌G3, #12, VA: 📚 (nowhere) Work")
        self.assertEqual(title.worktrees, {("labs", "VA")})
        self.assertEqual(title.unrecognised, ["𝛌G3", "nowhere"])


class Reading(unittest.TestCase):
    def test_damaged_and_duplicated_files_are_reported(self):
        _, err, code = invoke("list")
        self.assertEqual(code, 0)
        self.assertIn("skipping %s" % os.path.join(SUPPORT, ACCOUNT, ORG, "local_broken.json"),
                      err)
        self.assertIn("%s has more than one file" % IDS["va"], err)

    def test_a_failing_gate_reports_on_standard_error(self):
        broken = os.path.join(HOME, ".codex", "state_9.sqlite")
        with open(broken, "w") as handle:
            handle.write("not a database")
        gate.live_sessions.cache_clear()
        self.addCleanup(gate.live_sessions.cache_clear)
        self.addCleanup(os.remove, broken)
        out, err, code = invoke("--json", "list")
        self.assertEqual(out, "")
        self.assertEqual(err, "")
        self.assertRegex(code, r"^agent-sessions: the spawn gate could not list the live "
                               r"sessions: The Codex thread list in \S+state_9.sqlite could "
                               r"not be read, .*: file is not a database$")

    def test_transcript_tail(self):
        data = "".join('{"n": %d}\n' % n for n in range(100)).encode() + b'{"n": 1'
        start, records = agent_sessions.split_tail(data, 30)
        self.assertEqual(records, [{"n": 97}, {"n": 98}, {"n": 99}])
        self.assertEqual(data[start:start + 9], b'{"n": 97}')
        self.assertEqual(agent_sessions.split_tail(data, 1 << 16),
                         (0, [{"n": n} for n in range(100)]))


class Listing(unittest.TestCase):
    def test_default_lists_current_sessions_once(self):
        rows, code = run("list")
        self.assertEqual(code, 0)
        ids = [row["id"] for row in rows]
        self.assertEqual(len(ids), len(set(ids)))
        for key in ("vb", "va", "dormant", "unguarded", "limit", "terminal-1", "terminal-2"):
            self.assertIn(IDS[key], ids)
        self.assertIn("codex-open", ids)
        for absent in (IDS["archived"], "codex-archived", "codex-sub", "local_" + uuid(99)):
            self.assertNotIn(absent, ids)
        vb = next(row for row in rows if row["id"] == IDS["vb"])
        self.assertEqual(vb["title"], "VB: 🟠 #10235 Highlight Jinja templates")
        self.assertEqual(vb["status"], "running")

    def test_all_adds_archived_but_never_backups_or_subagents(self):
        ids = [row["id"] for row in run("list", "--all")[0]]
        self.assertIn(IDS["archived"], ids)
        self.assertIn("codex-archived", ids)
        self.assertNotIn("codex-sub", ids)
        self.assertNotIn("local_" + uuid(99), ids)

    def test_statuses(self):
        status = {row["id"]: row["status"] for row in run("list", "--all")[0]}
        self.assertEqual(status[IDS["va"]], "running")
        self.assertEqual(status[IDS["dormant"]], "dormant")
        self.assertEqual(status[IDS["archived"]], "archived")
        self.assertEqual(status["codex-open"], "open")
        self.assertEqual(status["codex-archived"], "archived")
        self.assertEqual(status["codex-untitled"], "untitled")
        self.assertNotIn("codex-untitled", {row["id"] for row in run("list")[0]})

    def test_filters(self):
        def ids(*argv):
            return {row["id"] for row in run("list", *argv)[0]}
        self.assertEqual(ids("--state", "📚"), {IDS["va"], IDS["stacked-dangling"],
                                                 IDS["waiting"], IDS["unlisted"],
                                                 IDS["stacked-two"]})
        self.assertEqual(ids("--mode", "bypassPermissions"), {IDS["dormant"]})
        self.assertEqual(ids("--grep", "GIZMO"), {IDS["unguarded"]})
        self.assertEqual(ids("--grep", "terraform|jinja"), {IDS["va"], IDS["vb"]})
        self.assertEqual(ids("--grep", "no such words"), set())

    def test_text_line_has_status_harness_id_title_and_mode(self):
        line = next(l for l in text("list").splitlines() if IDS["dormant"] in l)
        self.assertRegex(line, r'^dormant +claude-desktop +%s +"VA, V5: ⏸️ Paused work" +'
                               r'\(bypassPermissions, claude-opus-5-5\)$' % IDS["dormant"])
        line = next(l for l in text("list").splitlines() if "codex-open" in l)
        self.assertRegex(line, r'^open +codex +codex-open +"ℂEJ: 🐤 Codex takes EJ too" +\(gpt\)$')

    def test_harnesses(self):
        def ids(*harnesses):
            return {row["id"] for row in run("list", *(
                part for harness in harnesses for part in ("--harness", harness)))[0]}
        everything = ids()
        codex = ids("codex")
        desktop, terminal = ids("claude-desktop"), ids("claude-cli")
        self.assertEqual(codex, {"codex-open", "1a2b3c4d-codex", "codex-paused", "codex-quit-a",
                                 "codex-quit-b"})
        self.assertEqual(terminal, {IDS["terminal-1"], IDS["terminal-2"]})
        self.assertIn(IDS["vb"], desktop)
        self.assertEqual(ids("claude"), desktop | terminal)
        self.assertEqual(ids("codex", "claude-cli"), codex | terminal)
        self.assertEqual(everything, desktop | terminal | codex)
        self.assertEqual(invoke("list", "--harness", "gemini")[2], 2)

    def test_options_go_before_or_after_the_command(self):
        self.assertEqual(text("--json", "list"), text("list", "--json"))
        self.assertNotEqual(text("list"), text("list", "--json"))
        self.assertEqual(text(), text("list"))
        self.assertEqual(text("list", "--grep", "wake"), "")
        out, _, code = invoke("--help")
        self.assertEqual(code, 0)
        self.assertIn("{list,show,worktrees,check,free,wake,search,graph}", out)
        self.assertEqual(invoke("check", "--all")[2], 2)
        self.assertIn("--all applies only to list and show", invoke("--all", "free", "labs")[1])


class Show(unittest.TestCase):
    def test_ids_of_every_harness(self):
        for query, found in ((IDS["va"], IDS["va"]), (IDS["va"][6:], IDS["va"]),
                             (IDS["va"][:14], IDS["va"]), (uuid(1002), IDS["va"]),
                             (uuid(1002)[:8], IDS["va"]), (uuid(1019), IDS["terminal-1"]),
                             ("codex-open", "codex-open")):
            rows, code = run("show", "--session", query)
            self.assertEqual(([row["id"] for row in rows], code), ([found], 0), query)
        [row], _ = run("show", "--session", IDS["vb"])
        self.assertEqual(row["harness"], "claude-desktop")
        [row], _ = run("show", "--session", uuid(1019))
        self.assertEqual(row["harness"], "claude-cli")

    def test_harness_narrows_the_names(self):
        # The names are ORed together; --harness narrows the result.
        rows, code = run("show", "--worktree", "ℂEJ", "--session", IDS["vb"])
        self.assertEqual(({row["id"] for row in rows}, code),
                         ({IDS["stacked-dangling"], "codex-open", IDS["vb"]}, 0))
        rows, code = run("show", "--worktree", "ℂEJ", "--session", IDS["vb"], "--harness", "codex")
        self.assertEqual([row["id"] for row in rows], ["codex-open"])
        self.assertIn("no session matches --session %s;" % IDS["vb"], code)
        self.assertEqual(run("show", "--session", "codex-open", "--harness", "claude")[0], [])

    def test_facts(self):
        [vb], _ = run("show", "--session", IDS["vb"])
        self.assertEqual(vb["worktrees"], ["VB"])
        self.assertEqual(vb["cliSessionIds"], [uuid(1001)])
        self.assertEqual(vb["processStatus"], "idle")
        self.assertIsInstance(vb["pid"], int)
        self.assertEqual(vb["lastTurn"], "finished")
        self.assertEqual(vb["transcripts"], [os.path.join(
            HOME, ".claude", "projects", "-x", uuid(1001) + ".jsonl")])
        [limit], _ = run("show", "--session", IDS["limit"])
        self.assertEqual((limit["lastTurn"], limit["lastTurnWhy"]),
                         ("interrupted", "an API error: You've hit your limit"))
        self.assertRegex(vb["lastActivity"], r"^\d{4}-\d\d-\d\dT\d\d:\d\dZ$")
        [va], _ = run("show", "--session", IDS["va"])
        self.assertEqual((va["state"], va["stackedOn"]), ("📚", ["VB"]))
        self.assertEqual(va["spawnedFrom"], "local_parent")
        [restarted], _ = run("show", "--session", IDS["restarted"])
        self.assertEqual(restarted["cliSessionIds"], [uuid(2024), uuid(4024), uuid(3024)])
        self.assertEqual(restarted["lastTurn"], "finished")
        [unseen], _ = run("show", "--session", IDS["no-transcript"])
        self.assertEqual(unseen["transcripts"], [])

    def test_long_tail_without_messages(self):
        [row], _ = run("show", "--session", IDS["long-tail"])
        self.assertEqual(row["lastTurn"], "finished")
        for key in ("replayed", "replayed-then-shell", "replayed-twice", "absorbed",
                    "queued-replay", "old-launch-ended", "early-ends"):
            [row], _ = run("show", "--session", IDS[key])
            self.assertEqual(row["lastTurn"], "finished", key)

    def test_terminal_sessions(self):
        [row], _ = run("show", "--worktree", "VF")
        self.assertEqual((row["id"], row["status"], row["lastTurn"]),
                         (IDS["terminal-1"], "running", "finished"))
        self.assertEqual(row["transcripts"], [os.path.join(
            HOME, ".claude", "projects", "-x", uuid(1019) + ".jsonl")])

    def test_working_directory_claims(self):
        [row], _ = run("show", "--session", IDS["by-directory"])
        self.assertEqual(row["worktrees"], ["VE"])
        self.assertEqual({r["id"] for r in run("show", "--worktree", "VE")[0]},
                         {IDS["by-directory"]})

    def test_by_worktree(self):
        def ids(query):
            return {row["id"] for row in run("show", "--worktree", query)[0]}
        self.assertEqual(ids("VB"), {IDS["vb"], IDS["va"]})
        self.assertEqual(ids("labs VB"), ids("VB"))
        self.assertEqual(ids("INFRAE0"), {IDS["infra-1"], IDS["infra-2"]})
        self.assertEqual(ids("ℂEJ"), {IDS["stacked-dangling"], "codex-open"})
        self.assertEqual(ids(os.path.join(HOME, "dev", "contraptions")), {IDS["unguarded"]})

    def test_a_short_name_is_read_in_the_kind_given(self):
        self.assertEqual({row["id"] for row in run("show", "--worktree", "1a")[0]},
                         {IDS["digit"]})
        self.assertEqual({row["id"] for row in run("show", "--session", "1a")[0]},
                         {"1a2b3c4d-codex"})

    def test_a_name_is_needed(self):
        _, err, code = invoke("show")
        self.assertEqual(code, 2)
        self.assertIn("show needs at least one of --session, --worktree", err)
        for option, value, error in (("--worktree", "nowhere at all",
                                      "'nowhere at all' names no worktree"),
                                     ("--session", "", "an ID cannot be empty"),
                                     ("--session", "local_", "an ID cannot be empty"),
                                     ):
            _, err, code = invoke("show", option, value)
            self.assertEqual(code, 2, (option, value))
            self.assertIn(error, err)

    def test_some_names_match_and_some_do_not(self):
        rows, code = run("show", "--session", IDS["va"], "--session", "zzz")
        self.assertEqual([row["id"] for row in rows], [IDS["va"]])
        self.assertIn("no session matches --session zzz;", code)

    def test_earlier_claude_code_sessions(self):
        for cli in (uuid(2024), uuid(3024), uuid(4024)):
            self.assertEqual([row["id"] for row in run("show", "--session", cli)[0]],
                             [IDS["restarted"]], cli)

    def test_each_session_once(self):
        rows, _ = run("show", "--worktree", "VA", "--worktree", "V5", "--session", IDS["dormant"])
        ids = [row["id"] for row in rows]
        self.assertEqual(sorted(ids), sorted({IDS["va"], IDS["dormant"], IDS["infra-2"],
                                              IDS["stacked-two"]}))

    def test_text(self):
        out = text("show", "--session", IDS["vb"], "--session", IDS["va"])
        self.assertIn("\n\nharness: claude-desktop\nid: %s\n" % IDS["va"], out)
        self.assertIn('worktrees: ["VB"]\n', out)
        self.assertNotIn("permissionMode: None", out)

    def test_archived_only_with_all(self):
        self.assertEqual(run("show", "--session", IDS["archived"])[1],
                         "agent-sessions: no session matches --session %s; --all includes "
                         "archived sessions and untitled Codex threads" % IDS["archived"])
        [row], code = run("show", "--all", "--session", IDS["archived"])
        self.assertEqual((code, row["status"]), (0, "archived"))

    def test_codex_thread(self):
        [row], _ = run("show", "--session", "codex-open")
        self.assertEqual((row["harness"], row["transcripts"]), ("codex", [os.path.join(
            HOME, ".codex", "sessions", "codex-open.jsonl")]))
        self.assertEqual((row["model"], row["effort"]), ("gpt", "high"))
        self.assertEqual(row["created"], agent_sessions.timestamp(NOW_MS - 2 * HOUR_MS))
        self.assertEqual(row["lastTurn"], "finished")

    def test_no_match(self):
        rows, code = run("show", "--session", "zzz", "--session", "yyy")
        self.assertEqual(rows, [])
        self.assertIn("no session matches --session zzz, --session yyy;", code)


class Worktrees(unittest.TestCase):
    def setUp(self):
        self.trees = {row["worktree"]: row for row in run("worktrees")[0]}

    def test_claimed_worktrees(self):
        self.assertEqual(set(self.trees), {"VA", "VB", "V5", "VC", "VD", "VE", "VF", "VG",
                                           "VH", "VZ", "EQ", "1A", "ℂEJ", "ℂFG", "ℂEG",
                                           "INFRAE0", "contraptions"})

    def test_holders_are_the_gates(self):
        live = gate.live_sessions()
        for row in self.trees.values():
            kind, name, path = agent_sessions.resolve_worktree(row["worktree"])
            self.assertEqual({r["id"] for r in row["heldBy"]}, {s.host or s.id for s in live
                                                  if gate.holds(s, kind, name, path)}, row)

    def test_details(self):
        self.assertEqual(self.trees["VB"]["heldBy"], [ref(IDS["vb"])])
        self.assertEqual(self.trees["VB"]["stackedOnBy"], [ref(IDS["va"])])
        self.assertEqual(self.trees["VA"]["dormantClaims"], [ref(IDS["dormant"])])
        self.assertEqual(self.trees["ℂEJ"]["heldBy"], [ref(IDS["stacked-dangling"]),
                                                      ref("codex-open")])
        self.assertFalse(self.trees["ℂFG"]["exists"])
        self.assertTrue(self.trees["ℂEJ"]["exists"])
        self.assertEqual(self.trees["ℂFG"]["heldBy"], [])

    def test_query(self):
        rows, _ = run("worktrees", "VB", "labs V5", "EF")
        self.assertEqual([(row["worktree"], row["heldBy"]) for row in rows],
                         [("EF", []), ("V5", [ref(IDS["infra-2"])]), ("VB", [ref(IDS["vb"])])])
        self.assertEqual(run("worktrees", "VB", "nowhere at all")[1],
                         "agent-sessions: nowhere at all names no worktree")

    def test_text(self):
        out = text("worktrees", "VB", "VA", "ℂFG")
        self.assertIn('VB  %s\n  held by "VB: 🟠 #10235 Highlight Jinja templates" (claude-desktop '
                      '%s)\n  stacked on by "VA: 📚 (VB) Terraform templates in cf view" '
                      '(claude-desktop %s)\n' % (os.path.join(LABS, "VB"), IDS["vb"], IDS["va"]),
                      out)
        self.assertIn('; claimed without a running process by "VA, V5: ⏸️ Paused work" '
                      '(claude-desktop %s)' % IDS["dormant"], out)
        self.assertIn("(missing)\n  no session claims it\n", out)


class Check(unittest.TestCase):
    def test_problems(self):
        rows, code = run("check")
        self.assertEqual(code, 1)
        found = {}
        for row in rows:
            found.setdefault(row["problem"], []).append(row["text"])
        self.assertEqual(set(found), {"conflict", "missing", "unguarded", "unheld-base",
                                      "finished-base", "unrecognised", "unlisted-base",
                                      "lost-folder"})
        [missing] = found["missing"]
        self.assertIn('VZ is claimed by "VZ: 🧱 Gone worktree" (claude-desktop %s), but %s does '
                      'not exist' % (IDS["gone-worktree"], os.path.join(LABS, "VZ")), missing)
        conflicts = "\n".join(found["conflict"])
        self.assertIn("INFRAE0 is held by 2 sessions", conflicts)
        self.assertIn("ℂEJ is held by 2 sessions", conflicts)
        self.assertNotIn("VB", conflicts)
        self.assertEqual(len(found["unguarded"]), 1)
        self.assertIn("contraptions is claimed only by", found["unguarded"][0])
        bases = "\n".join(found["unheld-base"])
        self.assertIn("stacked on ℂFG, which no session claims, and", bases)
        self.assertIn("stacked on ℂEG", bases)
        self.assertIn('Waits on EQ" (claude-desktop %s) is stacked on EQ, which no session '
                      'claims\n' % IDS["stacked-two"], bases + "\n")
        self.assertNotIn("on VB", bases)
        [finished] = found["finished-base"]
        self.assertIn('Waits on landed work" (claude-desktop %s) is stacked on VC' % IDS["waiting"],
                      finished)
        self.assertIn(IDS["merged"], finished)
        self.assertEqual(len(found["unrecognised"]), 1)
        self.assertIn("lists `𝛌G3`, which is no worktree", found["unrecognised"][0])
        self.assertEqual(found["unlisted-base"], [
            '"📚 Android photos" (claude-desktop %s) is stacked, but its title lists no '
            "worktree it is stacked on" % IDS["unlisted"]])
        self.assertEqual(found["lost-folder"], [
            '"🧱 Moved away" (claude-desktop %s) works in %s, which no longer exists, so the '
            "app cannot deliver messages to it" % (IDS["moved"], os.path.join(HOME, "dev", "gone"))])

    def test_missing_claims(self):
        problems = agent_sessions.problems([agent_sessions.Session(
            "claude", "local_x", "ℂZZ: 🧱 Nowhere", HOME, None, {"isArchived": False})])
        self.assertEqual([kind for kind, _ in problems], ["missing", "unguarded"])
        present = [agent_sessions.Session("claude", "local_y", "VA: 🧱 Fine", HOME, None, {})]
        self.assertEqual([kind for kind, _ in agent_sessions.problems(present)], ["unguarded"])

    def test_text(self):
        self.assertIn("conflict: INFRAE0 is held by 2 sessions: ", text("check"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            agent_sessions.command_check(argparse.Namespace(json=False), [])
        self.assertEqual(out.getvalue(), "no problems found\n")


class Free(unittest.TestCase):
    def test_free_worktrees(self):
        # 1A is claimed, EQ has a session stacked on it, EK has uncommitted
        # changes, EA and EH are not on upstream's main, and EZ is not a
        # repository.
        rows, code = run("free", "labs")
        self.assertEqual(code, 0)
        self.assertEqual([(row["worktree"], row["branch"], row["landed"]) for row in rows],
                         [("2B", "2b", True), ("EF", "ef", True)])

    def test_harness(self):
        def free(*harnesses):
            return [row["worktree"] for row in run("free", "labs", *(
                part for harness in harnesses for part in ("--harness", harness)))[0]]
        self.assertEqual(free("codex"), ["2B"])
        self.assertEqual(free("claude"), ["EF"])
        self.assertEqual(invoke("free", "labs", "--harness", "claude-desktop")[2], 2)
        self.assertEqual(free("codex", "claude"), free())

    def test_unlanded(self):
        rows, _ = run("free", "labs", "--unlanded")
        self.assertEqual([(row["worktree"], row["landed"]) for row in rows],
                         [("2B", True), ("EF", True), ("EA", False), ("EH", False)])
        self.assertIn("EH  %s  eh  (has commits that are not on main)"
                      % os.path.join(LABS, "EH"), text("free", "labs", "--unlanded"))

    def test_main_branch_of_origin_or_of_no_remote(self):
        self.assertEqual([row["worktree"] for row in run("free", "cfs")[0]], ["ℂEM"])
        self.assertEqual(text("free", "infra"), "no free infra worktrees\n")
        self.assertEqual([(row["worktree"], row["landed"])
                          for row in run("free", "infra", "--unlanded")[0]],
                         [("INFRAEP", False)])

    def test_prefix_and_other_repositories(self):
        self.assertEqual(run("free", "labs", "--prefix", "v")[0], [])
        self.assertEqual([row["worktree"] for row in run("free", "labs", "--prefix", "e")[0]],
                         ["EF"])
        self.assertEqual(run("free", "contraptions")[1],
                         "agent-sessions: contraptions is not a repository with worktrees")


class Cache(unittest.TestCase):
    def test_changed_files_are_read_again(self):
        path = os.path.join(SUPPORT, ACCOUNT, ORG, IDS["unguarded"] + ".json")
        with open(path, encoding="utf-8") as handle:
            original = json.load(handle)
        self.addCleanup(write, path, original)
        before = {row["id"]: row["title"] for row in run("list")[0]}
        self.assertEqual(before[IDS["unguarded"]], "contraptions: ✅ Finished tool")
        self.assertTrue(os.path.exists(agent_sessions.CACHE))
        write(path, {**original, "title": "contraptions: 🧱 Renamed"})
        after = {row["id"]: row["title"] for row in run("list")[0]}
        self.assertEqual(after[IDS["unguarded"]], "contraptions: 🧱 Renamed")
        self.assertEqual({k: v for k, v in after.items() if k != IDS["unguarded"]},
                         {k: v for k, v in before.items() if k != IDS["unguarded"]})

    def test_cache_written_for_other_fields_is_ignored(self):
        run("list")
        with open(agent_sessions.CACHE, encoding="utf-8") as handle:
            saved = json.load(handle)
        for entry in saved["files"].values():
            entry[1]["title"] = "stale"
        saved["fields"] = ["title"]
        write(agent_sessions.CACHE, saved)
        titles = [row["title"] for row in run("list")[0]]
        self.assertNotIn("stale", titles)
        write(agent_sessions.CACHE, "not a cache")
        self.assertEqual([row["title"] for row in run("list")[0]], titles)


class LastTurn(unittest.TestCase):
    def verdict(self, records, started=None, done=False):
        return agent_sessions.turn_verdict(records, started, done)

    def test_finished(self):
        self.assertEqual(self.verdict(FINISHED), ("finished", ""))
        for stop in ("refusal", "max_tokens", "stop_sequence"):
            self.assertEqual(self.verdict([user("go"), assistant("no", stop=stop)]),
                             ("finished", ""), stop)

    def test_interrupted_endings(self):
        for records, why in [
            ([user("go"), assistant("Overloaded", isApiErrorMessage=True)],
             "an API error: Overloaded"),
            ([user("go"), assistant("No response requested.", stop="stop_sequence")],
             "the harness cut its turn short"),
            ([user("go"), assistant("running", stop="tool_use")], "a tool call never returned"),
            ([user("go"), assistant("half", stop=None)], "its reply stopped partway"),
            ([user("go"), launched("b1", 5)], "it never replied to a tool result"),
            (FINISHED + [user("and now this")], "it never replied to its last message"),
        ]:
            self.assertEqual(self.verdict(records), ("interrupted", why), records)

    def test_stopped(self):
        self.assertEqual(self.verdict([user("go"), user("[Request interrupted by user]")]),
                         ("stopped", ""))

    def test_notifications(self):
        unanswered = ("interrupted", "it never replied to its last message")
        for earlier, last, verdict in [
            (hand_back("a1", 10), notice("a1"), ("finished", "")),
            (notice("b1", 10), notice("b1"), ("finished", "")),
            (monitor_event("b1", 10), notice("b1"), unanswered),
            (monitor_event("b1", 10), monitor_event("b1"), unanswered),
            (hand_back("a1", 10), notice("a2"), unanswered),
            (hand_back("a1", 10), hand_back("a1"), unanswered),
        ]:
            records = [earlier, assistant("seen", minutes_ago=9)] + FINISHED + [last]
            self.assertEqual(self.verdict(records), verdict, (earlier, last))

    def test_failed_tasks_end(self):
        records = [user("go", 70), launched("b1", 60), notice("b1", 10, "failed"),
                   assistant("it failed; fixed", minutes_ago=9)]
        self.assertEqual(self.verdict(records), ("finished", ""))

    def test_hand_backs_that_quote_a_killed_status(self):
        quoting = user('<agent-message from="a3">\nThe task said <status>killed</status>.\n'
                       "</agent-message>", 1)
        unanswered = ("interrupted", "it never replied to its last message")
        self.assertEqual(self.verdict(FINISHED + [quoting]), unanswered)
        self.assertEqual(self.verdict(FINISHED + [quoting], done=True), unanswered)
        self.assertEqual(self.verdict(FINISHED + [queue("enqueue", 1, message_of(quoting))]),
                         ("interrupted", "a message queued for it was never delivered"))

    def test_finished_work_does_not_hide_messages(self):
        kill = notice("b5", 1, "killed")
        self.assertEqual(self.verdict(FINISHED + [user("please also fix X", 2), kill], done=True),
                         ("interrupted", "it never replied to its last message"))
        queued = FINISHED + [queue("enqueue", 2, "please also fix X"),
                             queue("enqueue", 1, kill["message"]["content"])]
        self.assertEqual(self.verdict(queued, done=True),
                         ("interrupted", "a message queued for it was never delivered"))
        self.assertEqual(self.verdict(FINISHED + [kill], done=True), ("finished", ""))

    def test_killed_tasks(self):
        killed = ("interrupted", agent_sessions.KILLED)
        for status in ("killed", "stopped"):
            notice_text = ("<task-notification>\n<task-id>b4</task-id>\n<status>%s</status>\n"
                           "</task-notification>" % status)
            self.assertEqual(self.verdict(FINISHED + [user(notice_text)]), killed)
            self.assertEqual(self.verdict(FINISHED + [queue("enqueue", 1, notice_text)]), killed)
            stop = {"type": "tool_use", "id": "s", "name": "TaskStop", "input": {"task_id": "b4"}}
            own = [user("go", 10), {**assistant("stopping"), "message": {
                "role": "assistant", "stop_reason": "tool_use", "content": [stop]}},
                   user([{"type": "tool_result", "tool_use_id": "s", "content": "ok"}], 3),
                   assistant("done", minutes_ago=2)]
            self.assertEqual(self.verdict(own + [user(notice_text, 1)]), ("finished", ""))
            self.assertEqual(self.verdict(own + [queue("enqueue", 1, notice_text)]),
                             ("finished", ""))

    def test_queued_messages(self):
        self.assertEqual(self.verdict(FINISHED + [queue("enqueue")]),
                         ("interrupted", "a message queued for it was never delivered"))
        delivered = [queue("enqueue", 3, "do X"), queue("dequeue", 3), user("do X", 2),
                     assistant("done X", minutes_ago=1)]
        self.assertEqual(self.verdict(FINISHED + delivered), ("finished", ""))
        # An app that quits takes queued messages and delivers none of them.
        self.assertEqual(self.verdict(FINISHED + delivered[:2]),
                         ("interrupted", "a message queued for it was never delivered"))
        self.assertEqual(self.verdict(FINISHED + [queue("remove"), queue("enqueue")]),
                         ("interrupted", "a message queued for it was never delivered"))
        earlier = [user("go"), queue("enqueue"), assistant("done"), queue("enqueue"),
                   queue("dequeue")]
        self.assertEqual(self.verdict(earlier),
                         ("interrupted", "a message queued for it was never delivered"))
        self.assertEqual(self.verdict([user("go"), queue("enqueue"), assistant("done")]),
                         ("finished", ""))
        repeat = notice("a1")["message"]["content"]
        answered = [hand_back("a1", 10), assistant("seen", minutes_ago=9)] + FINISHED
        self.assertEqual(self.verdict(answered + [queue("enqueue", content=repeat)]),
                         ("finished", ""))
        self.assertEqual(self.verdict(answered + [
            queue("enqueue", content="do X"), queue("enqueue", content=repeat),
            queue("remove", content=repeat)]),
            ("interrupted", "a message queued for it was never delivered"))
        self.assertEqual(self.verdict(FINISHED + [queue("enqueue", content="do X"),
                                                  queue("remove", content="something else")]),
                         ("interrupted", "a message queued for it was never delivered"))
        self.assertEqual(self.verdict(FINISHED + [queue("enqueue", content="do X"),
                                                  queue("remove", content="do X")]),
                         ("finished", ""))

    def test_background_tasks(self):
        killed = ("interrupted", agent_sessions.KILLED)
        recent = [user("go", 70), launched("b1", 60), assistant("waiting", minutes_ago=59)]
        self.assertEqual(self.verdict(recent), killed)
        self.assertEqual(self.verdict(recent, done=True), ("finished", ""))
        self.assertEqual(self.verdict(recent + [notice("b1"), assistant("ok", minutes_ago=1)]),
                         ("finished", ""))
        stop = {"type": "tool_use", "id": "s", "name": "TaskStop", "input": {"task_id": "b1"}}
        stopped = recent[:-1] + [{**assistant("stopping"), "message": {
            "role": "assistant", "stop_reason": "end_turn", "content": [stop]}}]
        self.assertEqual(self.verdict(stopped), ("finished", ""))
        old = [user("go", 800), launched("b1", 790), assistant("waiting", minutes_ago=789)]
        self.assertEqual(self.verdict(old), killed)
        self.assertEqual(self.verdict(recent, NOW - datetime.timedelta(minutes=30)), killed)
        self.assertEqual(self.verdict(recent, NOW - datetime.timedelta(minutes=90)),
                         ("finished", ""))
        # Output that quotes a launch, such as a listing of a transcript, starts
        # no task.
        quoted = user([{"type": "tool_result", "tool_use_id": "t", "content":
                        "Monitor started (task b9, persistent)"}], 60)
        self.assertEqual(self.verdict([user("go", 70), quoted, assistant("ok", minutes_ago=59)]),
                         ("finished", ""))

    def test_reports_read_with_task_output(self):
        read = user([{"type": "tool_result", "tool_use_id": "t", "content":
                      "<retrieval_status>success</retrieval_status>\n<task_id>b1</task_id>\n"
                      "<status>completed</status>"}], 30)
        records = [user("go", 70), launched("b1", 60), read, assistant("read it", minutes_ago=29)]
        self.assertEqual(self.verdict(records), ("finished", ""))
        restart = notice("b1", 1, "stopped")
        self.assertEqual(self.verdict(records + [restart]), ("finished", ""))

    def test_monitors(self):
        started = launched("m1", 60, "taskId")
        watching = [user("go", 70), started, monitor_event("m1", 30),
                    assistant("still watching", minutes_ago=29)]
        self.assertEqual(self.verdict(watching), ("interrupted", agent_sessions.KILLED))
        self.assertEqual(self.verdict(watching + [notice("m1", 1, "stopped")]),
                         ("interrupted", agent_sessions.KILLED))
        self.assertEqual(self.verdict(watching + [notice("m1", 1, "stopped")], done=True),
                         ("finished", ""))
        for ending in ("[Monitor expired after 30m with 1 event delivered. Re-arm it.]",
                       "[Monitor timed out — re-arm if needed.]"):
            expired = user("<task-notification>\n<task-id>m1</task-id>\n<event>%s</event>\n"
                           "</task-notification>" % ending, 10)
            self.assertEqual(self.verdict(watching + [expired, assistant("ok", minutes_ago=9)]),
                             ("finished", ""), ending)

    def test_subagents_that_finished_at_once(self):
        done_at_once = user([{"type": "tool_result", "tool_use_id": "t", "content": "done"}], 60,
                            toolUseResult={"agentId": "a2", "status": "completed"})
        self.assertEqual(self.verdict([user("go", 70), done_at_once,
                                       assistant("ok", minutes_ago=59)]), ("finished", ""))

    def test_subagents(self):
        waiting = [user("go", 70), subagent("a1", 60), assistant("waiting", minutes_ago=59)]
        self.assertEqual(self.verdict(waiting)[0], "interrupted")
        reply = user('<agent-message from="a1">\ndone\n</agent-message>', 3)
        # A subagent's message to the session does not mean it has finished.
        self.assertEqual(self.verdict(waiting + [reply, assistant("thanks", minutes_ago=2)]),
                         ("interrupted", agent_sessions.KILLED))
        self.assertEqual(self.verdict(waiting + [reply, assistant("thanks", minutes_ago=2),
                                                 notice("a1", 1)]), ("finished", ""))

    def test_messages_absorbed_in_the_middle_of_a_turn(self):
        start = launched("b1", 60)
        records = [user("go", 70), start, absorbed(hand_back("b1"), 30),
                   absorbed(notice("b1"), 30), assistant("done", minutes_ago=29)]
        self.assertEqual(self.verdict(records), ("finished", ""))
        self.assertEqual(self.verdict(records + [notice("b1")]), ("finished", ""))
        queued = queue("enqueue", 1, notice("b1")["message"]["content"])
        self.assertEqual(self.verdict(records + [queued]), ("finished", ""))
        with_image = user([{"type": "image"}, {"type": "text", "text": hand_back("b1")[
            "message"]["content"]}], 30)
        image_only = records[:2] + [absorbed(with_image, 30), records[4], notice("b1", 1)]
        self.assertEqual(self.verdict(image_only), ("finished", ""))
        self.assertEqual(self.verdict(records[:2] + records[4:])[0], "interrupted")

    def test_one_notice_for_several_tasks(self):
        both = user("<task-notification>\n<task-id>b1</task-id>\n<task-id>b2</task-id>\n"
                    "<status>stopped</status>\n</task-notification>", 10)
        records = [user("go", 70), launched("b1", 60), launched("b2", 59), both,
                   assistant("restarting both", minutes_ago=9)]
        self.assertEqual(self.verdict(records), ("finished", ""))
        started = launched("m1", 58, "taskId")
        mixed = user(message_of(notice("b1", 10)) + "\n" + message_of(monitor_event("m1", 10)),
                     10)
        self.assertEqual(self.verdict([user("go", 70), launched("b1", 60), started, mixed,
                                       assistant("noted", minutes_ago=9)]),
                         ("interrupted", agent_sessions.KILLED))

    def test_local_commands(self):
        model = [user("<command-name>/model</command-name>", 2),
                 user("<local-command-stdout>Set model</local-command-stdout>", 2)]
        self.assertEqual(self.verdict(FINISHED + model), ("finished", ""))
        self.assertEqual(self.verdict(FINISHED + [user("<command-name>/ship</command-name>")]),
                         ("interrupted", "it never replied to its last message"))

    def test_messages_that_expect_no_reply(self):
        for text in ("<bash-input>ls</bash-input>", "<bash-stdout>a</bash-stdout>",
                     "<local-command-stdout>Set model</local-command-stdout>",
                     "<system-reminder>\nThe session's working directory has changed to "
                     "/x.\n</system-reminder>",
                     "<system-reminder>\n<tools-used-before-summary>SubagentHandback"
                     "</tools-used-before-summary>\n</system-reminder>\n",
                     "<system-reminder>\nThe session's working directory has changed to /x."
                     "\n</system-reminder>\nCodebase and user instructions are shown below."):
            self.assertEqual(self.verdict(FINISHED + [user(text)]), ("finished", ""), text)
        for text in ("<system-reminder>x</system-reminder>\nAnd now, a question?",
                     "<system-reminder>a</system-reminder>\nPlease fix X\n"
                     "<system-reminder>b</system-reminder>",
                     "Stop hook feedback:\nUpdate your session title"):
            self.assertEqual(self.verdict(FINISHED + [user(text)])[0], "interrupted", text)

    def test_nothing_to_go_on(self):
        self.assertEqual(self.verdict([]), ("unknown", "its transcript ends with no messages"))
        self.assertEqual(self.verdict([user("<bash-input>ls</bash-input>")]),
                         ("unknown", "its transcript ends with no messages"))


class Wake(unittest.TestCase):
    DEFAULT = {
        ("wake", IDS["limit"], "an API error: You've hit your limit"),
        ("unknown", IDS["no-transcript"], "it has no transcript"),
        ("unknown", IDS["empty"], "its transcript has no messages"),
        ("reorient", IDS["stopped-long-ago"], ""),
        ("wake", IDS["unanswered"], "it never replied to its last message"),
        ("wake", IDS["watching-killed"], agent_sessions.KILLED),
        ("wake", IDS["old-launch"], agent_sessions.KILLED),
        ("wake", IDS["old-subagent"], agent_sessions.KILLED),
        ("reorient", IDS["unguarded"], ""),
        ("unreachable", IDS["moved"],
         "its folder %s no longer exists" % os.path.join(HOME, "dev", "gone")),
        ("reorient", "1a2b3c4d-codex", ""),
        ("wake", "codex-quit-a", "Codex quit during its turn"),
        ("wake", "codex-quit-b", "Codex quit during its turn"),
    }
    CODEX = {("reorient", "1a2b3c4d-codex", ""),
             ("wake", "codex-quit-a", "Codex quit during its turn"),
             ("wake", "codex-quit-b", "Codex quit during its turn")}

    def rows(self, *argv):
        rows, code = run("wake", *argv)
        self.assertEqual(code, 0)
        return {(row["action"], row["id"], row["why"]) for row in rows}

    def test_sessions_to_wake_and_reorient(self):
        self.assertEqual(self.rows(), self.DEFAULT)
        self.assertIn('reorient    "contraptions: ✅ Finished tool" (claude-desktop %s) in auto '
                      'mode\n' % IDS["unguarded"], text("wake"))
        self.assertIn('reorient    "🐤 Unrelated thread" (codex 1a2b3c4d-codex)\n', text("wake"))

    def test_harness(self):
        self.assertEqual(self.rows("--harness", "codex"), self.CODEX)
        self.assertEqual(self.rows("--harness", "claude"), self.DEFAULT - self.CODEX)

    def test_idle_time(self):
        self.assertEqual(self.rows("--harness", "codex", "--idle", "0.5"),
                         self.CODEX | {("reorient", "codex-open", "")})
        self.assertEqual(self.rows("--idle", "14"),
                         {row for row in self.DEFAULT if row[0] != "reorient"})

    def test_states(self):
        paused = {("reorient", IDS["dormant"], ""), ("reorient", "codex-paused", "")}
        self.assertEqual(self.rows("--skip-state"), self.DEFAULT | paused)
        self.assertEqual(self.rows("--state", "⏸️", "--skip-state"), paused)
        self.assertEqual(self.rows("--state", "⏸️"), paused)
        self.assertEqual(self.rows("--state", "⏸️", "✅"),
                         paused | {("reorient", IDS["unguarded"], "")})
        self.assertEqual(self.rows("--skip-state", "🧱"),
                         {row for row in self.DEFAULT | paused
                          if row[1] in ("1a2b3c4d-codex", IDS["unguarded"],
                                        IDS["watching-killed"])} | paused)
        self.assertEqual(self.rows("--skip-state", "🧱", "--skip-state", "⏸️"),
                         self.rows("--skip-state", "🧱", "⏸️"))
        self.assertEqual(self.rows("--state", "🐤", "--state", "✅"),
                         {("reorient", "1a2b3c4d-codex", ""), ("reorient", IDS["unguarded"], "")})

    def test_codex_turns(self):
        def verdict(ending, running, minutes=10):
            path = rollout("probe", ending, minutes / 60)
            session = agent_sessions.Session("codex", "probe", "🧱 Probe", HOME,
                                             thread={"rollout_path": path})
            return agent_sessions.codex_turn(session, lambda: running)
        long_ago, just_now = NOW - datetime.timedelta(days=1), NOW
        self.assertEqual(verdict("task_complete", None), ("finished", ""))
        self.assertEqual(verdict("turn_aborted", None), ("stopped", ""))
        unfinished = ("interrupted", "its turn never ended")
        self.assertEqual(verdict("task_started", None), unfinished)
        self.assertEqual(verdict("task_started", just_now), unfinished)
        self.assertEqual(verdict("task_started", long_ago), ("working", ""))
        session = agent_sessions.Session("codex", "probe", "🧱 Probe", HOME, thread={})
        self.assertEqual(agent_sessions.codex_turn(session), ("unknown", "it has no transcript"))
        oldest = agent_sessions.codex_started()
        self.assertIsNotNone(oldest)
        self.assertLessEqual(oldest, datetime.datetime.now(datetime.timezone.utc))

    def test_nothing_to_do(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            agent_sessions.command_wake(argparse.Namespace(
                json=False, harness=None, skip_state=None, state=None, idle=12), [])
        self.assertEqual(out.getvalue(), "no session needs waking or reorienting\n")


class Search(unittest.TestCase):
    def test_messages_only(self):
        rows, code = run("search", "zebra")
        self.assertEqual(code, 0)
        # Codex's agent messages, and archived sessions, are searched; hook
        # feedback, notifications, reminders and summaries are not.
        self.assertEqual([(row["harness"], row["id"], row["messages"]) for row in rows],
                         [("claude-desktop", IDS["zebra"], 2), ("codex", "codex-open", 1),
                          ("codex", "1a2b3c4d-codex", 1), ("codex", "codex-archived", 1)])
        self.assertIn("found the Zebra in the stable", rows[0]["context"])
        self.assertEqual([row["id"] for row in run("search", "zebra", "--harness", "codex")[0]],
                         ["codex-open", "1a2b3c4d-codex", "codex-archived"])
        for harness in ("claude", "claude-desktop"):
            self.assertEqual([row["id"] for row in run("search", "zebra", "--harness", harness)[0]],
                             [IDS["zebra"]], harness)
        self.assertEqual(run("search", "zebra", "--harness", "claude-cli")[0], [])
        self.assertEqual(run("search", "subagent saw")[0], [])
        self.assertEqual(run("search", "zebra.txt")[0], [])

    def test_text_that_json_escapes(self):
        # Transcripts are JSON, which escapes quotation marks, backslashes and
        # control characters, and a message is only part of its line.
        for regex in ('said "stripes"', r'"stripes"\s+then\nleft', '^find the zebra',
                      'in the stable$', r'\bkeeper\b', r'said .stripes.\sthen', '[" ]stripes'):
            self.assertEqual([row["id"] for row in run("search", regex)[0]], [IDS["zebra"]],
                             regex)
        self.assertEqual(run("search", "^the stable")[0], [])

    def test_text_and_limit(self):
        out = text("search", "zebra", "--limit", "1")
        self.assertRegex(out, r'^\d{4}-\d\d-\d\dT\d\d:\d\dZ  dormant "🧱 Zebra hunt" \(claude-desktop '
                              r'%s\), 2 messages: .*Zebra in the stable\n'
                              r'and 3 more sessions; --limit 0 lists them all\n$' % IDS["zebra"])
        self.assertEqual(text("search", "no such words"), "no session's messages match\n")
        self.assertIn("is not a regular expression", invoke("search", "(")[1])
        self.assertEqual(invoke("search", "(")[2], 2)
        # Python reads lookahead; ripgrep does not.
        self.assertIn("ripgrep failed", run("search", "zebra(?= please)")[1])


class Graph(unittest.TestCase):
    def test_edges(self):
        edges = {(row["session"]["id"], row["base"]): row for row in run("graph")[0]}
        self.assertEqual(set(edges), {(IDS["va"], "VB"), (IDS["stacked-dangling"], "ℂFG"),
                                      (IDS["stacked-dangling"], "ℂEG"), (IDS["waiting"], "VC"),
                                      (IDS["stacked-two"], "EQ"), (IDS["stacked-two"], "V5")})
        self.assertEqual(edges[(IDS["stacked-two"], "V5")]["dormantClaims"], [ref(IDS["dormant"])])
        self.assertEqual(edges[(IDS["va"], "VB")]["heldBy"], [ref(IDS["vb"])])
        self.assertEqual(edges[(IDS["va"], "VB")]["session"], ref(IDS["va"]))
        self.assertEqual(edges[(IDS["stacked-dangling"], "ℂFG")]["heldBy"], [])
        self.assertFalse(edges[(IDS["stacked-dangling"], "ℂFG")]["exists"])

    def test_text_and_mermaid(self):
        lines = text("graph").splitlines()
        self.assertIn("  on ℂFG: no session claims it; it does not exist", lines)
        mermaid = text("graph", "--mermaid")
        self.assertTrue(mermaid.startswith("graph LR\n"))
        self.assertIn("-->|VB|", mermaid)
        self.assertIn('["ℂFG (no holder)"]', mermaid)
        self.assertIn('["VA, V5: ⏸️ Paused work (no running process)"]', mermaid)
        start = lines.index(agent_sessions.Session(
            "claude", IDS["stacked-two"], "VH: 📚 (EQ, V5) Waits on EQ", "").label())
        self.assertEqual([line.split(":")[0] for line in lines[start + 1:start + 3]],
                         ["  on EQ", "  on V5"])
        _, err, code = invoke("graph", "--mermaid", "--json")
        self.assertEqual(code, 2)
        self.assertIn("--mermaid and --json cannot be used together", err)


if __name__ == "__main__":
    unittest.main(verbosity=2)
