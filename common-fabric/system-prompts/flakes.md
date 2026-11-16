## Flakes found while babysitting

A failure that does not seem obviously related to the PR may be a flake. You may retrigger CI using `git push 
origin <branch>` to see if the failure is transient.

When retriggering CI because of a suspected flake, you may use an empty commit, but even better is to add a new 
test to cover some previously unchecked invariant or desired behavior. Rebasing and force pushing is also a valid 
option.

While waiting for CI to rerun the test and/or for another session to fix it, run the affected test locally with 
and without the PR's change, to definitively prove that it is not related to the PR.

If you confirm that you have found an intermittent failure and that it is not caused by your own work, check if 
there is another session already dealing with that flake. If so, mention the flake to the user and indicate which 
worktree the other session is using to address the issue. If there is no other session dealing with that flake, 
find an [appropriate unused worktree](starting-new-sessions.md) for the affected [repo](identifying-worktrees.md), 
and [start a new session](starting-new-sessions.md) telling it only:

    Use REPO XX.
    Deflake <link to flaking run>

Do not give it more detailed instructions. This will guide it to use the [deflake steps](deflake.md).

If you discover your suspected flake is actually less a flake and more a production failure or red main, follow 
the "finding a failure" [red main](prodred.md) steps.

If you discover (or are informed by the deflaking agent) that your failure is specific to your branch, then it 
must be resolved in your branch before the PR can merge upstream, even if the PR sometimes manages to reach a 
condition where all the tests are passing. Create a test that reproduces the intermittent failure persistently, 
and resolve it.
