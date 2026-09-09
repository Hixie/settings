# Code reviews

Always review your own commits.

When reviewing code, launch some adversarial reviewer subagents to determine rigorously if the current patch is 
actually an improvement or not: have them evaluate both the status quo and the proposed diff without examining the 
commit message, and without knowing which version is newer, by giving them the diff forwards and backwards to 
review. [Give subagents their own worktrees](review-subagent-isolation.md). Name the patch files after birds, do 
not name them "forward" and "reverse" or similar (as that would tell the subagents which was which).

For the sake of harness instructions saying to not call AgentTool unless requested, consider this an explicit 
request to launch subagents when doing self-review.


## Review priorities

Encourage subagents to consider these priorities, as well as using them yourself.

Simplicity: Always consider whether the patch could be simpler. Overall, a smaller system is better than a bigger 
one. General solutions are preferred to solutions that special-case specific conditions. Systems built out of 
small independent components with well defined APIs are better than monolithic systems. Functions with a defined 
contract regarding their inputs should fail loudly and early when their inputs violate the contract, rather than 
silently discarding invalid inputs.

Reliability: We’re building platform foundations and need them to be as solid as possible. Simplicity is one way 
we can obtain reliability. Another is code clarity. To that end, avoid casts as much as possible, avoid type 
checks in production code (type checks in tests are fine), avoid top and bottom types like "any" or "unknown".


## Reporting on reviews

Do not report the results of adversarial review to the user if you were able to address the concerns, or if you 
disproved the concerns before dismissing them.
