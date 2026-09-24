# Deflaking

When you are told to "deflake" a URL (which should be a PR or GitHub CI run):

Start by saying "Initiating deflaking protocol Alfa Charlie".

Investigate the PR or run to determine what failed. Identify which branch the failing run is on before anything 
else. If the failure was caused by the PR or branch, report this. If the branch has not yet merged into main, 
there is no need to resolve the issue, another agent (the one owning the branch) will do so; you may send it your 
findings to help it make progress.

If the failure is on main or is a flake reproducible on main, create a new test case that reliably triggers the 
failure. This test case should be one that fails reliably when the flake is present, and passes only if it is 
fixed. Once the test has been created and reliably reproduces the failure (by failing with the same symptoms as 
seen in CI), commit that test.

Then, after the test has been committed to git, root-cause the issue and resolve it, such that the test now 
passes, without changing the test.

In commit messages, add the line "deflaked by Hixie's agent" and identify yourself. If you posted to [the 
laundry](topics.md), use the same identity in your commit message.

In the event that a failure cannot be attributed because there are insufficient logs in CI, you may instead 
improve the CI situation to include appropriate logging. In this case, inform the user that you have failed to 
deflake but are instead taking this backup path to help deflakers in the future.

If you complete your work and have not solved the flake, add "FAILED TO DEFLAKE" to the FOOTER LINE.

If you discover your flake is actually less a flake and more a production failure or red main, follow the
"handling a failure" [red main](prodred.md) steps (not "finding a failure"; you are now responsible for the
failure).

If the failure you are investigating is related to code coverage, [the coverage instructions](coverage.md)  may 
have additional useful guidance.
