#!/usr/bin/env python3
"""Cases for spawn-task-gate.py, the PreToolUse gate on spawning sessions.

Run it with no arguments. It drives the gate the way the harness does, by
handing it a hook payload on standard input and reading the decision it
writes on standard output, and it reports one line per case. The exit
status is 0 when every case decided the way it should and 1 otherwise.

The cases cover both directions: first lines the gate is to allow, and
first lines it is to deny. The allowed ones include spellings that differ
from the documented form only in punctuation or letter case, since a
prompt that names a worktree unambiguously is not turned away over
either. The denied ones check that a denial names what it objected to.

Live conditions decide what the cases can assume. The gate allows a
worktree only when no session works in it and it is pristine, so this file
finds such worktrees rather than naming them. The cases that need an
existing worktree use a labs worktree when one is free, and otherwise a
free existing worktree of another kind. The cases for a worktree held
through a session's title use the live sessions whose titles name one.
When live conditions rule a case out, the output says so on a "skip" line.
The case for a new session pointed at the spawning session's own worktree
passes that same worktree as the working directory, or the ID of the session
that holds it.

The cases also check how the gate reads the list of worktrees that opens a
session title, directly, for titles that name worktrees and titles that
only look as if they might.

No live session is ever waiting for the brief of an offer that this file
made, so the cases for briefs hand the gate made-up live sessions and app
records directly, in this process.

A case that gives no title gets one that fits the worktree its prompt
names, so that it checks the prompt. The cases for the title give their
own. A case can also give further arguments of the call, such as an
initiation or a proposal ID.
"""

import contextlib
import glob
import importlib.util
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "spawn-task-gate.py")
SESSION_ID = "spawn-task-gate-cases"

_spec = importlib.util.spec_from_file_location("gate", HOOK)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


def fitting_title(prompt):
    """A title that opens with the identifier of the worktree a prompt
    names, as the gate reads the prompt, or one with no identifier when it
    names none."""
    kind, name, _ = gate.resolve(gate.opening(prompt))
    if kind in (None, "path"):
        return "⚙️ Do the thing"
    return "%s: ⚙️ Do the thing" % gate.identifier(kind, name)


def decide(prompt, cwd, session_id=SESSION_ID, title=None, further=None):
    """The gate's output on one prompt, as parsed JSON, or None when it
    allowed the call, or a string when it failed."""
    if title is None:
        title = fitting_title(prompt)
    tool_input = {"prompt": prompt, "title": title}
    tool_input.update(further or {})
    payload = {"tool_input": {key: value for key, value in tool_input.items()
                              if value is not None},
               "cwd": cwd, "session_id": session_id}
    finished = subprocess.run([sys.executable, HOOK], input=json.dumps(payload),
                              capture_output=True, text=True)
    if finished.returncode != 0:
        return "ERROR: " + finished.stderr.strip()
    body = finished.stdout.strip()
    return json.loads(body) if body else None


def run(prompt, cwd, session_id=SESSION_ID, title=None, further=None):
    """The gate's decision on one prompt, as (decision, what it said)."""
    return interpret(decide(prompt, cwd, session_id, title, further))


def interpret(data):
    """A decision the gate wrote, as (decision, what it said)."""
    if isinstance(data, str):
        return "ERROR", data
    if data is None:
        return "ALLOW", ""
    hook = data.get("hookSpecificOutput")
    if hook and hook.get("permissionDecision") == "deny":
        reason = hook["permissionDecisionReason"]
        # A denial carries guidance and a reference to the session-spawning
        # instructions after the part saying what went wrong. The cases read
        # the latter.
        return "DENY", reason.split("\nThe session prompt must open")[0].strip()
    if "systemMessage" in data:
        return "WAIVE", data["systemMessage"]
    return "OTHER", json.dumps(data)


def refers_without_quoting(prompt):
    """Whether a denial of this prompt names the instruction file without
    quoting any line of it."""
    reason = decide(prompt, gate.COMMONFABRIC)["hookSpecificOutput"][
        "permissionDecisionReason"]
    with open(gate.INSTRUCTIONS, encoding="utf-8") as handle:
        lines = {line.strip() for line in handle if len(line.strip()) > 40}
    return (gate.INSTRUCTIONS in reason
            and not any(line in reason for line in lines))


def survey():
    """The live sessions, as the gate reads them."""
    return gate.live_sessions()


def held(sessions, kind, name):
    """Whether a live session works in a worktree, by its title or its
    working directory."""
    directory = gate.worktree_path(kind, name)
    return any(gate.holds(session, kind, name, directory)
               for session in sessions)


def free(sessions, kind, names, exists):
    """The first of `names` that no session holds, whose directory exists
    or does not as `exists` says, and which has no uncommitted changes.

    Which worktrees are free is a live condition, so the cases find one
    rather than naming one. This decides freedom without asking the gate,
    so that a case built on the answer checks the gate rather than
    repeating it.
    """
    for name in names:
        directory = gate.worktree_path(kind, name)
        if (os.path.isdir(directory) == exists and not held(sessions, kind, name)
                and not (exists and gate.worktree_is_dirty(directory))):
            return name
    return None


def held_by_title(sessions, kind):
    """(session ID, name) for a live session whose title names a worktree
    of this kind, outside the range reserved for Codex, that no session
    was started in, or None."""
    for session in sessions:
        for found_kind, name in sorted(gate.title_worktrees(session.title)):
            directory = gate.worktree_path(kind, name)
            if (found_kind == kind and not name[0].isdigit()
                    and not any(other.cwd and gate.contains(directory, other.cwd)
                                for other in sessions)):
                return session.id, name
    return None


OFFER_TITLE = "𝛌ZQ: 🍄 Do the thing"
PARENT = gate.Session("parent", "/", "⚙️ Make offers", "Claude session",
                      "local_parent")
WAITING = gate.Session("child", "/", OFFER_TITLE, "Claude session",
                       "local_child")
RECORDS = {
    "local_child": {"spawnedFrom": {"taskId": "task_1", "title": OFFER_TITLE,
                                    "sessionId": "local_parent"}},
    "local_untitled": {"spawnedFrom": {"taskId": "task_1",
                                       "sessionId": "local_parent"}},
    "local_odd": {"spawnedFrom": ["task_1"]},
    "local_orphan": {"spawnedFrom": {"taskId": "task_1",
                                     "title": OFFER_TITLE}},
    "local_plain": {"spawnedFrom": {"taskId": "task_1", "title": "🍄 Do it",
                                    "sessionId": "local_parent"}},
}

# Sessions, the session that calls, and the proposal ID it gives, and
# whether the gate is to find the session waiting for that brief.
AWAITING = [
    ("waiting for its brief", [WAITING], PARENT, "task_1", True),
    ("already briefed", [WAITING._replace(title="𝛌ZQ: ⚙️ Do the thing")],
     PARENT, "task_1", False),
    ("another session's offer", [WAITING],
     PARENT._replace(host="local_other"), "task_1", False),
    ("another offer", [WAITING], PARENT, "task_2", False),
    ("caller unknown to the app", [WAITING._replace(host="local_orphan")],
     PARENT._replace(host=None), "task_1", False),
    ("caller not live", [WAITING], None, "task_1", False),
    ("offer without a title", [WAITING._replace(host="local_untitled",
                                                title="")],
     PARENT, "task_1", False),
    ("record of another shape", [WAITING._replace(host="local_odd")], PARENT,
     "task_1", False),
    ("session unknown to the app", [WAITING._replace(host=None)], PARENT,
     "task_1", False),
]


# Briefs for an offer, as the label, the live sessions, the prompt, the
# decision, and a phrase the decision must carry. Each brief is sent by
# PARENT for the offer "task_1".
BRIEFS = [
    ("for its offer's session", [PARENT, WAITING], "Use loom ZQ", "ALLOW", ""),
    ("naming another worktree", [PARENT, WAITING], "Use loom ZR", "DENY",
     "which does not name it"),
    ("after the session was briefed",
     [PARENT, WAITING._replace(title="𝛌ZQ: ⚙️ Do the thing")], "Use loom ZQ",
     "DENY", "in use by the Claude session"),
    ("for another session's offer",
     [PARENT._replace(host="local_other"), WAITING], "Use loom ZQ", "DENY",
     "in use by the Claude session"),
    ("for an offer naming no worktree",
     [PARENT, WAITING._replace(host="local_plain", title="🍄 Do it")],
     "Use loom ZQ", "ALLOW", ""),
]


def brief(sessions, prompt):
    """The gate's decision on a brief that PARENT sends for the offer
    "task_1", made in this process with the given live sessions and the
    records in RECORDS, as (decision, what it said)."""
    payload = {"tool_input": {"proposal_id": "task_1",
                              "prompt": prompt + "\n\nDo it."},
               "cwd": "/", "session_id": PARENT.id}
    written = io.StringIO()
    with contextlib.redirect_stdout(written):
        try:
            gate.check(payload, lambda: sessions,
                       lambda session: RECORDS.get(session.host, {}))
        except SystemExit:
            pass
    body = written.getvalue().strip()
    return interpret(json.loads(body) if body else None)


def codex_threads_read():
    """Whether the gate reads, from the newest Codex state database, the
    threads that have a title, have not been archived, and are not a
    subagent's, and no others."""
    threads = [
        ("kept", "exec", "𝛌ZQ: 🧱 Work", 0),
        ("from the app", "vscode", "ωZQ: 🧱 Work", 0),
        ("subagent", '{"subagent":{"other":"guardian"}}', "Guardian review", 0),
        ("archived", "exec", "𝛌ZR: 🧱 Work", 1),
        ("untitled", "exec", "", 0),
    ]
    with tempfile.TemporaryDirectory() as directory:
        for number, rows in ((4, [("old", "exec", "Old", 0)]), (10, threads)):
            with contextlib.closing(sqlite3.connect(os.path.join(
                    directory, "state_%d.sqlite" % number))) as database:
                database.execute("CREATE TABLE threads (id TEXT, cwd TEXT, "
                                 "name TEXT, archived INTEGER, source TEXT)")
                database.executemany(
                    "INSERT INTO threads VALUES (?, '/', ?, ?, ?)",
                    [(id, name, archived, source)
                     for id, source, name, archived in rows])
                database.commit()
        found = gate.codex_sessions(os.path.join(directory, "state_*.sqlite"))
    return sorted(session.id for session in found) == ["from the app", "kept"]


def app_records_read():
    """Whether the gate reads an app record that is well formed, and reads
    a missing, malformed or non-object record as no record."""
    with tempfile.TemporaryDirectory() as directory:
        os.makedirs(os.path.join(directory, "a", "b"))
        for host, text in (("local_good", '{"spawnedFrom": {}}'),
                           ("local_bad", '{"spawnedFrom": '),
                           ("local_list", "[]")):
            with open(os.path.join(directory, "a", "b", host + ".json"),
                      "w", encoding="utf-8") as handle:
                handle.write(text)
        pattern = os.path.join(directory, "*", "*")
        read = {host: gate.app_record(WAITING._replace(host=host), pattern)
                for host in ("local_good", "local_bad", "local_list",
                             "local_missing", None)}
    return read == {"local_good": {"spawnedFrom": {}}, "local_bad": {},
                    "local_list": {}, "local_missing": {}, None: {}}


def names_in(kind):
    """The codes of the existing worktrees of a kind, leaving out those
    reserved for Codex."""
    family = gate.families()[kind]
    for directory in sorted(glob.glob(os.path.join(family.parent, "*"))):
        name = os.path.basename(directory)
        if (os.path.isdir(directory)
                and re.fullmatch(family.code, name, re.IGNORECASE)
                and not name[0].isdigit()):
            yield gate.canonical(kind, name)


def free_existing(sessions):
    """(kind, name) for a free worktree that exists, preferring labs, or
    None."""
    kinds = sorted((kind for kind, family in gate.families().items()
                    if family.code == gate.CODE),
                   key=lambda kind: kind != "labs")
    for kind in kinds:
        name = free(sessions, kind, names_in(kind), True)
        if name:
            return kind, name
    return None


# Titles, and the (kind, name) of each worktree the gate is to read from them.
TITLES = [
    ("B0: 🐤 Judge three publisher follow-ups", {("labs", "B0")}),
    ("ωU3, 𝛌3, INFRA2, deno1: 🧱 Work across seams",
     {("weaver", "U3"), ("loom", "3"), ("infra", "2"), ("deno", "1")}),
    ("𝛌C0, gvisor-T1, web-A1, cliffy2, settings: 🧱 Other repositories",
     {("loom", "C0"), ("gvisor", "T1"), ("web", "A1"), ("cliffy", "2"),
      ("settings", "settings")}),
    ("web-weaver-A1: 🧱 Full repository name", {("web", "A1")}),
    ("b0, ωu3: 🧱 Lowercase names", {("labs", "B0"), ("weaver", "U3")}),
    ("D4, #35657: 🐤 Pull request in the list", {("labs", "D4")}),
    ("CI: red main on B3", {("labs", "CI")}),
    ("Fix: bug", set()),
    ("🧱 Compare A, B0: which is better", set()),
    ("🧱 Fix: 🐛 the thing", set()),
    ("⏳ Waiting on the Workspace domain change", set()),
    ("", set()),
]


def cases(sessions):
    """Every case, as (label, prompt, working directory, decision), and
    optionally the session ID to use, a phrase the decision must carry, the
    title, and further arguments of the call, followed by a sentence for
    each case that live conditions ruled out."""
    here = gate.COMMONFABRIC
    skipped = []
    existing = free_existing(sessions)
    weaver = free(sessions, "weaver", [letter + digit for letter in "ZYXWV"
                                       for digit in "9876543210"], False)
    loom = free(sessions, "loom", [letter + digit for letter in "ZYXWV"
                                   for digit in "9876543210"], False)
    infra = free(sessions, "infra", [letter + digit for letter in "ZYXWV"
                                     for digit in "9876543210"], False)
    labs = free(sessions, "labs", [letter + digit for letter in "ZYXWV"
                                   for digit in "9876543210"], False)
    for kind, found in (("existing", existing), ("weaver", weaver),
                        ("loom", loom), ("infra", infra),
                        ("nonexistent labs", labs)):
        if found is None:
            raise SystemExit("No free %s worktree could be found for the "
                             "cases that need one. Free one and run this "
                             "again." % kind)
    kind, name = existing
    if kind != "labs":
        skipped.append("No labs worktree is free, so the cases that need an "
                       "existing worktree use %s instead."
                       % gate.label(kind, name))
    use = "Use %s" % gate.label(kind, name)
    path = gate.worktree_path(kind, name)
    listed = [
        ("plain", "%s\n\nDo the thing." % use, here, "ALLOW"),
        ("period", "%s.\n\nDo the thing." % use, here, "ALLOW"),
        ("comma", "%s,\n\nDo the thing." % use, here, "ALLOW"),
        ("colon", "%s:\n\nDo the thing." % use, here, "ALLOW"),
        ("sentence after", "%s. Do the thing." % use, here, "ALLOW"),
        ("sentences after", "  %s! Do it. Then stop.\n\nMore." % use, here,
         "ALLOW"),
        ("identifier, sentence after", "Use %s. Do it."
         % gate.identifier(kind, name), here, "ALLOW"),
        ("path, sentence after", "Use ~/dev. Do the thing.", here, "ALLOW"),
        ("period without space", "%s.Do the thing." % use, here, "DENY",
         SESSION_ID, "It opens with:\n\n  %s.Do the thing." % use),
        ("prose, then sentence", "%s for the gates. Do it." % use, here,
         "DENY", SESSION_ID, "further text"),
        ("Use, no form, sentence after", "Use frobnicate. Do the thing.",
         here, "DENY", SESSION_ID, "It opens with:\n\n  Use frobnicate."),
        ("lowercase use", "u%s\n\nDo it." % use[1:], here, "ALLOW"),
        ("lowercase name", "%s.\n\nDo it." % use.lower(), here, "ALLOW"),
        ("leading blank lines", "\n\n%s.\n\nDo it." % use, here, "ALLOW"),
        ("identifier", "Use %s.\n\nDo it." % gate.identifier(kind, name), here,
         "ALLOW"),
        ("name and hyphen", "Use %s-%s\n\nDo it." % (kind, name), here,
         "ALLOW"),
        ("full name and hyphen", "Use commonfabric-weaver-%s\n\nDo it."
         % weaver, here, "ALLOW"),
        ("loom name and hyphen", "Use loom-%s\n\nDo it." % loom, here,
         "ALLOW"),
        ("labs name and hyphen", "Use labs-%s\n\nDo it." % labs, here,
         "ALLOW"),
        ("identifier without Use", "ω%s\n\nDo it." % weaver, here, "DENY",
         SESSION_ID, "does not begin with the word"),
        ("weaver", "Use weaver %s\n\nDo the thing." % weaver, here, "ALLOW"),
        ("weaver, lowercase name",
         "Use weaver %s.\n\nDo it." % weaver.lower(), here, "ALLOW"),
        ("weaver, full name", "Use commonfabric-weaver %s\n\nDo it." % weaver,
         here, "ALLOW"),
        ("weaver identifier", "Use ω%s\n\nDo it." % weaver, here, "ALLOW"),
        ("infra identifier, period", "Use INFRA%s.\n\nDo it." % infra, here,
         "ALLOW"),
        ("infra", "Use infra %s\n\nDo it." % infra, here, "ALLOW"),
        ("loom, period", "Use loom %s.\n\nDo the thing." % loom, here, "ALLOW"),
        ("loom short name", "Use cfs %s\n\nDo the thing." % loom, here,
         "ALLOW"),
        ("loom identifier", "Use 𝛌%s\n\nDo the thing." % loom, here, "ALLOW"),
        ("path", "Use ~/dev\n\nDo the thing.", here, "ALLOW"),
        ("path, period", "Use ~/dev.\n\nDo the thing.", here,
         "ALLOW"),
        ("path to worktree, period", "Use %s.\n\nDo it." % path, here,
         "ALLOW"),
        ("path inside worktree", "Use %s/%s\n\nDo it."
         % (path, os.listdir(path)[0]), here, "ALLOW"),
        ("path, lowercase use", "use %s\n\nDo it." % path, here, "ALLOW"),
        ("waiver", "Do the thing.\n\nWorktree checks waived: a Codex repo.",
         here, "WAIVE"),

        ("no Use line", "Deflake the gates.\n", here, "DENY"),
        ("empty prompt", "", here, "DENY"),
        ("Use, no form", "Use frobnicate\n\nDo the thing.", here, "DENY"),
        ("labs name too long", "Use labs FOO\n\nDo the thing.", here, "DENY",
         SESSION_ID, "one or two letters or digits"),
        ("worktree plus prose", "%s for the gates\n\nDo it." % use,
         here, "DENY", SESSION_ID, "further text"),
        ("nonexistent labs", "Use labs %s\n\nDo the thing." % labs, here,
         "ALLOW"),
        ("nonexistent labs by id", "Use %s\n\nDo the thing." % labs, here,
         "ALLOW"),
        ("nonexistent gvisor", "Use gvisor-ZQ\n\nDo the thing.", here,
         "ALLOW"),
        ("nonexistent web", "Use web-ZQ\n\nDo the thing.", here, "ALLOW"),
        ("own nonexistent web", "Use web ZQ\n\nDo it.",
         os.path.join(here, "web-weaver", "ZQ"), "DENY",
         SESSION_ID, "this session is working in"),
        ("own web by full name", "Use web-weaver ZQ\n\nDo it.",
         os.path.join(here, "web-weaver", "ZQ"), "DENY",
         SESSION_ID, "this session is working in"),
        ("unknown repository", "Use commonfabric-web ZQ\n\nDo it.", here,
         "DENY", SESSION_ID, "does not open by naming a worktree"),
        ("path to nonexistent labs", "Use %s\n\nDo it."
         % gate.worktree_path("labs", labs), here, "ALLOW"),
        ("own nonexistent labs", "Use labs %s\n\nDo it." % labs,
         gate.worktree_path("labs", labs), "DENY",
         SESSION_ID, "this session is working in"),
        ("Codex range", "Use labs 42\n\nDo the thing.", here, "DENY",
         SESSION_ID, "reserved for Codex"),
        ("Codex, one digit", "Use labs 0\n\nDo the thing.", here, "DENY",
         SESSION_ID, "reserved for Codex"),
        ("own worktree", "%s\n\nDo the thing." % use, path, "DENY",
         SESSION_ID, "this session is working in"),
        ("own worktree by path", "Use %s\n\nDo it." % path, path, "DENY",
         SESSION_ID, "this session is working in"),
        ("own worktree by uppercase path", "Use %s\n\nDo it." % path.upper(),
         path, "DENY", SESSION_ID, "this session is working in"),
        ("path to Codex labs",
         "Use %s\n\nDo it." % gate.worktree_path("labs", "42"), here, "DENY",
         SESSION_ID, "reserved for Codex"),
        ("path to Codex weaver",
         "Use ~/dev/commonfabric/commonfabric-weaver/1\n\nDo it.", here, "DENY",
         SESSION_ID, "reserved for Codex"),
        ("weaver name too long", "Use weaver FOO\n\nDo the thing.",
         here, "DENY"),
        ("weaver Codex range", "Use weaver 42\n\nDo the thing.", here, "DENY",
         SESSION_ID, "reserved for Codex"),
        ("weaver Codex, one digit", "Use ω4\n\nDo the thing.",
         here, "DENY", SESSION_ID, "reserved for Codex"),
        ("loom Codex range", "Use 𝛌3\n\nDo the thing.", here, "DENY",
         SESSION_ID, "reserved for Codex"),
        ("deno Codex range", "Use deno1\n\nDo the thing.", here, "DENY",
         SESSION_ID, "reserved for Codex"),
        ("other repository Codex range", "Use gvisor 12\n\nDo it.", here,
         "DENY", SESSION_ID, "reserved for Codex"),
        ("path to Codex deno", "Use ~/dev/denoland/1/cli\n\nDo it.", here,
         "DENY", SESSION_ID, "reserved for Codex"),

        ("own weaver worktree", "Use weaver %s\n\nDo the thing." % weaver,
         gate.worktree_path("weaver", weaver), "DENY",
         SESSION_ID, "this session is working in"),
        ("loom name too long", "Use loom foo\n\nDo the thing.",
         here, "DENY"),
        ("own loom worktree", "Use loom %s\n\nDo the thing." % loom,
         gate.worktree_path("loom", loom), "DENY",
         SESSION_ID, "this session is working in"),
        ("infra plus prose", "Use INFRA%s for the gates\n\nDo it." % infra,
         here, "DENY"),
        ("waiver, no reason", "Do it.\n\nWorktree checks waived\n", here,
         "DENY"),
        ("nonexistent path", "Use ~/dev/nope-not-here\n\nDo it.", here, "DENY",
         SESSION_ID, "There is no directory"),

        ("title, list", "Use weaver %s\n\nDo it." % weaver, here, "ALLOW",
         SESSION_ID, "", "𝛌%s, ω%s: ⚙️ Do it" % (loom, weaver)),
        ("title, lowercase identifier", "Use weaver %s\n\nDo it." % weaver,
         here, "ALLOW", SESSION_ID, "", "ω%s: ⚙️ Do it" % weaver.lower()),
        ("title, loom identifier", "Use loom %s\n\nDo it." % loom, here,
         "ALLOW", SESSION_ID, "", "𝛌%s: ⚙️ Do it" % loom),
        ("title, pull request in list", "Use weaver %s\n\nDo it." % weaver,
         here, "ALLOW", SESSION_ID, "", "ω%s, #123: ⚙️ Do it" % weaver),
        ("title, list with prose", "Use weaver %s\n\nDo it." % weaver,
         here, "ALLOW", SESSION_ID, "", "ω%s, the gate: ⚙️ Do it" % weaver),
        ("title, bare code", "Use weaver %s\n\nDo it." % weaver, here, "DENY",
         SESSION_ID, "title must be a session title that opens with \"ω%s: \""
         % weaver, "%s: ⚙️ Do it" % weaver),
        ("title, list without it", "Use weaver %s\n\nDo it." % weaver, here,
         "DENY", SESSION_ID, "includes ω%s" % weaver,
         "𝛌%s, INFRA%s: ⚙️ Do it" % (loom, infra)),
        ("title, path inside worktree", "Use %s/%s\n\nDo it."
         % (path, os.listdir(path)[0]), here, "DENY", SESSION_ID,
         "opens with \"%s: \"" % gate.identifier(kind, name), "⚙️ Do it"),
        ("title, path with no identifier", "Use ~/dev\n\nDo it.",
         here, "ALLOW", SESSION_ID, "", "⚙️ Tidy the tools"),
        ("title, waiver", "Do it.\n\nWorktree checks waived: a Codex repo.",
         here, "WAIVE", SESSION_ID, "", ""),
        ("empty title", "Use weaver %s\n\nDo it." % weaver, here, "DENY",
         SESSION_ID, "Its title is:\n\n  (empty)", ""),
        ("title without identifier", "Use weaver %s\n\nDo it." % weaver,
         here, "DENY", SESSION_ID, "Its title is:\n\n  ⚙️ Fix the gate",
         "⚙️ Fix the gate"),
        ("title, another worktree", "Use weaver %s\n\nDo it." % weaver, here,
         "DENY", SESSION_ID, "title must be", "ωZZ: ⚙️ Do it"),
        ("title, no state", "Use weaver %s\n\nDo it." % weaver, here, "ALLOW",
         SESSION_ID, "", "ω%s: Fix the gate" % weaver),
        ("title, identifier only", "Use weaver %s\n\nDo it." % weaver, here,
         "DENY", SESSION_ID, "title must be", "ω%s:" % weaver),
        ("title, identifier without colon", "Use weaver %s\n\nDo it."
         % weaver, here, "DENY", SESSION_ID, "title must be",
         "ω%s ⚙️ Fix the gate" % weaver),

        ("offer", "", here, "ALLOW", SESSION_ID, "",
         "ω%s: ⚙️ Fix the gate" % weaver, {"initiation": "offer"}),
        ("offer naming no worktree", "", here, "ALLOW", SESSION_ID, "",
         "Fix the gate", {"initiation": "offer"}),
        ("offer, Codex range", "", here, "DENY", SESSION_ID,
         "reserved for Codex", "ω4: ⚙️ Fix the gate", {"initiation": "offer"}),
        ("offer, own worktree", "", path, "DENY", SESSION_ID,
         "this session is working in",
         "%s: ⚙️ Fix the gate" % gate.identifier(kind, name),
         {"initiation": "offer"}),
        ("offer, own worktree second", "", path, "DENY", SESSION_ID,
         "this session is working in", "ω%s, %s: ⚙️ Fix the gate"
         % (weaver, gate.identifier(kind, name)), {"initiation": "offer"}),
        ("offer with a prompt", "Deflake the gates.\n", here, "DENY",
         SESSION_ID, "does not open by naming a worktree", "Fix the gate",
         {"initiation": "offer"}),
        ("proposal started by ID", "", here, "ALLOW", SESSION_ID, "", "",
         {"proposal_id": "task_ab12cd34"}),
        ("brief for an offer", "Use weaver %s\n\nDo it." % weaver, here,
         "ALLOW", SESSION_ID, "", "", {"proposal_id": "task_ab12cd34"}),
        ("brief for an offer, no worktree", "Deflake the gates.\n", here,
         "DENY", SESSION_ID, "does not open by naming a worktree", "",
         {"proposal_id": "task_ab12cd34"}),
        ("brief for an offer, own worktree", "%s\n\nDo it." % use, path,
         "DENY", SESSION_ID, "this session is working in", "",
         {"proposal_id": "task_ab12cd34"}),
        ("proposal started by ID, blank prompt", "\n", here, "ALLOW",
         SESSION_ID, "", "", {"proposal_id": "task_ab12cd34"}),
        ("brief with another worktree's title", "Use weaver %s\n\nDo it."
         % weaver, here, "DENY", SESSION_ID, "title must be",
         "ωZZ: ⚙️ Do it", {"proposal_id": "task_ab12cd34"}),
        ("proposal, no prompt", "", here, "DENY", SESSION_ID,
         "the prompt is empty", "", {"initiation": "own_initiative"}),
    ]

    single = next((repository for repository in gate.SINGLE_COPIES
                   if free(sessions, repository, [repository], True)), None)
    if single:
        listed.append(("single copy", "Use %s\n\nDo it." % single, here,
                       "ALLOW"))
        listed.append(("single copy, title without name", "Use %s\n\nDo it."
                       % single, here, "DENY", SESSION_ID,
                       "opens with \"%s: \"" % single, "⚙️ Do it"))
        listed.append(("own single copy", "Use %s\n\nDo it." % single,
                       gate.worktree_path(single, single), "DENY",
                       SESSION_ID, "this session is working in"))
    else:
        skipped.append("No repository with a single copy is free, so none is "
                       "checked for being allowed.")

    dirty = next(((kind, name) for kind in gate.families()
                  for name in names_in(kind)
                  if gate.worktree_is_dirty(gate.worktree_path(kind, name))
                  and not held(sessions, kind, name)), None)
    if dirty:
        listed.append(("dirty worktree", "Use %s\n\nDo it." % gate.label(*dirty),
                       here, "DENY", SESSION_ID, "uncommitted changes"))
    else:
        skipped.append("No worktree has uncommitted changes without also "
                       "being held, so that denial is not checked.")

    for kind in ("labs", "weaver", "loom", "deno"):
        found = held_by_title(sessions, kind)
        if found is None:
            skipped.append("No live session's title names a %s worktree that "
                           "no session was started in, so holding a %s "
                           "worktree by title is not checked." % (kind, kind))
            continue
        holder, name = found
        prompt = "Use %s\n\nDo it." % gate.label(kind, name)
        listed.append(("%s held by a title" % kind, prompt, here, "DENY",
                       SESSION_ID, "in use by the"))
        listed.append(("own %s by title" % kind, prompt, here, "DENY", holder,
                       "this session is working in"))
        listed.append(("path held by a %s title" % kind, "Use %s\n\nDo it."
                       % gate.worktree_path(kind, name), here, "DENY",
                       SESSION_ID, "in use by the"))
    codex = next(((session.title, kind, name) for session in sessions
                  if session.description == "Codex thread"
                  for kind, name in sorted(gate.title_worktrees(session.title))
                  if not name[0].isdigit()),
                 None)
    if codex:
        title, kind, name = codex
        listed.append(("held by a Codex thread", "Use %s\n\nDo it."
                       % gate.label(kind, name), here, "DENY", SESSION_ID,
                       "in use by the Codex thread \"%s\"" % title))
    else:
        skipped.append("No Codex thread's title names a worktree outside "
                       "the Codex ranges, so holding one by a Codex thread "
                       "is not checked.")
    return listed, skipped


def main():
    wrong = 0
    for repository in sorted(gate.COMMONFABRIC_REPOSITORIES):
        good = os.path.isdir(os.path.join(gate.COMMONFABRIC, repository, "root"))
        wrong += 0 if good else 1
        print("%-4s table entry %s has a main worktree"
              % ("ok" if good else "FAIL", repository))
    for title, expected in TITLES:
        found = gate.title_worktrees(title)
        good = found == expected
        wrong += 0 if good else 1
        print("%-4s title %-38r -> %s" % ("ok" if good else "FAIL", title,
                                          sorted(found)))
    print()

    for label, sessions, caller, proposal, expected in AWAITING:
        found = gate.awaiting_brief(sessions, caller, proposal,
                                    lambda s: RECORDS.get(s.host, {}))
        good = (found is sessions[0]) == expected
        wrong += 0 if good else 1
        print("%-4s awaiting brief, %-26s -> %s"
              % ("ok" if good else "FAIL", label, found is not None))
    good = app_records_read()
    wrong += 0 if good else 1
    print("%-4s app records that cannot be read count as none"
          % ("ok" if good else "FAIL"))
    for label, sessions, prompt, expected, phrase in BRIEFS:
        decision, detail = brief(sessions, prompt)
        good = decision == expected and phrase in detail
        wrong += 0 if good else 1
        print("%-4s brief %-32s -> %-6s %s"
              % ("ok" if good else "FAIL", label, decision,
                 detail.replace("\n", " ")[:80]))
    good = codex_threads_read()
    wrong += 0 if good else 1
    print("%-4s Codex threads that hold worktrees leave out subagents' threads"
          % ("ok" if good else "FAIL"))
    print()

    for prompt in ("Use weaver 42\n", "Use labs 42\n", "Frobnicate\n"):
        good = refers_without_quoting(prompt)
        wrong += 0 if good else 1
        print("%-4s denial of %-28r refers to %s without quoting it"
              % ("ok" if good else "FAIL", prompt, gate.INSTRUCTIONS))
    print()

    listed, skipped = cases(survey())
    for label, prompt, cwd, expected, *extra in listed:
        session_id, phrase, title, further = (
            extra + [SESSION_ID, "", None, None][len(extra):])
        decision, detail = run(prompt, cwd, session_id, title, further)
        good = decision == expected and phrase in detail
        wrong += 0 if good else 1
        print("%-4s %-24s -> %-6s %s"
              % ("ok" if good else "FAIL", label, decision,
                 detail.replace("\n", " ")[:100]))
    for sentence in skipped:
        print("skip %s" % sentence)
    print("\n%d case(s) decided wrongly, %d skipped" % (wrong, len(skipped)))
    return 1 if wrong else 0


sys.exit(main())
