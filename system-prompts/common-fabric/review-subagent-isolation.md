# Give review and verification subagents their own worktree

When you spawn review or verification subagents — especially general-purpose ones that may run `git checkout`, 
`git stash`, `git apply`, or execute tests — give them their own git worktree (the Agent tool's `isolation: 
"worktree"`). Running them in the shared working directory lets several of them mutate the same tracked files at 
once.

Stage any before/after files explicitly for the reviewers, do not rely on their ability to construct the tree. Use 
`git fetch` as necessary to make sure their worktree is fully up to date.

A reviewer that runs `git stash` or `git checkout` in a _shared_ tree can silently revert your change back to 
HEAD, run the tests against the unfixed code, and then report a confident but false "the fix does not work, the 
test fails". Treat any single reviewer's "the test now fails" claim with suspicion when that same reviewer also 
reports running git operations, and re-verify in a clean state yourself before acting on it.

Before launching reviewers, save an authoritative `git diff` of the change to a scratch file so the working tree 
can be rebuilt if it gets corrupted.

This is the isolation detail behind the [code review](reviews.md) convention.
