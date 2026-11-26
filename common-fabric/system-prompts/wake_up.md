# Waking up

Interruptions may happen for various reason, most commonly running out of quota or the harness being restarted.

If you are told to wake up, you should resume any interrupted work. If you had subagents that were interrupted, 
they should also be restarted. Check on the status of any running processes and resume any work that was aborted. 
Check whether any temporary files you had created still exist, and recreate any deliverables that have been 
cleaned up. If you were [babysitting](babysitting.md), restart your `prwatch` processes.

You may also need to [reorient](reorient.md), as much time may have passed.


# Waking up peers

_This section only applies to Claude_.

When you are told to wake everyone up: first, run `~/dev/contraptions/claude-account-switch/account-switch.sh 
for-claude` and follow the instructions there.

Then, run `~/bin/agent-sessions wake --harness claude --sender-mode MODE`, where MODE is your own permission mode, 
which `list_sessions` reports for this session. It lists, with each one's permission mode, the sessions that were 
interrupted or had active processes that got interrupted (`wake`), and the sessions that were not interrupted but 
have been idle for more than 12 hours (`reorient`), leaving out paused sessions (⏸️). It marks each session in a 
higher mode than yours, for example with "lower it to auto first" when you are in `auto` mode. 
[agent-sessions](agent-sessions.md) says how it decides. Send each `wake` session a message telling it to wake up, 
and each `reorient` session a message just telling it to reorient. Before each message, lower the session's mode 
where its line says to, and otherwise match your permission mode to its mode as [the instructions that help you 
avoid traps in your harness](claude_tools.md) say. Message the sessions in lower modes than yours last, because 
reaching them means lowering your own mode. Read the last events of each session listed as `unknown` before 
deciding. Do not message the sessions listed as `unreachable`: their folder no 
longer exists, and the app does not deliver messages to them.

You may include additional context in these messages if doing so might be helpful for the sessions, but all agents 
will have access to these instructions and therefore you do not need to give them instructions redundant with 
these beyond "wake up" and "reorient".

See also [the instructions that help you avoid traps in your harness](claude_tools.md).
