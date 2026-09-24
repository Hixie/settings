# When spawning chips, spawning a visible task, or writing agent instructions for new sessions

## Writing instructions

When spawning a chip or visible task to do independent work, or when writing agent instructions for use in another 
session, instruct them to use a different worktree than the one the current session is using. Start agent 
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


## Choosing a worktree

When choosing a worktree, use the steps for [choosing a worktree](identifying-worktrees.md).

Once you have picked one, if it exists already, reset it to pristine condition before spawning the chip or writing 
the agent instructions. If it does not exist, you may let the session create it itself.

Before actually spawning a new session in this way, check open PRs and Claude and Codex sessions, and Claude's 
pending chip queue, for existing work in this area, to avoid duplicate efforts. Look at [the topics 
board](topics.md) to see if anyone else is working on this.


## Codex-specific instructions

When the user says to "spawn a chip", if you are Codex, interpret it as using `codex_app__create_thread`, and do 
not wait for the task to return.


## The gate on spawning chips

This section and the next describe a Claude Code mechanism, and apply only to Claude Code sessions. The rules
above apply everywhere.

In a Claude Code session, every `spawn_task` call passes through `~/.claude/hooks/spawn-task-gate.py`, registered 
as a PreToolUse hook in `~/.claude/settings.json`. The gate allows a call only when the first non-blank line of 
the chip prompt names the worktree the chip is to work in, and nothing else, e.g.:

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
exist. A denial hands back this file in full.

### Waiving the gate

Not all work belongs in a fresh labs worktree. A chip for a Codex worktree, for the directory the current session 
is already working in, or for anywhere else the checks above do not fit, is spawned by putting this line anywhere 
in the chip prompt:

    Worktree checks waived: REASON

The reason is required, and says why the chip does not go in a fresh labs worktree of its own. It is shown to
the user as the chip is spawned, so a waived chip is never silent.


## Subagents

- [When launching subagents for reviews, prepare their worktrees first](review-subagent-isolation.md)
