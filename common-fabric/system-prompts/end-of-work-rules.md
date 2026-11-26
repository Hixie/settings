# Whenever you are coming to the end of a code-writing task, in wrap-up mode

(Ignore this section if you are a subagent. This also does not apply when your task does not involve creating 
artifacts, e.g. you would not follow these instructions when reviewing an existing branch.)

When you think your work is complete (e.g. at the end of a turn): use git fetch and [rebase with the right 
remote](rebase.md), then run relevant tests and formatting checks.

Reconsider whether your work touched CFC-related topics, and if so, verify that you have thoroughly [reviewed your 
work](reviews.md) in the context of the CFC specification.

If you have completed the brief and reduced the overall coverage debt of the repository, and you are in the 🧱 
state, and your code is not already in a PR, and your work is not stacked on another session's work, and you want 
the code to be merged upstream, then: after rebasing, reread the [writing style 
guidelines](writing-style-and-commit-messages.md) and [squash](commit-new-not-amend.md) the commits, writing a 
commit message that follows those rules. Then, switch to the 🐤 state. The automatic squashing only happens during 
this transition from 🧱 to 🐤; in every other case, you should make new commits, not squash or amend.

If you know you are going to squash immediately after a rebase, you may squash first then rebase.

If you do not think your work should be merged upstream, do not enter the 🐤 state. If the premise of the brief 
was incorrect, abandon the work and switch to the 💬 state, providing the user with a detailed analysis of the 
situation. If the premise of the brief was correct but the execution was a failure, [spawn a new 
session](starting-new-sessions.md) to start again, then abandon any work you created in this session and switch to 
the most appropriate state.

When you switch to the 🐤 state, reread the [writing style guidelines](writing-style-and-commit-messages.md) and, 
applying those rules, provide the user a report containing the following items, each prefixed with the given 
emoji, and each staying below the stated maximum number of words:

 📋: the premise of the brief, for an audience who has not read it and has no context (max 50 words).

 🛠️: a synopsis of how you addressed the brief; in this synopsis, assume the user is unfamiliar with the work, has 
 not read the brief, has not read the commit message, and has not read anything else in the conversation. The user 
 sees the result, not the process: report the final state, not how you got there (max 250 words).

 📐: significant design decisions, especially those that go against the original brief or other instructions (max 
 100 words).

 🍄: any parts of the brief that were not addressed, along with an explanation as to why; skip the item if there 
 are none (max 100 words).

 🐝: any open issues; skip this item if there are none (max 100 words).

 ⚠️:: any warnings about the work and its implications; skip the item if there are none (max 100 words).

 💥: any enviromental failures that you raised earlier in the conversation that have not yet been acknowledged by 
 the user (but as usual, verify that they are still salient first; for example, the user may update configuration 
 or start suggested sessions without telling you, and your harness does not inform you of such changes either); 
 skip this item if there are none (max 500 words).

 🧪: How many tests were added (max 25 words).

 ☂: The impact the branch has on the repository's coverage metrics (max 25 words).

 📌: A list of relevant [laundry topics](topics.md), if any, and any conclusions or historical context based on 
 information collected from the laundry (max 100 words).

The user does _not_ need to know about events that had no impact on the final work, for example, there is no need 
to report on a subagent's mistakes if they were resolved without harm, temporary outages that have since been 
resolved, or messages received from or sent to other sessions.


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


## Cleanup

Shut down processes you have started, including Colima, acceptance looms, toolshed dev servers, etc, if you are 
done using them and nobody else is using them.
