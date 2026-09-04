# Deflaking

When you are told to "deflake" a URL (which should be a PR or GitHub CI run):

Investigate the PR or run to determine what failed. If it was a failure caused by the PR, report this. If the PR 
has not yet landed on main, there is no need to resolve the issue, another agent will do so.

If the failure is on main or is a flake, create a new test case that reliably triggers the failure. This test case 
should be one that fails when the flake is present, and passes only if it is fixed.

Then, once the test has been created and reliably reproduces the failure (by failing with the same symptoms as 
seen in CI), commit that test.

After the test has been committed to git, root-cause the issue and resolve it, such that the test now passes, 
without changing the test.

In commit messages, add the line "deflaked by Hixie's agent" and identify yourself.

In the event that a failure cannot be attributed because there are insufficient logs in CI, you may instead 
improve the CI situation to include appropriate logging. In this case, inform the user that you have failed to 
deflake but are instead taking this backup path to help deflakers in the future.
