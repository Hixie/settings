# Babysitting for Claude

Use `~/dev/usable-git/prwatch` to watch a pull request. It prints one line per event and flushes each one. Do not
pipe the output of this command through `sed` or anything else; its output is designed to be optimal for your
needs.

The Monitor tool turns each line into a notification; use it to run `prwatch <pr> --expect HEAD --follow`, with 
`timeout_ms` set to the maximum (`1800000`).

After 30 minutes, the Monitor tool exits. At that point:

- If you are still actively working (e.g. resolving feedback, fixing tests, etc), or if the `prwatch` has given 
you multiple updates since you last launched it, then re-arm the Monitor tool and continue.

- Otherwise, instead of re-arming the Monitor tool, use the Bash tool to run `prwatch <pr> --expect HEAD --once` 
with `run_in_background: true`. This will avoid waking you until the next time there is an event.

Ignore the `ccd_pr` tools.
