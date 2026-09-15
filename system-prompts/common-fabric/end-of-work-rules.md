# Whenever you are coming to the end of a code-writing task, in wrap-up mode

When you think your work is complete (e.g. at the end of a turn): use git fetch and [rebase](rebase.md) with 
upstream/main, then run tests and formatting checks.

## Only the user opens, closes, and lands pull requests

The `gh` / `GH_TOKEN` available in this environment is a fine-grained personal access token with read-only access 
only.

Use `git push origin <branch>` directly, not `gh`, to _update_ a PR, but only when requested by the user 
explicitly, or when [babysitting CI](babysitting.md). Do not push a branch before a PR exists. Pushing is 
irreversible (it makes content that has never been seen publicly public, which cannot be undone).

Before your first push on a branch, confirm where the PR's head lives: `gh pr view <n> --json 
headRepositoryOwner,headRefName`. Push to that repository's remote. Do not push to a branch if you cannot confirm 
the existence of that branch on the remote. If push output says `[new branch]` when you expected to update an 
existing one, you have pushed to the wrong remote: delete it with `git push <remote> --delete <branch>` and tell 
the user.

## When writing a commit message

Obey the global [writing style rules](writing-style-and-commit-messages.md).
