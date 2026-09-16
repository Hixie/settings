# Guidance regarding Claude-specific tooling

A `cd` inside a command changes the session's primary working directory for the rest of the current turn and is not 
carried past the turn boundary. Using `run_in_background: true` will avoid that.

The `change_directory` tool moves the session durably but requires user confirmation; this will seem to you like 
an instantaneous action but in reality will stall your session because the user may not see it for many hours. 
Prefer not using it at all, or, and only if your task is not critical, using it once, at the start of the session. 
The `change_directory` tool takes effect at the end of a turn; subagents spawned during that turn will _not_ be 
affected by it, they will see the old directory.

The `Agent` tool's `isolation: "worktree"` feature requires that the session's working directory to be inside a 
git repository. Beware, `isolation: "worktree"` branches from the main worktree, not the calling session!
