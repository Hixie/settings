# Commit message width

GitHub cuts a commit subject off at 72 characters and replaces the rest with an ellipsis, in the commit list, in the PR "Commits" tab, and in blame. It also lays the body out in a column narrower than the 80 columns a text editor defaults to, so a body wrapped at 80 spills its last word or two onto a line of its own.

Measured across 1,879 commits in labs: my subjects run to a median of 77 characters and 60% of them are past 72, and my bodies are hard wrapped at exactly 80. Both are a few characters too wide, which is why the ends of my commit messages keep disappearing or wrapping.

The limits are therefore:

- Subject: 72 characters at the absolute most, and aim for 50. This includes the `type(scope):` prefix and any `(#1234)` suffix that a squash merge appends, so leave room for that suffix.
- Body: wrapped at 72 columns. This is the width `git log` is built around, since it indents the body by four spaces and still fits an 80-column terminal.

Counting characters by eye does not work. Run the check instead.

## How to commit

1. Write the message to a file rather than passing it inline. Put it in the session scratchpad directory, say `$SCRATCHPAD/commit-msg.txt`. This also sidesteps the shell quoting problems that come with a here-document containing backticks.
2. Run `python3 ~/.claude/check-commit-message.py --fix $SCRATCHPAD/commit-msg.txt`. It rewraps ordinary paragraphs and list items to 72 columns, and it leaves indented blocks, fenced code, quotes, and the trailer block at the end untouched.
3. If it reports a problem, fix it and run it again. The subject is the one thing it cannot fix for you, because shortening a subject means rewording it.
4. Commit with `git commit -F $SCRATCHPAD/commit-msg.txt`.

The script distinguishes problems from notes. A problem is something that will render badly and can be fixed, and it makes the script exit non-zero. A note is something the script has decided not to touch: a line that is one long URL with nowhere to break, a trailer, or a line inside a code block. Read the notes and shorten those lines by hand where you can, but they are not failures.

## Enforcing it with git

The script also works as a git `commit-msg` hook, which git invokes with the path to the message file. That is not installed, for two reasons. It would police Ian's own commits as well as mine, which is his call to make and not mine. And the obvious way to install it everywhere, setting `core.hooksPath` globally, replaces each repository's own hooks rather than adding to them, which would disable the `post-merge` hook in the loom checkout.

Installing it in one repository is safe:

    ln -s ~/.claude/check-commit-message.py <repo>/.git/hooks/commit-msg

Note that Claude Code's own hooks cannot do this job: every labs copy carries a `settings.local.json` with `disableAllHooks` set, so a `PreToolUse` hook never fires there. Git hooks are unaffected by that setting.
