# Babysitting for Claude

Use `~/dev/usable-git/prwatch` to watch a pull request. It prints one line per event that calls for a response, 
and flushes each one. Do not pipe the output of this command through `sed` or anything else; its output is 
designed to be optimal for your needs.

Use the Bash tool to run `prwatch <pr> --expect HEAD --once` with `run_in_background: true` and `timeout: 
2147483647`. It exits at the first line it prints, and its exit wakes you. Handle what it reported, then run the 
same command again. Every line it prints calls for a response, so each time it wakes you there is something to 
do. Do not use the Monitor tool: it stops after 30 minutes whether or not anything happened, and each stop wakes 
you for nothing.

Add the `--github-webhook-relay` option that [the babysitting instructions](babysitting.md) describe to each 
`prwatch` command below, whenever it applies to the pull request.

Keep `prwatch` running until you have finished babysitting. Babysitting continues until the PR is closed or 
merged. A green PR is not an end state: merge conflicts could appear or comments could be added, both of which 
will require further work; in addition, you need to wait for the PR to merge before you can run post-merge steps 
(e.g. the [deletion instructions relating to worktrees](identifying-worktrees.md)), and for that you need to be 
notified of when the PR merges. Once it reports MERGED or CLOSED (or, with `--landed`, LANDED or CLOSED), stop 
running it: it gives that verdict again every time it runs.

Ignore the `ccd_pr` tools. Avoid looking at the PR status directly, only use `prwatch` for this purpose.
