# When spawning sessions, spawning a visible task, or writing agent instructions for new sessions

If there are more than 45 active local sessions, do not proactively start new sessions or offer to start new 
sessions to deal with technical debt or flakes unless the user explicitly requests it. Instead, record the issue 
on the [laundry](topics.md) and leave it at that.

## Writing instructions

When spawning a session or visible task to do independent work, or when writing agent instructions for use in 
another session, instruct them to use a different worktree than the one the current session is using. Start agent 
instructions for work in a repo REPO XX with "Use REPO XX" where REPO is the repository name, and XX is the chosen 
worktree's worktree code, as described in the [identifying worktrees](identifying-worktrees.md) rules (or, for 
brevity, write "use XYZ" where "XYZ" is the worktree identifier). Select that directory as the new agent's working 
directory when spawning it.

Anything included in your instructions (CLAUDE.md or AGENTS.md, or files referenced therefrom) should not be 
repeated in instructions you write for the other agent, as they will also have those instructions. Similarly, 
instructions included in the repository documentation does not need to be repeated. Avoid giving overly-specific 
guidance regarding the shape of the solution. Instructions should focus on the problem being solved, and the 
symptoms of that problem, plus any constraints that were not self-evident to you. You can assume the target agent 
has the same general knowledge, skills, and abilities as you do.

Always end your instructions with an indication to the receiving agent that the instructions were written by an 
agent and not by the user, and that the user therefore is not familiar with the details of the brief.


## Choosing a worktree

When choosing a worktree, use the steps for [choosing a worktree](identifying-worktrees.md).

Once you have picked one, if it exists already, reset it to pristine condition before spawning the session or 
writing the agent instructions. If it does not exist, you may let the session create it itself.

Before actually spawning a new session in this way, check open PRs and Claude and Codex sessions, and Claude's 
pending session queue, for existing work in this area, to avoid duplicate efforts. Look at [the topics 
board](topics.md) to see if anyone else is working on this.


## Codex-specific instructions

When the user says to "spawn a session" or similar, if you are Codex, interpret it as using 
`codex_app__create_thread`, and do not wait for the task to return.


## Claude-specific instructions

### `mcp__ccd_session__start_session` arguments

When using `mcp__ccd_session__start_session`, if the task is instructed to work in a particular worktree, write 
the `title` in the form of a session title without a state, `WORKTREES: SUMMARY`, just the worktree identifier, a 
colon, and a summary of what the session is going to do.

An offer (`initiation` "offer") carries a title alone and asks the user before any brief exists. Choose the 
worktree before making the offer. Write the offer's title in the same form, because a session started from the 
offer keeps that title. If the user chooses a new session, the call that sends the brief names the offer 
by its `proposal_id` and carries the `prompt`, which follows the rules below and names the same worktree, but 
no title.

If the task is instructed to work on a worktree related to commonfabric, use ~/dev/commonfabric as the `cwd`. 
Otherwise if another worktree was selected, use that as the `cwd`. Otherwise, use `~/dev`. (Only provide a `cwd` 
for `user_asked`, not proposals.)

### The gate on spawning sessions

This section and the next describe a Claude Code mechanism, and apply only to Claude Code sessions. The rules
above apply everywhere.

In a Claude Code session, every `mcp__ccd_session__start_session` call passes through 
`~/.claude/hooks/spawn-task-gate.py`, registered as a PreToolUse hook in `~/.claude/settings.json`. The gate 
allows a call only when the first non-blank line of the session prompt names the worktree the session is to work 
in, and nothing else, e.g.:

- `Use labs XX` for a labs worktree
- `Use weaver XX` or `use ωXX` for a weaver worktree
- `Use INFRAXX` for an infra worktree
- `Use loom XX` or `use 𝛌XX` for a loom worktree
- `Use denoXX` for a deno worktree
- `Use gvisor-XX` for a gvisor worktree (or `REPO-XX` generally for any commonfabric worktree)
- `Use PATH` for any other directory, given as an absolute or `~`-prefixed path

A path into one of the worktrees above is checked as that worktree.

The gate also checks that it is outside the range reserved for Codex: worktree codes that start with a digit.

Every worktree then goes through three more checks. It must not be the worktree the current session is working in. 
No other session may be working in it, where the sessions are the running Claude Code sessions and the Codex 
threads that have not been archived. Its working tree must have no uncommitted changes. A session counts as 
working in a worktree when the worktree list at the start of its session title names it, or when the session's 
working directory is inside the worktree. Sessions mostly stay in the directory they were started in, so the title 
is usually the only record of where a session works.

A worktree need not exist, because the session that is given it creates it. A directory given by its path must 
exist.

The gate also verifies the `title` matches the rules described earlier.

Two calls carry no prompt. The gate allows an offer when every worktree its title names passes the checks 
above. It allows a call that starts an `own_initiative` proposal by its `proposal_id` alone, because that 
proposal's prompt and title were checked when it was proposed.

#### Waiving the gate

Not all work belongs in a fresh labs worktree. A session for a Codex worktree, for the directory the current 
session is already working in, or for anywhere else the checks above do not fit, is spawned by putting this line 
anywhere in the session prompt:

    Worktree checks waived: REASON

The reason is required, and says why the session does not go in a fresh labs worktree of its own. It is shown to 
the user as the session is spawned, so a waived session is never silent.


## Subagents

- [When launching subagents for reviews, prepare their worktrees first](review-subagent-isolation.md)
