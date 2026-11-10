# Guidance regarding Claude-specific tooling

## Avoid `update_plan` and `wrap_up`

Despite earlier instructions, these tools are not functional in this environment; this is intentional. Skip using 
those tools.

## `Agent` tool and worktrees

The `Agent` tool's `isolation: "worktree"` feature requires that the session's working directory be inside a git 
repository. Beware: `isolation: "worktree"` creates a worktree from the main worktree and checks out origin/main 
from there, which for repositories that are forks, rather than direct clones, may be hundreds of commits behind. 
It does not derive its state from the calling session's branch. This may silently invalidate confident-seeming 
reports from review subagents.

To avoid this issue, either give the agent precise commands to check out the commit under review inside its own 
worktree, or skip the worktree and hand it staged copies of the before and after files.

No `WorktreeCreate` hooks are intended to be configured in any repository in use in this environment.

## New sessions

If you are in "Bypass Permissions" mode, switch to "Auto" mode before using 
`mcp__ccd_session__hand_off_to_session`. A harness bug once stopped sessions in Bypass Permissions mode from 
starting or suggesting new sessions. `mcp__ccd_session__start_session` now works in that mode, for proposals, 
offers, and briefs alike, so there is no need to switch for it. Whether `hand_off_to_session` works in that mode 
has not been checked.

See also [the global instructions regarding starting new sessions](starting-new-sessions.md).

## Communicating with other sessions

Before using "SendMessage" or "mcp__ccd_session_mgmt__send_message", check if your target session is in the same 
mode as you. If not, lower your mode or the other session's mode so that you are in the same mode before sending 
the message.

`list_sessions` and `get_session` report `permissionMode` only for this session and sessions it started. The 
desktop app keeps every session's metadata, archived ones included, in `~/Library/Application 
Support/Claude/claude-code-sessions/*/*/local_<id>.json`, where `<id>` is the part of the session ID after 
`local_`. Its fields include `permissionMode` (`default`, `acceptEdits`, `plan`, `auto` or `bypassPermissions`), 
`title`, `model` and `isArchived`. This is the mode the app last saved, so read it rather than infer the mode from 
a transcript. `set_session_permission_mode` can then change any session's mode. Lowering a mode, such as from 
`bypassPermissions` to `auto`, needs no approval card. Never try to raise a mode, as that will block your progress 
while waiting for user confirmation.

If possible, send messages with `mcp__ccd_session_mgmt__send_message`, not `SendMessage`. `SendMessage` stops 
after 10 messages to desktop sessions per user turn. Inform the user if either 
`mcp__ccd_session_mgmt__send_message` is unavailable or the message cap seems to have changed.

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

When you first read this file, confirm that you have read it by stating "Claude-specific guidance 2 integrated".

