# Production failures and red main

## Finding a failure

If you find a production failure, or if you find a failure on main, run these steps:

1. Check the [laundry](topics.md) for any sign that someone else is already working on the issue. Do this in the 
background while continuing the following steps, as it might take some time. If you find a relevant topic, add any 
information you have collected to the topic. If you do not, file a topic describing the issue. If the topic 
clearly states that there is active work on this issue, report to the user who is doing the work, and stop these 
steps.

2. Check local agent sessions for one working on this issue. If there is one, send it a message informing it of 
the information you have found, anything relevant you found in the laundry, and then report to the user which 
session is doing the work, and stop these steps.

3. [Start a new session](starting-new-sessions.md) to work on the problem. Tell that session everything you have 
found about the issue, including anything you found in the laundry. Tell it to follow the steps below. Do not 
update the laundry to say that you have started work on it, the session itself will do that (this avoids claiming 
to be working on an issue when the work has not started). For labs sessions, prefer a worktree in the range 0-9 
(for Codex) or E0-EZ (for Claude).


## Handling a failure

If you are a session tasked to work on a production issue or a red main, run these steps:

1. Check the [laundry](topics.md) for any sign that someone else is already working on the issue. Do this in the 
background while continuing the following steps, as it might take some time. If you find a relevant topic, and it 
clearly states that there is active work on this issue, report to the user who is doing the work, and stop these 
steps. If you do not find a topic, file a topic describing the issue. At this point there must now be a topic you 
found or filed that covers the issue, which nobody has claimed they are working on: add a clear statement to the 
topic saying that you are working on it. Identify your user (for intrateam communication), session ID (for 
cross-session communication), and worktree (so that the user can identify the session). Provide that information 
on the topic. Provide your user with a link to the topic on Estuary.

2. Check local agent sessions for one working on this issue. If there is one, then send it your topic (if you have 
already completed those steps) so that it can claim ownership, then report to the user which session is doing the 
work, and stop these steps.

3. Address the issue. Whenever you make significant progress (e.g. when you are ready for the user to send a PR, 
when the user merges your PR), keep any sessions that contact you about the issue updated, and keep your topic 
updated regarding your status.
