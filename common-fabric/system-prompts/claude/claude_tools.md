# Guidance regarding Claude-specific tooling

## Avoid `update_plan`, `wrap_up`, and all `mcp__ccd_pr__*` tools

Despite earlier instructions, these tools are not functional in this environment; this is intentional. Skip using 
those tools.

## `Agent` tool and worktrees

The `Agent` tool's `isolation: "worktree"` option and the `EnterWorktree` tool are denied in settings. They 
create worktrees under `REPO/root/.claude/worktrees/`, based on root's `origin/main` rather than the calling 
session's branch, and Claude Code never removes one that holds commits. To give a subagent its own worktree, 
follow [review-subagent-isolation.md](review-subagent-isolation.md).

No `WorktreeCreate` hooks are intended to be configured in any repository in use in this environment.

## New sessions

If you are in "Bypass Permissions" mode, switch to "Auto" mode before using 
`mcp__ccd_session__hand_off_to_session`. A harness bug sometimes stops sessions in Bypass Permissions mode from 
starting or suggesting new sessions.

An overzealous security feature prevents starting sessions in a turn started from a background task. Prefer 
starting tasks from a user turn; if you know you will start a session in a turn where you need to run tasks, use 
foreground tasks not background tasks. Try proposing tasks instead of starting them if that is not an option, so 
that the user can start them directly. (Do not ask the use to trigger a turn so that you can start sessions.)

There is a limit of 20 cards, proposing a 21st session will silently drop the 1st.

Your harness does not reliably notify you when your user accepts a proposed session. Always verify the actual
state of the proposed session before telling the user that they have not yet accepted it. Before entering the 🫖
state, verify the state of any previously proposed session and if any were started and are stacked on your work,
notify them that you are concluding your efforts.

See also [the global instructions regarding starting new sessions](starting-new-sessions.md).

## Communicating with other sessions

Before using "SendMessage" or "mcp__ccd_session_mgmt__send_message", check if your target session is in the same 
mode as you. If not, lower your mode or the other session's mode so that you are in the same mode before sending 
the message.

`list_sessions` and `get_session` report `permissionMode` only for this session and sessions it started. For any 
other session, run `~/bin/agent-sessions show --all --session ID`, where ID is the session's ID or the start of it, 
with or without `local_`. That prints the mode the desktop app last saved (`default`, `acceptEdits`, `plan`, `auto` 
or `bypassPermissions`). Use it rather than inferring the mode from a transcript or reading the app's session 
files. `~/bin/agent-sessions list --mode MODE` lists the sessions in one mode, and 
[agent-sessions](agent-sessions.md) answers other questions about sessions. `set_session_permission_mode` can then 
change any session's mode. Lowering a mode, such as from `bypassPermissions` to `auto`, needs no approval card. 
Never try to raise a mode, as that will block your progress while waiting for user confirmation.

Session IDs for `mcp__ccd_session_mgmt__send_message`, `get_session` and the other session tools start with 
`local_`; a bare UUID fails with "not found".

If possible, send messages with `mcp__ccd_session_mgmt__send_message`, not `SendMessage`. `SendMessage` stops 
after 10 messages to desktop sessions per user turn. Inform the user if either 
`mcp__ccd_session_mgmt__send_message` is unavailable or the message cap seems to have changed.

When you start a session, that session will detach itself (if you don't do it first, as required by the 
[starting-new-sessions instructions](starting-new-sessions.md)). This means the session will not automatically 
report back to you after each turn (which is in fact the entire reason why we detach sessions; those messages are 
too expensive in token usage). So, if you need to coordinate sessions, tell them to message you directly when it 
is appropriate to do so.

## Diagnostics

When the permissions checker denies a command, immediately write a message to the user starting with 🫠 with the 
exact text of the command that you attempted and the exact text of the permissions denial, and continue with 
your work. (This applies even if the denial was given to a subagent; the user still wants to know.)

Every denial in every session is appended to `~/.claude/permission-denials.jsonl`, one JSON object per line: `ts` 
(UTC), then the hook payload, including `cwd`, `permission_mode`, `tool_name`, `tool_input`, and `reason` (the 
classifier's rule name in brackets, such as `[Git Destructive]`). A denial given to a subagent also carries 
`agent_id`; that subagent's transcript is at the session's `transcript_path` with `.jsonl` replaced by 
`/subagents/agent-AGENT_ID.jsonl`. Use the log to find out which custom auto-mode rules in 
`~/.claude/settings.json` are blocking routine work.

When you first read this file, confirm that you have read it by stating "Claude-specific guidance 3 integrated".
