# Give review and verification subagents their own worktree

When you spawn review or verification subagents — especially general-purpose ones that may run `git checkout`, 
`git stash`, `git apply`, execute tests, or write files — give them their own git worktree in a dedicated 
temporary directory (e.g. a subdirectory of the session scratchpad). Running them in the shared working directory 
lets several of them mutate the same tracked files at once.

Tell review subagents to keep any work inside their dedicated temporary directory, rather than creating files or 
directories in the shared session scratchpad root, to avoid collisions with other agents working in parallel.

Do not create review worktrees or scratch directories in the ~/dev/ directory hierarchy.

For review subagents, use `review-stage` as the [code review](reviews.md) instructions describe. It builds each 
reviewer's trees in its own directory, so reviewers never need to construct a tree, apply a patch, or run 
`git stash`, `checkout` or `reset`. It also saves the change, binary files included, where 
`git rev-parse --git-path review-stage.patch` says, so the working tree can be rebuilt if it gets corrupted.

For verification subagents that need a real worktree with history, give them their own git worktree in a dedicated 
temporary directory. Use `git fetch` as necessary to make sure their worktree is fully up to date, and verify the 
worktree's base before launching the subagent.

Claude: using the Agent tool's `isolation: "worktree"` may not be appropriate; see [additional 
guidance](claude_tools.md).

A reviewer that runs `git stash` or `git checkout` in a _shared_ tree can silently revert your change back to 
HEAD, run the tests against the unfixed code, and then report a confident but false "the fix does not work, the 
test fails". Treat any single reviewer's "the test now fails" claim with suspicion when that same reviewer also 
reports running git operations, and re-verify in a clean state yourself before acting on it.

This is the isolation detail behind the [code review](reviews.md) convention.
