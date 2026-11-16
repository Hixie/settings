#!/usr/bin/env python3
"""PreToolUse gate for spawning sessions.

Reads the hook payload on stdin and writes a PreToolUse decision on stdout. A
start_session call is allowed when the session prompt opens by naming the
worktree the new session is to work in, that worktree passes the checks below,
and the new session's title is a session title whose list of worktrees includes
that worktree. Two calls carry no prompt. One is an offer, which asks the user
before any brief is written; it is allowed when every worktree its title names
passes the checks. The other starts a proposal by its ID alone, and is allowed,
because the prompt and title of a proposal were checked when it was proposed.
The call that sends the brief for an accepted offer names the offer by its ID
and carries no title. By then the app has opened the offer's session under the
offer's title. While that session waits for its brief, it does not count as
holding the worktree, and the brief must name a worktree that its title names,
when its title names any. Every other call is denied, and the denial names the
file that holds the session-spawning instructions.
"""

import functools
import glob
import json
import os
import re
import sqlite3
import subprocess
import sys
from collections import namedtuple
from contextlib import closing

HOME = os.path.expanduser("~")
DEV = os.path.join(HOME, "dev")
CLAUDE_DIR = os.path.join(HOME, ".claude")
COMMONFABRIC = os.path.join(DEV, "commonfabric")
CODEX_STATE = os.path.join(HOME, ".codex", "state_*.sqlite")
# The desktop app's record of each session, as local_<id>.json.
APP_SESSIONS = os.path.join(HOME, "Library", "Application Support", "Claude",
                            "claude-code-sessions", "*", "*")

# A session that can hold a worktree: its ID, working directory, title, a
# description of what kind of session it is, and, for a desktop app session,
# the app's ID for it.
Session = namedtuple("Session", "id cwd title description host")

# A worktree code: one or two letters or digits, read as a base 36 number.
CODE = r"[0-9A-Za-z]{1,2}"

# A family of worktrees: the directory whose entries are the worktrees; the
# words that name the family in a first line of the form "Use REPO XX"; the
# pattern that comes before the code in a worktree identifier, as in "ωU3",
# whose first alternative is how the gate writes it; and the pattern the code
# matches. A repository with a single copy has no
# words, and its name for its code with nothing before it, so its identifier
# is its name.
Family = namedtuple("Family", "parent names mark code")

# Common Fabric repositories whose worktrees have a name other than the
# repository's, or an identifier other than "REPO-XX": the repository, the
# name the gate gives its worktrees, the other names it goes by, and the
# pattern before the code in its identifiers.
COMMONFABRIC_REPOSITORIES = {
    "labs": ("labs", (), ""),
    "loom": ("loom", ("cfs",), "𝛌|λ"),
    "commonfabric-weaver": ("weaver", ("commonfabric-weaver",), "ω"),
    "infra": ("infra", (), "INFRA"),
    "web-weaver": ("web", ("web-weaver",), "web-"),
}

# Other repositories with worktrees: the name the gate gives their
# worktrees, which is also the mark before the code in their identifiers,
# and the directory under ~/dev that holds them.
OTHER_REPOSITORIES = {"deno": "denoland", "cliffy": "cliffy"}

# Repositories with a single copy, directly under ~/dev.
SINGLE_COPIES = ("contraptions", "settings", "usable-git")


@functools.cache
def families():
    """Every family of worktrees, by the name the gate gives it.

    Every directory under ~/dev/commonfabric that has a main worktree
    called "root" is a Common Fabric repository.
    """
    listed = []
    roots = glob.glob(os.path.join(COMMONFABRIC, "*", "root"))
    repositories = {os.path.basename(os.path.dirname(root)) for root in roots}
    for repository in sorted(repositories):
        kind, others, mark = COMMONFABRIC_REPOSITORIES.get(
            repository, (repository, (), re.escape(repository) + "-"))
        listed.append((kind, Family(os.path.join(COMMONFABRIC, repository),
                                    (kind,) + others, mark, CODE)))
    for kind, directory in OTHER_REPOSITORIES.items():
        listed.append((kind, Family(os.path.join(DEV, directory), (kind,),
                                    kind, CODE)))
    for repository in SINGLE_COPIES:
        listed.append((repository, Family(DEV, (), "", re.escape(repository))))
    found = dict(listed)
    if len(found) != len(listed):
        kinds = [kind for kind, _ in listed]
        raise ValueError("More than one repository gives its worktrees the "
                         "name %s." % ", ".join(sorted(
                             {kind for kind in kinds if kinds.count(kind) > 1})))
    return found


def identifier_pattern(family):
    """The pattern for a worktree identifier, with the code as its group.

    Besides the family's own mark, any name the family goes by followed by
    a hyphen comes before the code, as in "labs-G7" or "loom-3".
    """
    marks = [family.mark] + [re.escape(name) + "-" for name in family.names]
    return "(?:%s)(%s)" % ("|".join(marks), family.code)


# A title that opens with a list of worktrees, then a colon, then the rest of
# the title. Worktree identifiers are letters, digits, and hyphens, where
# letters include non-ASCII ones such as "ω" and "𝛌", so a list never contains
# an emoji.
TITLE_HEAD = re.compile(r"([\w\s,#-]*):\s*\S")

# The instruction file every denial refers to.
INSTRUCTIONS = os.path.join(CLAUDE_DIR, "starting-new-sessions.md")

# A session prompt carrying this line, with a reason, skips every check below.
_WAIVER_LEAD = r"^[ \t]*(?:[-*>][ \t]*)?Worktree checks waived"
WAIVER = re.compile(_WAIVER_LEAD + r":[ \t]*(\S.*?)\s*$", re.MULTILINE)
WAIVER_WITHOUT_REASON = re.compile(_WAIVER_LEAD + r"\b", re.MULTILINE)

# Punctuation a sentence may end with, which the forms below are written
# without and which is therefore removed before a first line is matched.
TRAILING_PUNCTUATION = re.compile(r"[.,;:!]+\s*$")

# The opening of a session prompt: its first non-blank line, cut short after
# the first sentence when the line goes on past it.
OPENING = re.compile(r"\s*(.*?(?:[.!](?=\s)|$))", re.MULTILINE)

FIRST_LINE_FORMS = """The session prompt must open with a line or sentence that names the worktree
the new session is to work in, and nothing else, in one of these forms:

  Use REPO XX    a worktree, by its repository's name or short name and its
                 worktree code of one or two letters or digits, e.g.
                 "Use labs G7", "Use weaver U3", "Use loom 3", "Use deno 2"
  Use XYZ        a worktree, by its worktree identifier, e.g. "Use G7",
                 "Use ωU3", "Use 𝛌3", "Use INFRA2", "Use deno2",
                 "Use gvisor-T1", "Use labs-G7", "Use settings"
  Use PATH       any other directory, as an absolute or ~-prefixed path

Choose the worktree by following the session-spawning instructions, then issue
the start_session call again with that opening in place. Work that does not
belong in any of these can waive these checks; the instructions say how."""


def opening(prompt):
    """The part of a session prompt that names a worktree, as in
    "Use labs G7." from "Use labs G7. Fix the gate." or from
    "Use labs G7.\\nFix the gate."."""
    return OPENING.match(prompt).group(1).strip()

REFERENCE = ("The session-spawning instructions are in %s. Read that file in "
             "full before trying again." % INSTRUCTIONS)


def deny(problem, guidance=FIRST_LINE_FORMS):
    reason = "\n\n".join(filter(None, (problem, guidance, REFERENCE)))
    json.dump({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }, sys.stdout)
    sys.exit(0)


def allow():
    sys.exit(0)


def waive(reason):
    json.dump({"systemMessage": "Session worktree checks waived: %s" % reason},
              sys.stdout)
    sys.exit(0)


def canonical(kind, name):
    """The one spelling of a worktree name that the gate compares."""
    return name.upper() if families()[kind].names else name.lower()


def worktree_path(kind, name):
    """The directory of a worktree, from its kind and name."""
    return os.path.join(families()[kind].parent, name)


def named(kind, name):
    """(kind, name, directory) for a worktree, from any spelling of its name."""
    name = canonical(kind, name)
    return kind, name, worktree_path(kind, name)


def from_path(spelled):
    """(kind, name, directory) for a directory named by its path.

    A path inside a worktree names that worktree, so that it gets the same
    checks as when it is named by its kind and name.
    """
    directory = os.path.abspath(os.path.expanduser(spelled))
    for kind, family in families().items():
        parent = family.parent
        if contains(parent, directory) and directory != parent:
            entry = os.path.relpath(directory.lower(),
                                    parent.lower()).split(os.sep)[0]
            if re.fullmatch(family.code, entry, re.IGNORECASE):
                return named(kind, entry)
    return "path", spelled, directory


def identifier(kind, name):
    """A worktree's identifier, as in "ωU3": the first alternative of its
    family's mark, followed by its code."""
    mark = families()[kind].mark.split("|")[0]
    return re.sub(r"\\(.)", r"\1", mark) + name


def label(kind, name):
    """A worktree as the session-spawning instructions write it, e.g.
    "labs G7"."""
    if kind == "path" or not families()[kind].names:
        return name
    return "%s %s" % (kind, name)


def resolve_one(first_line):
    """Map one spelling of a first line to (kind, name, directory)."""
    for kind, family in families().items():
        forms = [identifier_pattern(family)]
        if family.names:
            forms.append(r"(?:%s)\s+(%s)" % (
                "|".join(map(re.escape, family.names)), family.code))
        for form in forms:
            match = re.match(r"Use\s+%s\s*$" % form, first_line,
                             re.IGNORECASE)
            if match:
                return named(kind, match.group(1))
    match = re.match(r"(?i:Use)\s+(~/\S+|/\S+)\s*$", first_line)
    if match:
        return from_path(match.group(1))
    return None, None, None


def resolve(first_line):
    """Map the first line of a session prompt to (kind, name, directory).

    The forms are written without a sentence's closing punctuation, so a
    line that does not resolve with such punctuation is resolved again
    without it. A path swallows the punctuation rather than failing to
    match, so a path that does not exist gives way to whatever the line
    names without the punctuation.
    """
    exact = resolve_one(first_line)
    trimmed_line = TRAILING_PUNCTUATION.sub("", first_line)
    if trimmed_line == first_line:
        return exact
    trimmed = resolve_one(trimmed_line)
    if exact[0] is None or (exact[0] == "path" and not os.path.isdir(exact[2])
                            and trimmed[0] is not None):
        return trimmed
    return exact


def near_miss(first_line):
    """A sentence naming what a first line that did not resolve got wrong."""
    names = [name for family in families().values() for name in family.names]
    match = re.match(r"Use\s+(%s)\s+(\S+?)[.,;:!]*(\s.*)?$"
                     % "|".join(map(re.escape, names)), first_line,
                     re.IGNORECASE)
    if match:
        repository = match.group(1).lower()
        rest = (match.group(3) or "").strip()
        if rest:
            return ("\n\nThe line names %s %s and then carries further "
                    "text: \"%s\". The prompt opens by naming the worktree "
                    "and nothing else; everything else goes in a later "
                    "sentence or line."
                    % (repository, match.group(2), rest))
        return ("\n\nThe line names a %s worktree as \"%s\". This form "
                "names a worktree by a code of one or two letters or digits, "
                "such as %s G7." % (repository, match.group(2), repository))
    if not re.match(r"Use\b", first_line, re.IGNORECASE):
        return ("\n\nThe line does not begin with the word \"Use\", which "
                "every form below begins with.")
    return ("\n\nThe line begins with \"Use\". What follows that word "
            "matches none of the forms below, or is followed by further text.")


def contains(directory, path):
    """Whether `path` is `directory` or something inside it.

    The comparison folds case because the volume these worktrees live on
    does, so two spellings of one directory are one directory here.
    """
    directory = os.path.abspath(directory).lower()
    path = os.path.abspath(path or os.getcwd()).lower()
    return path == directory or path.startswith(directory + os.sep)


def title_worktree(item):
    """(kind, name) for one item of a title's list of worktrees, or None."""
    for kind, family in families().items():
        match = re.fullmatch(identifier_pattern(family), item.strip(),
                             re.IGNORECASE)
        if match:
            return kind, canonical(kind, match.group(1))
    return None


def title_worktrees(title):
    """The (kind, name) of each worktree that a session title opens with.

    Titles take the form "WORKTREES: STATE SUMMARY", where WORKTREES is a
    comma-separated list and STATE an emoji. A title without that list
    starts with the emoji, and names no worktree even when its summary has
    a colon in it. Items in the list that name no worktree, such as a pull
    request number, are passed over. The state is not required, so a title
    that opens with a word and a colon, as in "CI: red main", is read as
    naming the worktree that word identifies, if any.
    """
    match = TITLE_HEAD.match(title or "")
    if not match:
        return set()
    items = {title_worktree(item) for item in match.group(1).split(",")}
    return items - {None}



def live_claude_pids():
    result = subprocess.run(["ps", "-A", "-o", "pid=,comm="],
                            capture_output=True, text=True)
    pids = set()
    for line in result.stdout.splitlines():
        number, _, command = line.strip().partition(" ")
        if "claude" in command.lower() and number.isdigit():
            pids.add(int(number))
    return pids


def claude_sessions():
    """A Session for every running Claude Code session."""
    pids = live_claude_pids()
    sessions = []
    for path in glob.glob(os.path.join(CLAUDE_DIR, "sessions", "*.json")):
        try:
            with open(path, encoding="utf-8") as handle:
                record = json.load(handle)
        except (OSError, ValueError):
            continue
        if record.get("pid") in pids:
            sessions.append(Session(record.get("sessionId"), record.get("cwd"),
                                    record.get("name") or "", "Claude session",
                                    record.get("hostSessionId")))
    return sessions


def codex_sessions(state=CODEX_STATE):
    """A Session for every Codex thread that has a title, has not been
    archived, and is not a subagent's thread.

    A Codex thread lasts until it is archived, whether or not the Codex app
    is running, so it holds the worktrees its title names until then. A
    subagent's thread, such as one that Codex starts to review a command
    before it runs, works for the thread that started it, which is the one
    that holds the worktree.
    """
    paths = glob.glob(state)
    if not paths:
        return []
    newest = max(paths, key=lambda path: int(re.search(
        r"([0-9]+)\.sqlite$", path).group(1)))
    try:
        with closing(sqlite3.connect("file:%s?mode=ro" % newest,
                                     uri=True)) as database:
            rows = database.execute(
                "SELECT id, cwd, name FROM threads WHERE archived = 0 "
                "AND name != '' AND CASE WHEN json_valid(source) "
                "THEN json_extract(source, '$.subagent') END IS NULL")
            return [Session(*row, "Codex thread", None) for row in rows]
    except sqlite3.Error as error:
        deny("The Codex thread list in %s could not be read, so the gate "
             "cannot tell which worktrees Codex threads hold: %s"
             % (newest, error))


@functools.cache
def live_sessions():
    """A Session for every session that can hold a worktree."""
    return claude_sessions() + codex_sessions()


def app_record(session, directory=APP_SESSIONS):
    """The desktop app's record of a session, or {} when it has none that
    can be read."""
    if not session.host:
        return {}
    for path in glob.glob(os.path.join(directory, "%s.json" % session.host)):
        try:
            with open(path, encoding="utf-8") as handle:
                record = json.load(handle)
        except (OSError, ValueError):
            continue
        if isinstance(record, dict):
            return record
    return {}


def awaiting_brief(sessions, caller, proposal, record=app_record):
    """The session the app opened when the user accepted the offer
    `proposal` that the session `caller` made, while that session still
    waits for its brief, or None.

    The app opens the session under the offer's title, and the session
    changes its title as soon as it starts work on its brief, so a session
    that still has the offer's title is waiting for its brief."""
    if not caller or not caller.host:
        return None
    for session in sessions:
        spawned = record(session).get("spawnedFrom")
        if (isinstance(spawned, dict) and spawned.get("taskId") == proposal
                and spawned.get("sessionId") == caller.host
                and spawned.get("title") and session.title == spawned["title"]):
            return session
    return None


def holds(session, kind, name, directory):
    """Whether a session is working in a worktree.

    Sessions mostly keep the directory they were started in and move
    between worktrees within it, so the worktrees a session's title names
    are what say where it works. The working directory counts as well.
    """
    return ((session.cwd and contains(directory, session.cwd))
            or (kind, name) in title_worktrees(session.title))


def occupant(kind, name, directory, others):
    """A description of a session working in a worktree, if there is one."""
    for session in others:
        if holds(session, kind, name, directory):
            return "the %s \"%s\"" % (session.description,
                                      session.title or session.id)
    return None


def worktree_is_dirty(directory):
    result = subprocess.run(["git", "-C", directory, "status", "--porcelain"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        return False
    return bool(result.stdout.strip())


def check_worktree(payload, kind, name, directory, live, recipient=None):
    """Deny the call unless a worktree is outside the range reserved for
    Codex, is not this session's, is held by no other of the sessions that
    `live` lists than the one that is to receive the brief, and is
    pristine."""
    here = label(kind, name)
    if name[0].isdigit():
        deny("%s is reserved for Codex, which is given the worktrees whose "
             "codes start with a digit. Pick a worktree whose code starts "
             "with a letter." % here)

    own_id = payload.get("session_id")
    sessions = live()
    others = [s for s in sessions
              if (not own_id or s.id != own_id) and s != recipient]
    own = [s for s in sessions if own_id and s.id == own_id]
    own.append(Session(own_id, payload.get("cwd"), "", "Claude session", None))
    if any(holds(s, kind, name, directory) for s in own):
        deny("%s is the worktree this session is working in. A new session "
             "must be given a different worktree." % here)
    holder = occupant(kind, name, directory, others)
    if holder:
        deny("%s is in use by %s. Pick a worktree that no session is "
             "using." % (here, holder))
    if worktree_is_dirty(directory):
        deny("%s has uncommitted changes, so it is not pristine. Pick a "
             "different worktree, or land the work already in this one "
             "first. Do not discard it with git checkout, git restore, or "
             "git stash." % here)


def check(payload, live=live_sessions, record=app_record):
    """Decide on the call a hook payload describes, given a function that
    lists the live sessions and one that reads the app's record of a
    session."""
    tool_input = payload.get("tool_input") or {}
    prompt = tool_input.get("prompt") or ""
    title = tool_input.get("title") or ""
    proposal = tool_input.get("proposal_id")
    if not prompt.strip():
        if tool_input.get("initiation") == "offer":
            for kind, name in sorted(title_worktrees(title)):
                check_worktree(payload, kind, name, worktree_path(kind, name),
                               live)
            allow()
        if proposal:
            allow()

    waiver = WAIVER.search(prompt)
    if waiver:
        waive(waiver.group(1))
    if WAIVER_WITHOUT_REASON.search(prompt):
        deny("The session prompt waives the worktree checks but gives no "
             "reason. The waiver line takes the form \"Worktree checks "
             "waived: REASON\", and the reason is shown to the user when the "
             "session is spawned.")

    start = opening(prompt)
    kind, name, directory = resolve(start)
    if kind is None:
        if not start:
            deny("The session prompt does not open by naming a worktree: the "
                 "prompt is empty.")
        deny("The session prompt does not open by naming a worktree. It "
             "opens with:\n\n  %s%s" % (start, near_miss(start)))

    if kind == "path":
        if not os.path.isdir(directory):
            deny("There is no directory %s." % directory)
        allow()

    here = label(kind, name)
    if proposal and not title:
        caller = next((s for s in live() if s.id == payload.get("session_id")),
                      None)
        recipient = awaiting_brief(live(), caller, proposal, record)
        check_worktree(payload, kind, name, directory, live, recipient)
        offered = title_worktrees(recipient.title) if recipient else set()
        if offered and (kind, name) not in offered:
            deny("The brief names %s, but the app opened the offer's session "
                 "under the title \"%s\", which does not name it. The brief "
                 "must name a worktree that the offer's title names."
                 % (here, recipient.title), None)
        allow()

    check_worktree(payload, kind, name, directory, live)
    if (kind, name) not in title_worktrees(title):
        deny("The new session is to work in %s, so its title must be a "
             "session title that opens with \"%s: \", or with a "
             "comma-separated list of worktree identifiers that includes %s "
             "followed by \": \", and then a summary of what the new session "
             "will do, as in \"%s: ⚙️ Fix the gate\". Its title is:\n\n  %s"
             % (here, identifier(kind, name), identifier(kind, name),
                identifier(kind, name), title.strip() or "(empty)"), None)

    allow()


def main():
    """Check the call, denying it when the check itself fails, since a hook
    that fails lets the call through."""
    try:
        payload = json.load(sys.stdin)
    except ValueError as error:
        deny("The hook payload could not be parsed, so the session prompt "
             "could not be checked: %s" % error)
    try:
        check(payload)
    except Exception as error:
        deny("The gate failed while checking the session prompt: %r" % error)


if __name__ == "__main__":
    main()
