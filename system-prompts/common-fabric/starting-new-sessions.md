# When spawning chips, spawning a visible task, or writing agent instructions for new sessions

An unused repo is one that no other session is using, and that has no active work (you may `git fetch` and check 
if the latest branch has landed to determine this).


## Labs work

When spawning a chip or visible task to do independent work, or when writing agent instructions for use in another 
session, instruct them to use a different labs repo than the one the current session is using. Always start agent 
instructions for work in a labs repo with "Use labs XX" where XX is the chosen worktree. Select that directory as 
the new agent's working directory when spawning it.

When choosing a labs repo worktree, select a currently-unused labs. Once you have picked an unused labs repo, 
reset it to pristine condition before spawning the chip or writing the agent instructions.

Where relevant, prefer the following associations ([these suffixes are to be interpreted in base 
36](labs-dev-servers-port-offset.md)):

- labs 1 to labs 9: for use by Codex for [production and red main fixes](prodred.md).
- labs 10 to labs 8Z: for use by Codex.
- labs 80 to labs 8Z: for use by Codex for Dashboard-related work.
- labs 90 to labs 9Z: for use by Codex for deflaking.
- labs B0-BZ: for use by Claude for follow-up work from another session in the labs B or B0-BZ range.
- labs C0-CZ: for use by Claude for CFC-related work.
- labs D0-DZ: for use by Claude for Dashboard work.
- labs E0-EZ: for use by Claude for [production and red main fixes](prodred.md) and other bug fixing tasks.
- labs F0-FZ: for use by Claude for dealing with flakes (including those found during babysitting).
- labs G0-GZ: for use by Claude for technical debt work.
- labs L0-LZ: for use by Claude for feature work that does not fit another category.
- labs R0-RZ: for use by Claude for regression-related work (especially performance-related work).
- labs T0-TZ: for use by Claude for timeout-related, sleep-related, or retry-loop-related issues.
- labs U0-UZ: for use by Claude for user-facing improvements.
- labs Z0-ZZ: for use by Claude for work related to `cf view`.

Before actually spawning a new session in this way, check open PRs and Claude and Codex sessions, and Claude's 
pending chip queue, for existing work in this area, to avoid duplicate efforts. Look at [the topics 
board](topics.md) to see if anyone else is working on this.


## Weaver work

When spawning new sessions in weaver worktrees, use the [weaver conventions](weaver.md). Always start agent
instructions for work in a weaver worktree with "Use weaver XX" where XX is the chosen worktree. The worktree
does not have to exist yet; the session that is given it creates it if it is missing.

Prefer unused worktrees to creating new ones.


## Loom work

Similar rules apply for [loom](loom.md) worktrees.


## Codex-specific instructions

When the user says to "spawn a chip", if you are Codex, interpret it as using `codex_app__create_thread`, and do 
not wait for the task to return.


## The gate on spawning chips

This section and the next describe a Claude Code mechanism, and apply only to Claude Code sessions. The rules
above apply everywhere.

In a Claude Code session, every `spawn_task` call passes through
`~/.claude/hooks/spawn-task-gate.py`, registered as a PreToolUse hook in `~/.claude/settings.json`. The gate
allows a call only when the first non-blank line of the chip prompt names the worktree the chip is to work in,
and nothing else:

- `Use labs XX` for a labs worktree
- `Use weaver XX` for a weaver worktree
- `Use INFRA123` for an infra worktree
- `Use loom N` for a loom worktree
- `Use denoX` for a deno worktree
- `Use PATH` for any other directory, given as an absolute or `~`-prefixed path

A path into one of the worktrees above is checked as that worktree.

For a labs worktree the gate also checks that the worktree exists, that it is not labs 0 (the root copy),
and that it is outside the range reserved for Codex. For a weaver worktree, the range reserved for Codex is
every name that starts with a digit, however long the name. In both the labs and weaver forms the name is one
or two letters or digits, and the gate uppercases it.

Every worktree then goes through three more checks. It must not be the worktree the current session is working
in. No other session may be working in it, where the sessions are the running Claude Code sessions and the
Codex threads that have not been archived. Its working tree must have no uncommitted changes. A session counts
as working in a worktree when the worktree list at the start of its session title names it, or when the
session's working directory is inside the worktree. Sessions mostly stay in the directory they were started
in, so the title is usually the only record of where a session works.

A labs or deno worktree must already exist. A weaver, loom, or infra worktree need not exist, because the
session that is given it creates it. A denial hands back this file in full, and adds the weaver conventions
when the worktree it turned away was a weaver one. A denial of a labs or weaver worktree also names the
unoccupied and pristine worktrees in the same range.

### Waiving the gate

Not all work belongs in a fresh labs worktree. A chip for a Codex repo, for the directory the current session
is already working in, or for anywhere else the checks above do not fit, is spawned by putting this line
anywhere in the chip prompt:

    Worktree checks waived: REASON

The reason is required, and says why the chip does not go in a fresh labs worktree of its own. It is shown to
the user as the chip is spawned, so a waived chip is never silent.


## Subagents

- [When launching subagents for reviews, prepare their worktrees first](review-subagent-isolation.md)
