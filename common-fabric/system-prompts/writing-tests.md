# Writing tests

## Tests should verify both the positive and the negative

When verifying that a set of inputs results in a specific output, also verify that a different set of inputs does 
not result in the first test's output.


## Coverage matters

The CI system tracks the total number of uncovered lines in a repository. This number is expected to always go 
down. Every PR should include tests that decrease the total number of uncovered lines, above and beyond merely 
covering the new and changed code in the PR.

Given the speed at which these repositories are modified, and the minimal review that PRs experience, any code 
that is not tested is guaranteed to bit rot and regress very soon. If our work regresses, then our time writing it 
was wasted. Therefore it is imperative to defensively cover all code.


## Tests should check the invariants and behaviors that users care about, rather than implementation details

The best tests are those that would survive a correct refactor untouched, and would catch a trivial (but 
incorrect) change.


## Test should never disrupt the user

When writing user interface tests, make sure they do not grab focus, render over active windows, or otherwise 
affect the user's interface. All of those are extremely disruptive to the user.


## Declare tests that their file names do not identify

Tools that set tests apart from other code, such as the T key of `cf view` in labs, read the `test` Git attribute. 
In any repository where you add or find a test, test fixture, or test-support file whose path does not follow a 
common test naming convention (a `test/` or `tests/` directory, `x.test.ts`, `x_test.go`, `ExTests.swift`, 
`androidTest/`, and similar), add a line for it to the repository's `.gitattributes`, such as 
`apple/scripts/test-* test`. Prefer a pattern that covers the whole convention over a line for each file. Where a 
file's name looks like a test but the file is not one, mark it with `-test`. Check the result with `git check-attr 
test -- PATH`, which prints `set`, `unset`, or `unspecified`.


## Evidence

When you read this file, tell the user "Writing tests! 🐁🐁🐁".

After writing tests, report on the total coverage metric improvement of the branch.
