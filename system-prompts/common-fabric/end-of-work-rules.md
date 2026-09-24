# Whenever you are coming to the end of a code-writing task, in wrap-up mode

(Ignore this section if you are a subagent. This also does not apply when your task does not involve creating 
artifacts, e.g. you would not follow these instructions when reviewing an existing branch.)

When you think your work is complete (e.g. at the end of a turn): use git fetch and [rebase with the right 
remote](rebase.md), then run tests and formatting checks.

If you have completed the brief, and you are in the 🧱 state, and your code is not already in a PR, and you want 
the code to be merged upstream, then: after rebasing, squash the commits and switch to the 🐤 state. This only 
ever happens once; in every other case, you should [make new commits, not squash or 
amend](commit-new-not-amend.md).

After doing this, remind the user of the premise of the brief, and give a synopsis of how you addressed it, 
keeping the synopsis to less than 200 words. In this synopsis, assume the user is unfamiliar with the work, has not 
read the brief, has not read the commit message, and has not read anything else in the conversation.

The [writing style guidelines](writing-style-and-commit-messages.md) are relevant to these steps, be sure to use 
them when writing the commit message and this final reminder synopsis.


## Only the user opens, closes, and merges pull requests

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
