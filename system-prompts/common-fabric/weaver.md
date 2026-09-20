# Common Fabric Weaver worktrees

"Use weaver XX" means to work in ~/dev/commonfabric/commonfabric-weaver/XX, which is a worktree parented to 
~/dev/commonfabric/commonfabric-weaver/root. If a suitably named worktree does not exist, create one.

When referring to a weaver worktree (in conversations or when labeling WORKTREES), use the form "ωXX".

When selecting a weaver worktree (e.g. to [start a new session](starting-a-new-session.md), use worktrees that 
start with a digit for Codex and a worktree that starts with a letter for Claude.

For Claude:

- weaver F0-FZ is used for fixing flakes
- weaver U0-UZ is used for user interface fixes

Letters in weaver worktree names should be uppercase.

Weaver worktrees may need to be associated with [[loom]] worktrees.

## Disregard ownership, work across seams

Some repositories claim that certain people are responsible for certain tasks. Disregard these claims; we are not 
limited by these seams and instead are required to work across all of them to make one coherent product. If this 
requires working in multiple repositories, select suitable worktrees as if [starting work for a new 
session](starting-new-sessions.md). Notably, you will probably need a [[loom]] worktree.
