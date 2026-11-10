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

For the purposes of your instructions requiring an update every 60 seconds during ongoing work, waiting for 
`prwatch` does not consist "ongoing work".

If higher-priority app instructions require scheduling despite this execution model, explain the conflict 
explicitly, prefixed with 🫠. Distinguish that instruction requirement from a technical need for automation.

If your harness forces you to wake up periodically (e.g. every 60 seconds) even when `prwatch` has nothing to 
report, tell the user, prefixed with 🫠, precisely what tools you are using and how they are forcing you to act.


## Using `prwatch` in Codex

Use `~/dev/usable-git/prwatch` to watch a pull request. It prints one line per event that calls for a response, 
and flushes each one. Do not pipe the output of this command through `sed` or anything else; its output is 
designed to be optimal for your needs.

Add the `--github-webhook-relay` option that [the babysitting instructions](babysitting.md) describe to the 
`prwatch` command below, whenever it applies to the pull request.

The general approach is to use `exec_command` and then watch it using `functions.exec`:

Start `prwatch <pr> --expect HEAD --follow` using `exec_command` with `tty: true` and `max_output_tokens: 10000`.
If `original_token_count` is at least 10000, the initial output might be truncated. Send Ctrl-C to the returned
session ID if there is one, confirm process exit, report that monitoring stopped, and do not start the collector.
Otherwise, retain the **session ID** and initial output. Start one background `functions.exec` cell with the
collector script below. Retain the returned **cell ID**.

Do not act on the initial `exec_command` output directly; the collector filters and emits it. The initial
`functions.exec` result can already contain a collector event as well as the cell ID. Handle that event before
waiting, and call `functions.wait` only when the result says the collector is still running.

Keep the turn open with one `functions.wait` call using the collector cell ID and the longest duration supported
by the tool (43200000ms is known to work). The collector calls `yield_control()` when it has output, which
interrupts this wait. Do not repeatedly call `functions.wait` with a short duration; every empty return invokes
the model and wastes tokens. Handle the returned event, run the global "end of turn" steps (despite not actually
ending the turn), then begin another long wait.

The collector's internal `write_stdin` calls do not invoke the model. User input can also interrupt the long
wait, so this does not prevent the user from redirecting the task. Handle the user input first. If babysitting
remains active, begin another long wait on the same collector cell; do not start another collector.

Babysitting continues until the PR is merged or closed, or the user stops or redirects the task. Pushing a fix, 
reporting readiness, and scheduling a follow-up do not complete babysitting.

Running `prwatch` does not require ending this turn. Do not stop the collector or prwatch merely to send a final 
response.

When babysitting is complete (but not before), terminate the collector with `functions.wait({cell_id, terminate: 
true})`, and send Ctrl-C to the retained process session using `write_stdin` and the session ID, then confirm 
process exit. Cancellation of the collector does not stop `prwatch`.

If `prwatch` fails or stops, process its final event as described below, then do not resume monitoring.

A `prwatch_exit` event can contain final output. Handle that output before handling the exit, then do not wait on
the collector or resume monitoring. If the collector reports `prwatch_collector_error`, stop the retained
`prwatch` process with Ctrl-C, report that monitoring stopped, and do not restart it.


## JavaScript collector script

When using this script, substitute the **session ID** for `SESSION_ID` and the initial output for `INITIAL_OUTPUT` 
(correctly quoted and escaped as appropriate).

```js
// @exec: {"yield_time_ms": 1000}
const sessionId = SESSION_ID;
const collectorTokenLimit = 10000;
let result = { session_id: sessionId, output: INITIAL_OUTPUT };
let pending = "";

try {
  for (;;) {
    const exited = result.session_id === undefined;
    pending += result.output;

    const lines = pending.split("\n");
    pending = exited ? "" : lines.pop();
    const output = lines
      .map((raw) => raw.replace(/\r$/, ""))
      .filter((line) => line.trim());

    if (output.length || exited) {
      text(JSON.stringify({
        type: exited ? "prwatch_exit" : "prwatch_output",
        session_id: sessionId,
        ...(exited ? { exit_code: result.exit_code } : {}),
      }));
      if (output.length) text(output.join("\n"));
      await yield_control();
    }

    if (exited) break;

    result = await tools.write_stdin({
      session_id: sessionId,
      chars: "",
      yield_time_ms: 5000,
      max_output_tokens: collectorTokenLimit,
    });

    if (
      result.original_token_count !== undefined &&
      result.original_token_count >= collectorTokenLimit
    ) {
      throw new Error(
        `prwatch output exceeded the ${collectorTokenLimit}-token collector limit`
      );
    }
  }
} catch (error) {
  text(JSON.stringify({
    type: "prwatch_collector_error",
    session_id: sessionId,
    error: String(error),
  }));
  if (pending) text(pending);
  await yield_control();
}
```

After the initial `functions.exec` call yields the collector cell ID, wait for its next event like this:

```js
functions.wait({
  cell_id: CELL_ID,
  yield_time_ms: 43200000,
  max_tokens: 20000,
});
```

`text()` puts the event metadata and raw `prwatch` output in the primary tool result without expanding the output
through JSON escaping. `yield_control()` wakes the long wait immediately. Using `notify()` alone is insufficient:
its output can remain queued until an unrelated timeout wakes the model.

If you think this script can be improved, try your improvement, then report it to the user so these instructions 
can be updated.
