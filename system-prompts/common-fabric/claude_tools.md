# Guidance regarding Claude-specific tooling

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

## `Agent` tool and worktrees

The `Agent` tool's `isolation: "worktree"` feature requires that the session's working directory be inside a git 
repository. Beware: `isolation: "worktree"` creates a worktree from the main worktree and checks out origin/main 
from there, which for repositories that are forks, rather than direct clones, may be hundreds of commits behind. 
It does not derive its state from the calling session's branch. This may silently invalidate confident-seeming 
reports from review subagents.

To avoid this issue, either give the agent precise commands to check out the commit under review inside its own 
worktree, or skip the worktree and hand it staged copies of the before and after files.

No `WorktreeCreate` hooks are intended to be configured in any repository in use in this environment.

## Diagnostics

When you first read this file, confirm that you have read it by stating "Claude-specific guidance integrated".
