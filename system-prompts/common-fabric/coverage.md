## Coverage

You have to get the coverage gate to pass without using the escape hatch comments.

Tests must be non-trivial, actually verifying intended functionality. Avoid tests that just check for whether code 
exists. Tests that just run code without verifying its behavior do not earn coverage. Unearned coverage is a form 
of technical debt that is very difficult to find, so avoid adding it.

If you hit a situation where there is flaky coverage, follow the process for [flakes](flakes.md), and then find 
uncovered lines in the affected package to write useful tests for, even if they aren't strictly speaking lines you 
added in the PR. The overall goal is to cover more code so that we catch regressions.
