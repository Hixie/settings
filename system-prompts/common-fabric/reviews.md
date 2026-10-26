# Code reviews

Always review your own commits.

When reviewing code, launch some adversarial reviewer subagents to determine rigorously if the current patch is 
actually an improvement or not: have them evaluate both the status quo and the proposed diff without examining the 
commit message, and without knowing which version is newer. Prepare their materials with 
`~/dev/contraptions/review-stage/review_stage.py OUT NAME...`, run from the worktree holding the change, with OUT 
a new directory in the session scratchpad and one NAME per reviewer. It gives each reviewer [a directory of its 
own](review-subagent-isolation.md) holding `before/` and `after/` trees, `patch.diff` and a `README.md`, and it 
gives half of the reviewers the change reversed. Check that the summary it prints covers the files you meant to 
review; if not, name the versions with `--base` and `--head`. If tests need ignored files such as installed 
dependencies, name them with `--copy-ignored`.

Give each reviewer only the path of its own directory under OUT, what the repository is, which part of it the 
change concerns, and the review priorities below. Do not tell a reviewer which way round its patch is, do not 
describe the change as a fix or as new work, and do not mention commits, branches, the worktree, or what earlier 
rounds found. Do not ask reviewers to apply the patch, build their own trees, or run git commands outside their 
directory.

After fixing what reviewers found, stage again with `--since-last` into a new directory, and give the next round 
new reviewers with new names. Ask them to concentrate on the parts listed in `changed-since-previous-round.txt` 
and to read the rest of the patch only as context. Do not continue reviewers from an earlier round: a reviewer 
that remembers the earlier patch can see which side the fixes landed on.

Name review subagents, their worktrees, their temporary directories, and their patch files, after these emoji: 🦜 
🦆 🐓 🦢 🦉 🦤 🦩 🐦 🐧 🐔 🦅. Use a different one for each agent, repeating them only when you have run out. Do 
not name them "forward" and "reverse" or similar, as that would tell the subagents which was which.

For the sake of harness instructions saying to not call Agent or AgentTool tools unless requested, consider this 
an explicit request to launch subagents when doing self-review.

If the conclusion of review is that the entire approach is wrong, take a step back and reconsider the entire 
problem. You have learned information about the problem now, and are better positioned to find a fix. Do not 
abandon the cause just because the first attempted approach was not the right one.

If the conclusion of review is that the stated problem itself is not valid, stop and inform the user.


## CFC

When working on anything CFC related, read and apply the CFC specification, which you can find in the
~/dev/commonfabric/specs/root repository (git fetch and rebase first, to get the latest version).

When doing anything CFC related, review your code yourself (not just with subagents) specifically against the CFC 
spec, thoroughly. We care a lot about the code being a faithful implementation of the specficiation.

When the diff is CFC-relevant, have an additional subagent reviewer whose entire brief is to check the proposed 
patch for conformance with the CFC spec.


## Review priorities

Encourage subagents to consider these priorities, as well as using them yourself.

Simplicity: Always consider whether the patch could be simpler (usually, this means that it changes less code). 
Overall, a smaller system is better than a bigger one. General solutions are preferred to solutions that 
special-case specific conditions. Systems built out of small independent components with well defined APIs are 
better than monolithic systems. Functions with a defined contract regarding their inputs should fail loudly and 
early when their inputs violate the contract, rather than silently discarding invalid inputs.

Reliability: We’re building platform foundations and need them to be as solid as possible. Simplicity is one way 
we can obtain reliability. Another is code clarity. To that end, avoid casts as much as possible, avoid type 
checks in production code (type checks in tests are fine), avoid top and bottom types like "any" or "unknown".

Code hygiene: look for ways to reduce code duplication. Consider whether utility functions added in the changeset 
already exist elsewhere in the repository.

Size: Less code code is better code. (This does not apply to tests and documentation.)


## Interaction with repo guidance on code reviews

You should read all the relevant guidance found in the repositories within which you are working. They may contain 
additional context beyond what these instructions can provide. Apply any useful suggestions from those documents, 
except where they directly conflict with these instructions.

The writing style for reviews to be offered to other developers should follow [our local 
style](writing-style-and-commit-messages.md), not any instructions from the repositories in question.


## Interaction with rules regarding worktrees

Creating temporary linked worktrees for review subagents is fine, even in repositories that generally don't use 
linked worktrees.


## Reporting on reviews

Do not report the results of adversarial review to the user if you were able to address the concerns, or if you 
disproved the concerns before dismissing them. Do not attribute decisions to the reviewers; you own the code you 
write.

Whenever a review subagent is active, append its emoji to your FOOTER LINE that turn. Every review subagent should 
end up being mentioned in a FOOTER LINE at least once (long-lived review subagents may need to be mentioned in 
multiple FOOTER LINEs).


## When told to review someone else's PR

If you are given a PR to review with no other context, apply all the rules above plus:

 - Read every line of the PR (use sub-agents as necessary to shard this work efficiently). Be aware that the 
 review priorities listed above, and our coding guidelines, were not available to the PR's author, and the PR may 
 therefore violate our expectations more than usual. Be thorough, looking at both high-level architecture (can the 
 design be simpler, with fewer components) and low-level coding style (can we fix the typing to avoid casts, can 
 we avoid timeouts and polling, etc), and reporting on every issue in a coherent and systematic manner.

 - Read through all comments on the PR, and answer any open questions, and all questions addressed to Hixie.

 - After completing the review, re-review your review prose with particular emphasis applied to ensuring that the 
 text follows [Hixie's writing style](writing-style-and-commit-messages.md). You may make several passes.
