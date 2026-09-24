# Babysitting for Codex

When you are asked to babysit a PR, perform the work in the current active conversation. Run `prwatch` as 
described below, receive its events, and address CI failures or review feedback until the PR merges, closes, or 
the user redirects you.

The running watcher provides the continuation. Keep the turn open while waiting for its events. The task’s 
duration does not itself create a need for scheduled execution.

Distinguish this from a request for another agent invocation at a future time, after this active session ends, or 
on a recurring schedule. Those requests call for automation.

Before scheduling anything, identify what future execution the schedule would provide that the active watcher does 
not already provide. Do not infer that need solely from words such as “babysit”, “watch”, or “monitor”.

If higher-priority app instructions require scheduling despite this execution model, explain the conflict 
explicitly. Distinguish that instruction requirement from a technical need for automation.


## Using `prwatch` in Codex

Use `~/dev/usable-git/prwatch` to watch a pull request. It prints one line per event and flushes each one. Do not 
pipe the output of this command through `sed` or anything else; its output is designed to be optimal for your 
needs.

The general approach is to use `exec_command` and then watch it using `functions.exec`:

Start `prwatch <pr> --expect HEAD --follow` using `exec_command` with `tty: true`. Retain its **session ID** and 
initial output. Start one background `functions.exec` cell with the collector script below. Retain the returned 
**cell ID**.

Keep the turn open and wait with `clock.sleep` with the longest duration supported by the tool (typically this is 
43200000ms -- this will be a short, bounded wait because the `prwatch` tool will interrupt the wait). 
Notifications interrupt the wait. Handle the notifications, run the global "end of turn" steps (despite not 
actually ending the turn), then wait again. 

Babysitting continues until the PR is merged or closed, or the user stops or redirects the task. Pushing a fix, 
reporting readiness, and scheduling a follow-up do not complete babysitting.

Running `prwatch` does not require ending this turn. Do not stop the collector or prwatch merely to send a final 
response.

When babysitting is complete (but not before), terminate the collector with `functions.wait({cell_id, terminate: 
true})`, and send Ctrl-C to the retained process session using `write_stdin` and the session ID, then confirm 
process exit. Cancellation of the collector does not stop `prwatch`.

If `prwatch` fails or stops, do nothing. Do not resume monitoring.


## JavaScript collector script

When using this script, substitute the **session ID** for `SESSION_ID` and the initial output for `INITIAL_OUTPUT` 
(correctly quoted and escaped as appropriate).

```js
// @exec: {"yield_time_ms": 1000}
const sessionId = SESSION_ID;
let result = { session_id: sessionId, output: INITIAL_OUTPUT };
let pending = "";
let keepContinuation = true;
const summaries = new Map();

try {
  for (;;) {
    const exited = result.session_id === undefined;
    pending += result.output;

    const lines = pending.split("\n");
    pending = exited ? "" : lines.pop();
    const output = [];

    for (const raw of lines) {
      const line = raw.replace(/\r$/, "");
      const event = line.match(
        /^\d{2}:\d{2}\s+(#\d+)\s+([A-Z][A-Z-]*)\s+(.*)$/
      );

      if (event) {
        const [, pr, tag, message] = event;
        keepContinuation = true;

        if (tag === "WATCHING" || tag === "RETARGET") {
          summaries.delete(pr);
        }

        if (tag === "STATUS" || tag === "PROGRESS") {
          keepContinuation = summaries.get(pr) !== message;
          summaries.set(pr, message);
        }
      } else if (line.trim() && !/^\s/.test(line)) {
        keepContinuation = true;
      }

      if (keepContinuation && line.trim()) output.push(line);
    }

    if (output.length || exited) {
      notify({
        type: exited ? "prwatch_exit" : "prwatch_output",
        session_id: sessionId,
        output: output.join("\n"),
        ...(exited ? { exit_code: result.exit_code } : {}),
      });
    }

    if (exited) break;

    result = await tools.write_stdin({
      session_id: sessionId,
      chars: "",
      yield_time_ms: 5000,
      max_output_tokens: 10000,
    });
  }
} catch (error) {
  notify({
    type: "prwatch_collector_error",
    session_id: sessionId,
    error: String(error),
    buffered_output: pending,
  });
}
```

If you think this script can be improved, try your improvement, then report it to the user so these instructions 
can be updated.
