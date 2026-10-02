# Writing tests

## Tests should verify both the positive and the negative

When verifying that a set of inputs results in a specific output, also verify that a different set of inputs does 
not result in the first test's output.


## Tests should check the invariants and behaviors that users care about, rather than implementation details

The best tests are those that would survive a correct refactor untouched, and would catch a trivial (but 
incorrect) change.


## Test should never disrupt the user

When writing user interface tests, make sure they do not grab focus, render over active windows, or otherwise 
affect the user's interface. All of those are extremely disruptive to the user.
