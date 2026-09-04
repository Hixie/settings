# When rebasing, check all the commits since you last rebased

When rebasing (or after noticing that the user has done so for you), examine all the intermediate commits to see 
if any include new instructions (e.g. changes to `.md` files), changes to related code, changes to the assumptions 
that the work was based on, etc, and adjust your work accordingly. Do not assume that merely because a rebase 
happened without merge conflicts, that it requires no updates. If the landscape has changed while work has 
progressed, it may be better to rebuild the work on the new ground than to blindly continue on the previous path.

The user will sometimes rebase your work without telling you. When pushing your work to GitHub, the user will 
typically git fetch and rebase the work first, using `~/dev/usable-git/push`. Do not be surprised when your work's 
parent commit changes. Do not rely on upstream/main being stable.

The upstream/main of a worktree will also frequently be updated in the background by other agents working on other 
worktrees that share a parent.
