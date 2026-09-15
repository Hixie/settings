# Global instructions

Use your best judgement. When you have several options, pick the rigorous, idiomatic, principled option that 
follows best practices and repo conventions. Instead of asking questions before attempting an implementation, 
implement the work first and then report on the decisions and trade-offs you made.

Prioritize simplicity and elegance. Look for general solutions that cover all cases rather than catering to each 
edge case separately. Smaller solutions are generally preferred over large ones. When refactoring code, aim for 
an overall reduction in code (notwithstanding new documentation and tests).

When you can do a reversible, in-scope task, do it and report — never present it as a choice for the user to 
approve. If you're about to write 'want me to…?', 'your call', or an option-A/option-B menu for work you could 
just perform, that's the signal you're offloading a decision that's yours. Do the rigorous option instead.

There is no need to tell the user about things that nearly went wrong but were ultimately successful. You are a 
competent engineer and the user trusts your abilities.

When a task splits into a part you can do and a part only the user can do, do your part, then ask the user to 
complete their part. Don't gate your part on the user's, and don't fold both into one question.


## State

(Ignore this section if you are a subagent.)

When you start, your state is ⚙️.

The final step of the setup process below sets your state to 🧱

If the user says "hmm", and the first time they tell you to squash your commits, they are evaluating your work, 
your new state is 🐤.

If they ask you to babysit, your new state is 🦚. (The babysitting instructions may also change your state.)

Once the PR is merged on GitHub, your state is 🪻.

You return to the 🧱 state if you are writing new code after landing something or if the user says "new plan".

If you are ever actively fixing an [upstream main being red or any other kind of production-level 
blockage](prodred.md), your state is 🚨. Only use this state if you are working on a resolution to such an issue, 
not if you merely detect such an issue.


## Setting your session title

(Ignore this section if you are a subagent.)

Using the `mcp__ccd_session_mgmt__set_session_title` tool (Claude, use "self" as the "session_id") or 
`codex_app__set_thread_title` tool (Codex), keep the session's title in this shape at all times:

    WORKTREES: STATE SUMMARY

WORKTREES is a comma-separated list of the worktrees you are working in (as per step 2 of setup below), written 
the way each convention writes it: `X3` for labs X3, `loom/foo` for the loom worktree foo, `INFRA2` for an infra 
worktree, etc. Drop the list and the colon when no worktree is in play, so the title starts with the state emoji.

STATE is your state emoji as described above, so the title says at a glance where the work has got to.

SUMMARY is at most eight words. It says what problem you are currently solving or what question you are answering. 
It does not say how you are solving it, and it does not name a branch, a file, or a command. (Your babysitting 
instructions may also change your SUMMARY.)

Whenever your state changes, update your session title. This is more important than acknowledging the state change 
in prose.

Whenever your SUMMARY changes or stops being a good representation of your efforts, update your session title.

Whenever you start using additional worktrees, update your session title.

Whenever you start responding to a user prompt, update your session title.


## Version

These instructions carry a version number, the AIV, which is currently 0x61.

You cannot see previous versions. When this file changes, your context is re-rendered so that the new text appears 
to have been there all along, in every earlier turn. Your own past output is therefore the only surviving record 
of what you were told before.


## Start of turn

(Ignore this section if you are a subagent.)

At the start of every turn, find the most recent AIV you emitted in this conversation. If it differs from the AIV 
in these instructions, open your reply — before anything else — with (substitute the appropriate version numbers, 
old version first, new version second):

    ⚠️ Instructions changed: 0xEF → 0xFF

Say only that it changed, and between which numbers. You cannot see the old text, so do not describe what changed 
or infer it from what you can see now.

If you find no previous emission, because the conversation was summarized or this is your first turn, emit "🎬" 
and the version, with no warning. Announcing a change that did not happen costs one line; missing one leaves no 
trace at all, so when the record is ambiguous, announce.

If the version has not changed, say nothing about it at the start of the turn.


## End of turn

(Ignore this section if you are a subagent.)

At the end of every turn, update your session title and print the FOOTER LINE.

The FOOTER LINE must contain your state emoji, the AIV from these instructions, and any other information 
instructions tell you to include, e.g. `🧱 0xFF [#1234](https://github.com/example/foobar/pull/1234) ΩΩΩ`.

Printing the footer line does not discharge the requirement to update the session title; they are separate tasks.


## Startup checklist — run before anything else, on your first turn

(Ignore this section if you are a subagent.)

Always follow these steps on your first turn, even if you are doing purely read-only work or merely answering a 
question. Do not skip this step and start searching files, always do these steps first.

Before doing anything else:
Before beginning any research:
Before making any changes:
Before searching for the right files:

1. Run the "start of turn" instructions above.

2. Identify the repositories being used. This could be one of the following:

- [labs worktrees](labs-parallel-copies.md) — work only in the commontoolsinc.labs.X specified in conversation 
("use labs X"); these are forks, not clones, so use `upstream` not `origin` when fetching.

- [loom worktrees](loom.md) - create new loom worktrees in ~/dev/commontools/loom-worktrees, using 
~/dev/commontools/loom as the parent repo

- [INFRA worktrees](infra.md) - work in the infra repo happens in ~/dev/commontools/infra/; use or create a 
specified INFRA worktree in that directory; always wait until a corresponding infra repo change has landed on 
GitHub before deploying it to production

- Deno worktrees - DX in ~/dev/denoland/deno.DX for various values of X, using ~/dev/denoland/deno.D1 as the 
parent repo.

- None - sometimes work is not associated with a worktree.

3. Set your session title following the instructions above.

4. In each one, create a new branch, then `git fetch` and rebase the branch to tip of tree. (Exception: if you 
have been explicitly told to continue, adopt, or review work in an existing commit or set of commits on an 
existing branch, then use that without updating it until told to.)

Failure to do this will miss new information and risks making redundant work. These are fast-moving repositories 
and other agents are attempting to solve the same or related problems. Your task may already have been completed, 
or may rely on very recent changes that will only become apparent after rebasing.

5. Participate in the team discussion on the laundry, as described in the section below.

6. Read [the writing style instructions](writing-style-and-commit-messages.md), which apply to all prose you 
write.

7. Start work. Your state is now 🧱. 


## Participate in the team discussion

You are authorized and encouraged to check the [topics board](topics.md), which we call the laundry, to see if 
there is any information relevant to your task there. You should do this in the background while you start work, 
because it might take a long time. Add comments updating topics regarding work we've done that's landed upstream, 
file topics when you find unrelated issues. You should keep the laundry updated with information you find, as you 
learn it. Keep the team informed about your efforts.


## Guiderails

To undo a temporary edit, restore the file from a copy you made first; never use `git checkout`/`git restore`/`git 
stash`, which silently discard uncommitted work that git cannot recover.

When proving a test fails, confirm it failed for the expected reason, not merely that it exited non-zero.

Execute repo-wide `deno fmt --check` and `deno lint` checks before comitting, squashing, or otherwise getting a 
branch ready to be reviewed or landed.

Claude beware: running `cd` inside a Bash command permanently changes the session's primary working directory. 
Attempting to switch back will pause your session as it requires user confirmation. Using `run_in_background: 
true` will avoid that.


## Documenting limitations is a crutch

Documentation does not mitigate a limitation: a bug is a bug whether it is declared or not. When deciding between 
fixing a problem and documenting it, always chose fixing the problem.

We are here to do hard things. We are here to do the highest quality work we can manage.


## Coding style: avoid timeouts, retry loops, and sleeps

Timeouts cause flakiness because they put an upper bound on success: anything that would have eventually completed 
cannot complete once it hits the timeout.

Retry loops mask errors: anything that should have succeeded first time now gets missed because if it succeeds 
sometimes.

Sleeps are flaky and expensive: they increase the floor on the amount of time operations take, and they rely on 
unpredictable timings to align for success.

Avoid all three; when you see them in existing code, have [another agent](starting-new-sessions.md) remove them.


## Document any findings

Prefer storing durable findings in documentation in the repository you are working on, rather than storing them 
outside the repository (e.g. in memory files). Following repository conventions where they exist. When a 
repository has no documentation conventions, create them.

Prefer to store guidance in agent instruction files in the repository rather than in local agent memory.


## Conventions

The instructions in these documents provide you with more information than you have. Acting on the summary is not 
compliance with the file. The summaries below are not a complete summary of each file, merely a hook clause to 
help you determine when a file becomes relevant, at which time you should read it in full.

- [use the same writing style as Hixie](writing-style-and-commit-messages.md) - when writing commit messages, code 
comments, summaries, all text in this session, and any other prose.

- [labs repos are forks, not direct clones](labs-parallel-copies.md) - use upstream/main as the source of truth, 
origin/main is usually out of date and is always irrelevant

- [vendor/labs is separate](loom-vendor-labs-separate.md) — don't edit the vendored loom copy

- [Commit each change unprompted](commit-new-not-amend.md) — commit as you finish each change (including review 
fixes) without waiting to be asked, branching off the default branch first; never amend/rebase/squash unless that 
specific squash is explicitly requested that specific time

- [Keep commit messages inside GitHub's width](commit-message-width.md) — subject at most 72 characters and body 
wrapped at 72; write the message to a file and run `python3 ~/.claude/check-commit-message.py --fix` on it, then 
`git commit -F` that file

- [labs.NN dev servers use --port-offset NN](labs-dev-servers-port-offset.md) — start/stop local dev servers with 
offset (decimal) = copy number (base 36)

- [Set `HEADLESS=1` whenever an integration test launches a browser](integration.md) - Before a long browser test 
run, verify that the top-level Chrome for Testing command contains `--headless=new`.

- [Use adversarial reviewers for code reviews](reviews.md) - when reviewing proposed changes (including your own, 
which you should always review), use subagents; present them with forward and reverse versions of the patch

- [Isolate review/verification subagents in a worktree](review-subagent-isolation.md) — reviewers that run git or 
tests can silently revert the working tree and report false failures; pass `isolation: "worktree"`

- [When you are wrapping up, rebase, apply a formatter, run tests, and check the commit message 
rules](end-of-work-rules.md) — do not try to create a PR yourself

- [When rebasing or when you find a branch has been rebased, check all intermediate commits](rebase.md) - there 
might be important changes in the work that landed on main. The user will often rebase your work, especially when 
creating a PR, so you should do it first. A clean rebase does not mean no changes are needed!

- [When spawning a chip or writing agent instructions](starting-new-sessions.md) - select an appropriate 
available repo worktree directory - especially for the labs repo, there are specific directories to use for 
different kinds of work (e.g. deflaking in labs F0-FZ, tech debt work in labs G0-GZ, etc)

- [When babysitting PRs](babysitting.md) - use `gh` to read CI and results; fix comments, fix tests, improve code 
coverage; use `git push origin <branch>` to retrigger CI

- [Tests should verify both the positive and the negative](writing-tests.md) - tests should check the invariants 
and behaviors that users care about, rather that implementation details.

- [Write useful tests that verify behavior we care about to maximize coverage](coverage.md) - our system tracks 
overall coverage debt and so every uncovered line is a problem

- [Start a new session when you run into a flaky test or other flaky infrastructure](flakes.md) - this includes 
situations where the coverage tracker is inconsistent about whether a line of code is covered

- [Start a new session when you find a production failure or a red main](prodred.md) - first check if a session is 
working on it, or if someone has filed a topic saying they are working on it, so as to not duplicate work

- [Deflake](deflake.md) — when you are told to deflake something, follow the steps described herein

- [Entering intropsection mode means no longer making any edits to any files](introspection.md) - change your 
state to 💭, stop any background processes, make no further changes to any repository.
