# When spawning chips, spawning a visible task, or writing agent instructions for new sessions

When spawning a chip or visible task to do independent work, or when writing agent instructions for use in another 
session, instruct them to use a different labs repo than the one the current session is using. Always start agent 
instructions for work in a labs repo with "Use labs XX" where XX is the chosen worktree.

When chosing a labs repo wortree, select a currently-unused labs. An unused labs repo is one that no other session 
is using, and that has no active work (you may `git fetch` and check if the latest branch has landed to determine 
this). Once you have picked an unused labs repo, reset it to pristine condition before spawning the chip or 
writing the agent instructions.

Where relevant, prefer the following associations ([these suffixes are to be interpreted in base 
36](labs-dev-servers-port-offset.md)):

- labs 10 to labs 8Z: for use by Codex.
- labs 80 to labs 8Z: for use by Codex for Dashboard-related work.
- labs 90 to labs 9Z: for use by Codex for deflaking.
- labs C0-CZ: for use by Claude for coverage-related tasks.
- labs E0-EZ: for use by Claude for bug fixing tasks.
- labs F0-FZ: for use by Claude for dealing with flakes (incluing those found during babysitting).
- labs G0-GZ: for use by Claude for technical debt work.
- labs L0-LZ: for use by Claude for work that does not fit another category (including dashboard work).
- labs R0-RZ: for use by Claude for regression-related work (especially performance-related work).
- labs T0-TZ: for use by Claude for timeout-related, sleep-related, or retry-loop-related issues.
- labs U0-UZ: for use by Claude for user-facing improvements.
- labs Z0-ZZ: for use by Claude for work related to `cf view`.

Before actually spawning a new session in this way, check open PRs and Claude and Codex sessions, and Claude's 
pending chip queue, for existing work in this area, to avoid duplicate efforts. Look at [the topics 
board](topics.md) to see if anyone else is working on this.


## Codex-specific instructions

When the user says to "spawn a chip", if you are Codex, interpret it as using `codex_app__create_thread`, and do 
not wait for the task to return.


## The gate on spawning chips

This section and the next describe a Claude Code mechanism, and apply only to Claude Code sessions. The rules
above apply everywhere.

In a Claude Code session, every `spawn_task` call passes through
`~/.claude/hooks/spawn-task-gate.py`, registered as a PreToolUse hook in `~/.claude/settings.json`. The gate
allows a call only when the first non-blank line of the chip prompt names the worktree the chip is to work in:

- `Use labs XX` for a labs worktree
- `Use INFRA123` for an infra worktree
- `Use loom NAME` for a loom worktree
- `Use deno.XX` for a deno worktree
- `Use PATH` for any other directory, given as an absolute or `~`-prefixed path

For a labs worktree the gate also checks that the worktree exists, that it is outside the range reserved for
Codex, that it is not the worktree the current session is working in, that no other live session has it as its
working directory, and that its working tree has no uncommitted changes. A denial names the unoccupied and
pristine worktrees in the same range, and hands back this file in full.

### Waiving the gate

Not all work belongs in a fresh labs worktree. A chip for a Codex repo, for the directory the current session
is already working in, or for anywhere else the checks above do not fit, is spawned by putting this line
anywhere in the chip prompt:

    Worktree checks waived: REASON

The reason is required, and says why the chip does not go in a fresh labs worktree of its own. It is shown to
the user as the chip is spawned, so a waived chip is never silent.


## Subagents

- [When launching subagents for reviews, prepare their worktrees first](review-subagent-isolation.md)
