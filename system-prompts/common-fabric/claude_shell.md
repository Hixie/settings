# Guidance for Claude when using the shell

## Read files with `Read`

Rather than `cat`, `head`, or `sed`, prefer reading with the `Read` tool, paging with `offset` and `limit` (up to 
2,000 lines a page). Use `Bash` to search (`grep`, `rg`) and to run commands, not to print file contents. Bash 
output over 30,000 characters is saved to a file with only a preview shown, which costs an extra call.

When writing briefs for [review subagents](reviews.md), tell them the precise path to the patch you want them to 
read, and name the `Read` tool explicitly as the mechanism they should use to read it.

## Long commands

Run any command that can take more than a couple of minutes, such as a test suite, a build, a gate or a job that 
waits in a queue, through longrun, in one call:

    /Users/ianh/dev/contraptions/longrun/longrun.py run 'COMMAND'

Give it the bare command. Do not pipe it through `tail` or `grep`, and do not redirect its output: longrun keeps 
the whole output in a log in your scratchpad, and a command whose output goes to `tail` prints nothing until it 
ends, so it looks stalled. When the command ends, longrun prints its exit status, how long it took, the log's 
path, and the part of the log that matters, numbered as in the log: the test runner's summary when longrun 
recognises it, and otherwise the last lines. Read the log only for what that part leaves out, by line number.

Run every longrun call, `run` and `wait` alike, bare too: do not pipe it, redirect it, or wrap it in `$(...)`. Its 
exit status is the result, the command's own status or 75 for a stall, and a pipeline reports `tail`'s status 
instead. Its report is already short, and it opens with how the command ended, which is what `tail` would drop.

The call blocks until the command ends. A hook gives it the longest timeout Claude Code allows, so do not set 
`timeout` yourself, and do not poll, sleep or read the log while it runs.

If the command prints nothing for 10 minutes, the call returns with exit status 75 and a report that starts with 
`STALLED`. The command is still running. The report says what each of its processes is doing. Decide at once what 
to do:

- If a process is waiting for something that will come, such as a free slot in a queue, or is busy in a long 
  silent step, run `.../longrun.py wait RUN`. It blocks until the command ends or stalls again, and never reports 
  the same stall twice.

- If a process is waiting for something that will never happen, run `.../longrun.py stop RUN`, then fix the cause.

For a command that is known to stay silent for longer, give `--quiet MINUTES`.

When the command's job is to start a process that outlives it, such as `bench-weaver.sh up`, a development server 
or a local service, give `--keep`:

    /Users/ianh/dev/contraptions/longrun/longrun.py run --keep 'COMMAND'

Without it, longrun ends whatever the command leaves running when it exits, and the result lists what it ended. Do 
not give `--keep` to a test suite or a build to make that list go away: a test or build that leaves processes 
running has a bug to fix.

In a main session, `run_in_background: true` on a `.../longrun.py run` call lets you work while it runs. You are 
notified when it ends or stalls, and its output is the same short report.

In a subagent, block instead. Claude Code moves a subagent's call to the background after a few minutes, whatever 
its timeout, unless the call starts with `sleep`, so the hook starts a subagent's longrun call with `sleep 0;`. Do 
not end your turn, read the log, or sleep while a run is going.

## Stopping processes

To stop a process you started, use `TaskStop` for a background task and `.../longrun.py stop RUN` for a longrun 
run. The permission classifier allows both.

To stop any other process of yours, such as one whose handle you lost to a context summary and found again with 
`ps`, `lsof`, or `pgrep`, run:

    /Users/ianh/dev/contraptions/claude-stop-own/claude-stop-own.py [--tree] [--signal NAME] PID ...

It signals a PID only when the process descends from your Claude process, runs in your own 
`~/dev/commonfabric/REPO/XX` worktree, or names your scratchpad as its working directory or on its command line. 
It refuses every other PID, printing the process's working directory and command line, and then exits with status 
1. `--tree` also stops each descendant that meets one of those conditions itself.

A permission rule allows claude-stop-own without consulting the classifier, but only when it is the whole command. 
Find the PID in an earlier call, and do not put a `cd` before it, pipe into it, use `$(...)` in its arguments, or 
set a variable in front of it. Run it with the environment Claude Code gives you: do not set `CLAUDE_PID`, 
`CLAUDE_CODE_SESSION_ID`, or `HOME` for it, and do not change directory into another session's worktree to run it.

Do not run `kill` on a PID you found with `ps`, `lsof`, or `pgrep`. The permission classifier sees your command but 
not the output of your earlier commands, so it cannot tell that the process is yours, and it denies the command. If 
claude-stop-own refuses a process that you believe is yours, report its PID, working directory, and command line to 
the user rather than working around the refusal.

## One outward action per command

Run a command that changes something outside your worktree and scratchpad in a Bash call of its own. Examples are a 
push, a process signal, a worktree removal, a deploy, and a topics board write. Do not prefix it with `cd`, chain 
it with `&&` or `;`, pipe it, or bundle reads with it. Run the checks it depends on in an earlier call.

The permission classifier judges a whole command at once, so a denial of one step loses every other step in that 
command. A permission allow rule applies only when every part of a compound command matches it.

## The shell

Commands run in zsh, not bash. `~/.zshenv` sets options in the shell that runs each agent command so that it 
expands words the way bash does:

- a glob that matches nothing, or a malformed glob, is passed on as typed;
- a word starting with `=` is an ordinary word, so `echo ===` and `[ a == b ]` work;
- an unquoted `$var` is split on whitespace and globbed;
- arrays start at 0, and neither `"$v[0]"` nor `$ref:src/x` is a subscript or a modifier;
- `[[ =~ ]]` fills `BASH_REMATCH`;
- `echo` does not interpret backslashes unless given `-e`.

A zsh script that a command runs keeps zsh's defaults.

No option changes the following, so avoid these bash idioms:

- `status` is a read-only variable. Name an exit code something else, such as `rc`.
- `path` is the array form of `PATH`. A variable named `path` replaces the command search path.
- `PIPESTATUS` does not exist. The zsh equivalent is `pipestatus`, which also starts at 0 in agent shells.
- `shopt`, `mapfile`, and `readarray` do not exist. `read -a` is spelled `read -A`.
- `${x,,}`, `${x^^}`, `${!x}`, and `${!arr[@]}` are bad substitutions.
- `VAR=x time cmd` is a parse error. Write `time VAR=x cmd`.

`/bin/bash` is version 3.2, which also lacks `mapfile`, `${x,,}`, and associative arrays.

## `grep`

In Claude Code shells, `grep` is a function that runs the bundled ugrep with `-I` and `--ignore-files`. It 
silently skips any file that looks binary, even a file named on the command line. In that case there is no output, 
even with `-c`, and the exit status is 1. A recursive search also skips every file that a `.gitignore` excludes. 
Test and probe logs often contain control bytes or broken UTF-8, and they are often in ignored directories. For 
those, use `command grep`, the system grep, which searches everything and prints "Binary file ... matches". With 
the function, `-a` stops it skipping binary files and `--no-ignore-files` stops it skipping ignored ones.

## Working directories

A `cd` inside a command changes the session's primary working directory for the rest of the current turn when the 
target lies inside the directory tree the session is already allowed to work in; this change is not carried past 
the turn boundary. Using `run_in_background: true` will avoid changing the directory in your session.

The directory changing back happens silently at a turn boundary. One symptom is that `deno` will say "no version 
configured here" or similar in subsequent turns. Generally, an unexplained working-directory change in the 
environment block (reported after the next command) is caused by the turn-boundary revert, not something you did.

A `cd` to a directory outside the tree the session is allowed to work in will report "Shell cwd was reset to" with 
no environment update at all (though the command itself still runs in the target directory).

The `change_directory` tool moves the session durably but always requires user confirmation; this will seem to you 
like an instantaneous action but in reality will stall your session because the user may not see it for many 
hours. You will not experience this stall, but the user will: the median cost is 4m39s, one call in twelve exceeds 
an hour, the worst on record took three days. A seemingly fast return is not evidence that no confirmation was 
required. Prefer not using it at all. If you must, use it only once, at the start of the session, and only if your 
task is not time-sensitive.

The cheap (no confirmation, so no interruption) alternative to `change_directory` within the session's current 
working directory is a `cd` at the start of each turn.

When `change_directory` moves the primary directory, the previous one is dropped from the allowed list. This means 
that toggling back and forth requires multiple user confirmations.

The `change_directory` tool takes effect at the end of a turn; subagents spawned during that turn will _not_ be 
affected by it (they will see the old directory).

## Versioning

When you first read this file, tell the user: Read 🐚 6.
