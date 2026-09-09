# Using `prwatch` in Codex

The general approach is to use `exec_command` and then watch it using `functions.exec`:

Start `prwatch <pr> --expect HEAD --follow` using `exec_command` with `tty: true`. Retain its **session ID** and 
initial output. Start one background `functions.exec` cell with the collector script below. Retain the returned 
**cell ID**.

Keep the turn open and wait with `clock.sleep` with the longest duration supported by the tool (typically this is 
43200000ms). Notifications interrupt the wait. Handle the notifications, run the global "end of turn" steps 
(despite not actually ending the turn), then wait again. If the collector or process exits unexpectedly, restore 
monitoring before sleeping again. If restoration is blocked, report the specific blocker. Renew expired waits 
without separately checking stdout from a model turn. All output polling stays inside JavaScript.

Babysitting continues until the PR is merged or closed, or the user stops or redirects the task. Pushing a fix, 
reporting readiness, and scheduling a follow-up do not complete babysitting.

If higher-priority instructions require an automation, create it and continue the live watch. Creating an 
automation does not require ending this turn. Do not stop the collector or prwatch merely to send a final 
response.

When babysitting is complete (but not before), terminate the collector with `functions.wait({cell_id, terminate: 
true})`, and send Ctrl-C to the retained process session using `write_stdin` and the session ID, then confirm 
process exit. Cancellation of the collector does not stop `prwatch`.


Most importantly: Do not poll from model turns; use `functions.wait` only to terminate the collector.


## Javascript collector script

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
