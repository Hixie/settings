# Common Fabric Weaver worktrees

## Selecting weaver worktrees

When selecting a weaver worktree (e.g. to [start a new session](starting-new-sessions.md)), use worktrees that 
start with a digit for Codex and a worktree that starts with a letter for Claude.

For Claude:

- weaver F0-FZ is used for fixing flakes
- weaver U0-UZ is used for user interface fixes

Weaver worktrees may need to be associated with [loom](loom.md) worktrees.

## Testing

Avoid showing visible windows when running tests or experiments. They disrupt the user, who is using the computer 
to review the output of other sessions while you work.

Logs must go in your session scratchpad, not in the ~/dev/ directory hierarchy.
