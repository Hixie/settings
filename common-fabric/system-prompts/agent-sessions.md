# agent-sessions

`~/bin/agent-sessions` answers questions about the Claude and Codex sessions on this machine from the files those
programs keep on disk, in one command, without the desktop app's session-management tools. Use it to find which
session holds a worktree, what state a session is in, which sessions are stacked on which, what permission mode
another session is in, where a session's transcript is, which sessions mentioned something, which worktrees no
session uses, and which sessions to wake up. It changes nothing but its own cache.

```sh
agent-sessions                         # one line per current session
agent-sessions list --harness codex    # only Codex threads
agent-sessions list --all --grep 'jinja|terraform'
agent-sessions show --worktree VB      # the sessions that claim labs VB
agent-sessions show --session 8eb1a0c3 # a session, by its ID or the start of it
agent-sessions search 'prune.*cache'   # the sessions whose messages mention it
agent-sessions worktrees               # each claimed worktree and its holders
agent-sessions check                   # conflicting and unguarded claims
agent-sessions free labs               # labs worktrees that no session uses
agent-sessions wake                    # sessions to wake up or tell to reorient
agent-sessions graph --mermaid         # which sessions are stacked on which
```

Every command takes `--json`, which prints the same facts as JSON. `list` and `show` also take `--all`, which
includes archived sessions and Codex threads without a title. These options can go before or after the command's
name.

Each session runs in a harness: `claude-desktop` for a Claude session the desktop app started, whose ID starts with
`local_`; `claude-cli` for a Claude session started from a terminal, whose ID is its Claude Code session's; and
`codex` for a Codex thread. Output names each session by its harness and ID, as in
`claude-desktop local_8eb1a0c3-…`, and puts its title in quotation marks. `list`, `show`, `search`, `free` and
`wake` take `--harness`, which keeps only that harness; `--harness claude` stands for both of Claude's, and the
option can be given more than once.

## Commands

`list` (the default) prints one line per session: its status, harness, ID, title, and, where it has them, its
permission mode and model. `--state`, `--mode`, `--grep` and `--harness` narrow the list. `--grep` takes a regular
expression and matches it, ignoring case, against the session's title, its earlier titles, the desktop app's
summary of its last turn, and a Codex thread's first message.

`show` prints everything the tool knows about each session that a name picks out. There are two kinds of name:

- `--session ID`: a session's ID, or the start of one: a Claude desktop session's ID (with or without `local_`),
  the ID of any Claude Code session that ran it, which names its transcript file, or a Codex thread's ID;
- `--worktree WORKTREE`: a worktree, written as its identifier (`VB`, `ωLF`, `ℂEJ`, `INFRAE0`, `deno1`,
  `specs-CF`, `contraptions`), as `labs VB`, or as a path, which picks out the sessions that claim the worktree and
  the sessions stacked on it.

Each option can be given more than once, and `show` prints every session that any of the names picks out. With
`--harness`, a name picks out only the sessions in that harness, so a name that picks out only sessions in other
harnesses picks out none. `show` exits with status 1, after printing what it found, if a name picks out none. The
facts include the session's permission mode, model, working directory, process ID and status, the session that
started it, its earlier titles, the desktop app's summary of its last turn, the paths of its transcripts, and how
its last turn ended (see `wake`).

`search REGEX` lists the sessions, archived ones included, in whose messages a regular expression matches, ignoring
case. The messages are those that a person typed into the session and those that the session's agent wrote; tool
results, notifications, hook feedback, system reminders, summaries of compacted conversations, and messages from
other sessions and from subagents are left out. Each line gives the time of the newest match, the session's status,
the session, the number of its messages that match, and the text around the newest match. Put the alternatives in
one pattern rather than searching once for each: other wordings, as in
`remov\w* .{0,20}variables|variables .{0,30}(deleted|obsolete)`, and several things at once, as in
`pull/(8535|8566|8555)`. A pattern matches words, not meanings, so think of the words the session would have used.
It lists the 20 sessions with the newest matches; `--limit N` changes that, and `--limit 0` lists them all. It
searches the transcripts of every session this tool knows of in seconds, with ripgrep (`rg`) finding the lines that
could match, so it needs ripgrep.

`worktrees` prints each worktree that a session claims, its path, whether it exists, which sessions hold it, which
sessions with no running process claim it, and which sessions are stacked on it. Name worktrees to print only
those, whether or not a session claims them.

`check` prints what is wrong with the sessions' claims on worktrees, and exits with status 1 when there is
anything:

- `conflict`: two or more sessions hold the same worktree.
- `missing`: a session claims a worktree whose directory does not exist.
- `unguarded`: the only sessions that claim a worktree have no running process. The spawn gate does not count such
  sessions, so it would let a new session take the worktree.
- `unheld-base`: a session is stacked on a worktree that no session claims.
- `finished-base`: a session is stacked on a worktree whose sessions have all finished: their work has merged (🪻),
  or they had nothing to merge (🫖).
- `lost-folder`: a Claude session that is not archived works in a folder that no longer exists. The app refuses to
  deliver messages to it.
- `unlisted-base`: a session's state is 📚, but its title lists no worktree it is stacked on.
- `unrecognised`: a title lists something that is neither a worktree identifier nor a pull request number such as
  `#12`, for example `𝛌G3`, so the spawn gate does not count it.

`free REPOSITORY` prints the worktrees of a repository that no session uses: no current session claims them or is
stacked on them, they have no uncommitted changes, and the commit they have checked out is on the repository's main
branch, as last fetched (upstream's when the repository has an upstream remote, origin's otherwise). Those are the
worktrees that can be cleaned up or given to a new session. `--harness claude` keeps only the codes set aside for
Claude, which start with a letter, and `--harness codex` only those for Codex, which start with a digit.
`--prefix X` keeps only the codes that start with X. Use it to choose within the range of codes that a repository's
own rules set aside for a kind of work: `free labs --prefix B` lists only B0 to BZ, the labs worktrees for
follow-up work, and `free weaver --prefix F` only F0 to FZ, the weaver worktrees for flaky tests. `free` knows
nothing of those rules itself. `--unlanded` adds the worktrees whose commit is not on main, which may hold work
that has not landed, or work that landed as a squashed commit.

`wake` does the reading that [the waking-up instructions](wake_up.md) ask for when someone says to wake everyone
up. It lists the current sessions (see `--all`) whose last turn was interrupted (`wake`), and those whose last turn
was not interrupted and that have been idle for more than 12 hours (`reorient`). Each line of a Claude session
gives its permission mode, which must match the sender's own before a Claude session sends it a message. A session
whose last turn cannot be read, usually because it has no transcript, is listed as `unknown`. A Claude session
whose folder no longer exists is listed as `unreachable`, since the app does not deliver messages to it. A session
that is working is left out: a Claude session whose process says it is busy, or a Codex thread whose turn has not
ended and started after the oldest running Codex process.

- `--idle HOURS` changes how long a session must have been idle to be told to reorient.
- When neither `--state` nor `--skip-state` is given, paused sessions (⏸️) are left out. `--state STATE` keeps
  only the sessions in the states it names. `--skip-state STATE` leaves out the sessions in the states it names,
  and with no states leaves out none. Each takes several states after it, or can be given more than once.
- `--harness` keeps only the sessions in that harness.
- `--sender-mode MODE` names the permission mode of the session that will send the messages. Each session in a
  higher mode is marked "lower it to MODE first", and its `lowerTo` in JSON is MODE rather than null. The modes,
  lowest first, are `plan`, `default`, `acceptEdits`, `auto` and `bypassPermissions`.

A Claude session's last turn was interrupted when its transcript ends without a reply that finished: with an API
error such as a usage limit, a reply cut short, a tool call or tool result with no reply, a message with no reply,
or a message queued for the session and never delivered. It was also interrupted when a background task, subagent
or monitor that the session started was killed, as an app restart kills every task still running, unless the
session stopped the task itself or its state says its work has finished (🪻 or 🫖). A turn that someone stopped was
not interrupted. Messages that need no reply do not count as messages with no reply: commands someone ran in the
session's shell, local slash commands and their output, messages made only of system reminders, and notifications
about tasks that had already ended or handed back. A Codex thread's last turn was interrupted when it started and
never ended, and no Codex process now running started before it. Codex records a turn that someone stopped as
aborted, and also every turn still running when it quits; a turn aborted within a second of another thread's last
change was cut off by a quit, and was interrupted.

`graph` prints each stacked session with the sessions that claim the worktrees it is stacked on. `--mermaid` prints
the same as a Mermaid flowchart.

## Sessions and their status

A session's title takes the form `WORKTREES: STATE SUMMARY`. WORKTREES is a comma-separated list of the worktrees
the session holds. STATE is an emoji. A session whose work is stacked on work in other worktrees has the state
`📚 (WORKTREES)`, listing those worktrees.

Each session has one status:

- `running`: a Claude session whose Claude Code process is running.
- `dormant`: a Claude session that has not been archived but has no running process, for example after the desktop
  app stopped it to make room.
- `open`: a Codex thread that has a title and has not been archived.
- `untitled`: a Codex thread that has no title and has not been archived.
- `archived`: an archived Claude session or Codex thread.

A session holds a worktree when its title lists the worktree or its working directory is inside the worktree, and
it is running or open. These are the rules of the hook that guards session spawning,
`~/.claude/hooks/spawn-task-gate.py`. agent-sessions loads that hook's code and uses its functions to read titles,
name worktrees, and decide who holds what, so the two cannot disagree. Dormant sessions are listed apart, because
the hook does not count them. Codex subagent threads are left out, as the hook leaves them out.

## Where the data comes from

- The desktop app keeps one file per Claude session, `local_<id>.json`, in
  `~/Library/Application Support/Claude/claude-code-sessions/<account>/<org>/`, where each of `<account>` and
  `<org>` is a UUID. Directories beside `<org>` whose names go on past the UUID, such as `<org>.superseded.XXXXXX`
  and `<org>.before-recover.XXXXXXXX`, hold old copies of those files, and are not read.
- Claude Code keeps a file per running process in `~/.claude/sessions/`, naming the process, its status, and the
  desktop app's ID for its session.
- Claude Code's transcripts are in `~/.claude/projects/*/<id>.jsonl`, named after the Claude Code session ID,
  which the desktop app's file records as `cliSessionId` (and `priorCliSessionIds` after a restart).
- Codex keeps its threads in the `threads` table of `~/.codex/state_<n>.sqlite`, with the path of each thread's
  transcript.

The desktop app's files total about 250 MB, almost all of it the configuration of remote tool servers. The tool
keeps the fields it uses in `~/Library/Caches/agent-sessions/desktop.json`, and reads a file again only when its
modification time or size has changed. To judge a last turn, it reads the end of the transcript, and finds the
lines anywhere in it that start or end tasks without decoding the rest.

## Cases

`common-fabric/shell/tests/agent-sessions-cases.py` in the settings repository builds a made-up home directory with
sessions, transcripts, worktrees, and a Codex database, and runs agent-sessions against it. It uses the spawn gate
from the same checkout, so it fails if the gate changes in a way agent-sessions does not follow.
