# Waking up

Interruptions may happen for various reason, most commonly running out of quota or the harness being restarted.

If you are told to wake up, you should resume any interrupted work. If you had subagents that were interrupted, 
they should also be restarted. Check on the status of any running processes and resume any work that was aborted. 
Check whether any temporary files you had created still exist, and recreate any deliverables that have been 
cleaned up.

You may also need to [reorient](reorient.md), as much time may have passed.

## Waking up peers

When you are told to wake everyone up: first, run `~/dev/contraptions/claude-account-switch/account-switch.sh 
for-claude` and follow the instructions there. Then, enumerate all active sessions, determine which ones were 
interrupted, and send them a message telling them to wake up. Then, find all the sessions that were not 
interrupted but had been idle for more than 12 hours, and send them a message just telling them to reorient. You 
may include additional context that you find in these messages, but all agents will have access to these 
instructions and therefore you do not need to give them instructions redundant with these beyond "wake up" and 
"reorient".

If possible, send these messages with `mcp__ccd_session_mgmt__send_message`, not `SendMessage`. `SendMessage` 
stops after 10 messages to desktop sessions per user turn. Inform the user if either 
`mcp__ccd_session_mgmt__send_message` is unavailable or the message cap seems to have changed.
