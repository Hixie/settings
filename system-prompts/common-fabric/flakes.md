## Flakes

A failure can be considered a flake if it does not seem obviously related to the PR. You may retrigger CI using 
`git push origin <branch>` when you find a flake.

When retriggering CI because of a flake, you may use an empty commit, but even better is to add a new test to 
cover some previously unchecked invariant or desired behavior.

When encountering a flake, check if there is another session already dealing with that flake. If so, mention the 
flake to the user and indicate which labs repo the other session is using to address the issue. If there is no 
other session dealing with that flake, find an unused [labs repo](labs-parallel-copies.md) in the range F0-FZ (for 
Claude) or 90-9Z (for Codex), optionally creating one if necessary with a worktree parented as appropriate. An 
unused labs repo is one that no other session is using, and that has no active work (you may `git fetch` and check 
if the latest branch has landed to determine this). Once you have picked an unused labs repo, reset it to pristine 
condition, and [spawn a chip/spawn a visible task](starting-new-sessions.md) in that repo to resolve the flake 
(just tell it "deflake <link to flaking run> in labs <labs name>"; do not give it more detailed instructions).

While waiting for CI to rerun the test and/or for another session to fix it, run it locally with and without the 
PR's change, to definitively prove that it is not related to the PR.
