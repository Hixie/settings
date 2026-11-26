# worktree-buttons

A Claude Code mod that shows, above the prompt, a button for each worktree
named in the session title. The title has the shape `WORKTREES: STATE SUMMARY`,
where WORKTREES is a comma-separated list of worktree identifiers (as
`~/bin/l` understands them) and STATE is the session's state emoji.

Each worktree's button is labeled with its identifier followed by what a press
does.
N is the number of commits on the worktree's branch that are not on the main
branch (the commits `logs` marks with a `+`), and #P is the number of the
branch's pull request. Commands run in the shell of iTerm2's frontmost
session, through `~/dev/contraptions/iterm-run`.

| Pull request | State | N | Label | A press |
|--|--|--|--|--|
| any | any | 0 | `D0: OPEN WORKTREE` | runs `cd WORKTREE; l` |
| none | any | 1 | `D0: REVIEW` | runs `cd WORKTREE; c --separate` |
| none | any | >1 | `D0: REVIEW (N commits)`, `SQUASH` | runs `cd WORKTREE; c --separate`; SQUASH sends the session "squash" |
| listed | not ✅ | >0 | `D0: OPEN PR #P` | opens the pull request with `open` |
| listed | ✅ | 1 | `D0: REREVIEW TO MERGE (PR #P)` | runs `cd WORKTREE; c` |
| listed | ✅ | >1 | `D0: REVIEW TO MERGE (N-1 new commits, PR #P)`, `EACH COMMIT` | runs `cd WORKTREE; c A..B`; EACH COMMIT adds `--separate` when N-1 > 1 |

In `c A..B`, A is the second-oldest of the N commits and B the newest; with N-1
of 1 the label says "1 new commit". When N-1 is more than 1, a dim `EACH
COMMIT` button beside it runs `cd WORKTREE; c A..B --separate` instead, to show
the commits one at a time. Without a pull request and with more than one
commit, a dim `SQUASH` button beside REVIEW sends the session the message
"squash", as if typed at the prompt. A worktree with no commits of its own
offers OPEN WORKTREE whatever pull request is listed for its branch.

When merging the N commits into the main branch would conflict, every row of
the table above except OPEN WORKTREE also has a dim `REBASE` button, after any
other dim button, which sends the session the message "rebase". The mod finds
out with `git merge-tree --write-tree --quiet`, which merges the branch into the
main branch without touching the worktree. It exits with status 1 and prints
nothing when the merge conflicts. Any other failure, including status 1 with a
message, is shown as an error in place of the worktree's buttons, as described
below.

The pull request comes from `~/.cache/github-prs.tsv`, which
`~/dev/contraptions/github-hookbar` keeps up to date. The mod reads it with
`lockf -kn`, which holds a `flock(2)` lock on the file while `cat` reads it,
the same lock github-hookbar holds while it rewrites the file. A line about a
pull request holds a GitHub repository as `owner/name`, a branch name, and a
pull request number, separated by tabs. Other lines are skipped. A line matches
a worktree when its branch is the worktree's branch and its repository is the
GitHub repository of the worktree's `upstream` remote, or of its `origin`
remote when there is no `upstream`. When several lines match, the highest
number wins.

A title that starts with an emoji, such as `💬 Fix: a bug`, has no worktree
list, and neither does a title whose text after the first `: ` does not start
with an emoji, such as `PR: fix flake`. Emoji here, and as states below, are
pictographic emoji, with any skin tone or other pictographic emoji joined to
them; flags and keycaps are not. An identifier that `~/bin/l` would
reject is skipped, and so is a second identifier for a folder already listed.
A worktree whose folder does not exist, such as one deleted before the title
was updated, is shown as dim `D0: FOLDER MISSING` text instead of a button. A
worktree that cannot be inspected for another reason, for example because its
main branch was never fetched, is shown with the error instead of a button.
The mod runs its commands in `/` or in the worktree's folder, never in the
session's working directory, so a session whose own worktree has been deleted
still shows the other worktrees' buttons. A folder that exists but is not a
git checkout, such as `~/dev/commonfabric/dogfood` (the identifier `dogfood`),
which holds two clones, has no commits of its own, so it offers OPEN WORKTREE.

The title comes from the desktop app's record of the session, in
`~/Library/Application Support/Claude/claude-code-sessions/`. The buttons are
worked out again when the session starts, even with no window attached, when a
desktop window attaches to it, when a turn ends, when the session title is set
by a tool call, and after a button is pressed. A press does what the button
showed when it was drawn.

While the buttons are being worked out, which runs git in each worktree and
reads the pull request table, the band shows a spinner labeled `Checking
worktrees` in place of everything else, including the dim text of a press that
has not finished. That happens each time the buttons are worked out again, so
the buttons are gone until git and the table have answered. The mod draws the
spinner with the `Progress` element, which the test kit draws on the terminal
and the desktop as the label followed by a dim `Running…`. A title without
worktrees never shows the spinner, because the mod decides there is nothing to
show before it does any of that work. When refreshes overlap, only the newest
one changes the band.

Until a press finishes, the band shows dim text in place of the button, so the
button cannot be pressed again. The text is the button's label followed by
`(running)` for a command. For a message such as SQUASH or REBASE, it is
followed by `(sending)`, or by `(sent when this turn ends)` while the session
is working, because a message from the mod reaches the session only once it is
idle.

iterm-run runs a command only when that shell is idle at an empty prompt, and
only in shells that load its listener from `~/.zshrc`; otherwise nothing runs
and a message says the shell was busy. iterm-run asks iTerm2 which session is
frontmost, so macOS asks once whether Claude may control iTerm2.

## Sorting sessions into sidebar sections

The mod also files the session in the desktop app's sidebar under the section
for its state: the first section, in sidebar order, that the sidebar shows and
whose name contains the state emoji of the session's title. A section can
therefore hold several states, such as one named `🧱 🚧`. Only whole emoji
count, so the state `❤` does not match a section named `❤️‍🔥`, and emoji are
compared without U+FE0F VARIATION SELECTOR-16, so `⏸` and `⏸️` match each
other. The state is the emoji the title starts with, or else the emoji that
follows the first `: `.

The session is sorted when it starts, and when a tool call that sets its own
title or moves it to the top level of the sidebar succeeds
(`set_session_title` or `detach_session` naming `self` or the session's own
id). A call that names another session sorts nothing; that session's own copy
of the mod sorts it when it sets its own title. One sort finishes before the
next starts, so the last title set decides. The mod reads the title and the
session's section with `get_session`, the sections with `list_sections`, and
moves the session with `move_sessions`, all through the desktop app's MCP
servers. A session the desktop app did not start, such as one in a terminal,
has no `CLAUDE_CODE_HOST_SESSION_ID` and is never sorted.

The session stays where it is when no section's name contains its state, when
the title has no state, when it is pinned (moving a pinned session unpins it),
or when the app has not yet reported which section the session is in. A
session in a section whose name starts with `Arc:` also stays; a session in
any other section is moved out of it when its state matches another section.
When a call fails, or the app answers in a form the mod does not expect, a
toast says why. According to the description of `move_sessions`, moving a
session switches the sidebar to a layout that shows custom sections if it was
not in one.

## Checking changes

From this folder:

    claude plugin validate .
    claude plugin test .

`claude plugin test` runs `tests/register.test.tsx`, which stands in for the
session title, the pull request table, git, and the commands a press runs, and
`tests/sort-session.test.ts`, which stands in for the desktop app's session and
sidebar tools.
Run both with the Claude Code that the desktop app runs, which is at
`~/Library/Application Support/Claude/claude-code/VERSION/*/claude.app/Contents/MacOS/claude`
for the newest VERSION there. The mod draws the spinner with the `Progress`
element, and the tests expect the band to be a list of one row per mod, both
of which an older `claude` on the `PATH` may lack.
To type-check, run `tsc -p .`. The `tsconfig.json` here extends
`.claude-plugin/types/tsconfig.json`, which a session that watches this folder
(`CLAUDE_CODE_PLUGIN_DIR_WATCH=1`) writes, with the API's declarations, each
time it loads the mod; git ignores that folder.
