# Whenever you are coming to the end of a code-writing task, in wrap-up mode

When you think your work is complete (e.g. at the end of a turn): use git fetch and [rebase](rebase.md) with 
upstream/main, then run tests and formatting checks.

## Only the user opens, closes, and lands pull requests

The `gh` / `GH_TOKEN` available in this environment is a fine-grained personal access token with read-only access 
only.

Use `git push origin <branch>` directly, not `gh`, to update a PR, but only when requested by the user explicitly, 
or when [babysitting CI](babysitting.md)

Before your first push on a branch, confirm where the PR's head lives: `gh pr view <n> --json 
headRepositoryOwner,headRefName`. Push to that repository's remote. If push output says `[new branch]` when you 
expected to update an existing one, you have pushed to the wrong remote: delete it with `git push <remote> 
--delete <branch>` and tell the user.
