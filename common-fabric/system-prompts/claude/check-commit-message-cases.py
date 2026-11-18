#!/usr/bin/env python3
"""Cases for check-commit-message.py, the script that checks and rewraps
commit messages.

Run it with no arguments. It writes each message to a temporary file, runs
the script on it with --fix, and checks the exit status and the rewritten
message. It then runs the script on the result again and checks that the
second run changes nothing, since a message that --fix has already wrapped
is often wrapped again. It reports one line per case. The exit status is 0
when every case passed and 1 otherwise.
"""

import os
import subprocess
import sys
import tempfile

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "check-commit-message.py")

# (description, message, message after --fix, exit status of the first
# run and of a second run on its result)
CASES = [
    ("a line starting with a number other than 1 continues the paragraph",
     """Report stalls on the command's own output

longrun reports a stall when a command has printed nothing for `--quiet`
minutes (10 by default). A hung deno test prints

    'loom-cold-reader' has been running for over (8m0s)

nine minutes into the test, so longrun reported it after 19 minutes, not
10. A test stuck in loom's pytest suite prints a stack dump at 300
seconds and another line at 600, so it was reported after 15 or 20
minutes.
""",
     """Report stalls on the command's own output

longrun reports a stall when a command has printed nothing for `--quiet`
minutes (10 by default). A hung deno test prints

    'loom-cold-reader' has been running for over (8m0s)

nine minutes into the test, so longrun reported it after 19 minutes,
not 10. A test stuck in loom's pytest suite prints a stack dump at 300
seconds and another line at 600, so it was reported after 15 or 20
minutes.
""", (0, 0)),

    ("labels directly above their paragraphs stay on lines of their own",
     """Leave row notification repair to the shared store

PROBLEM
The test-only arrival dependency in ba66b0bbe hides a missing notification in the shared row API.

SOLUTION
Revert ba66b0bbe in full.
Keep the kept-change test using the same row API as its callers.

DESIGN DISCUSSION
NodeCaptureTest makes every frame take two and a half seconds, so the
test waits for each frame.
SEE ALSO
 * top/3156: Recovery can inspect superseded pull request runs
""",
     """Leave row notification repair to the shared store

PROBLEM
The test-only arrival dependency in ba66b0bbe hides a missing
notification in the shared row API.

SOLUTION
Revert ba66b0bbe in full. Keep the kept-change test using the same row
API as its callers.

DESIGN DISCUSSION
NodeCaptureTest makes every frame take two and a half seconds, so the
test waits for each frame.
SEE ALSO
 * top/3156: Recovery can inspect superseded pull request runs
""", (0, 0)),

    ("a label ending in a colon stays on a line of its own",
     """Seal consent results once

PROBLEM:
The broker sealed a Calendar write consent's result to a key that no
reader holds.
SOLUTION:
- Delete the sealed result.
""",
     """Seal consent results once

PROBLEM:
The broker sealed a Calendar write consent's result to a key that no
reader holds.
SOLUTION:
- Delete the sealed result.
""", (0, 0)),

    ("labels after a sentence, a list item or another label, with trailing spaces",
     """Label after other lines

The test waits for each frame.
DESIGN DISCUSSION\x20\x20
- an item
NOTE
The fix (it was slow.)
FOLLOW-UP
He said "stop."
SEE ALSO
 * top/3156: Recovery can inspect superseded pull request runs
""",
     """Label after other lines

The test waits for each frame.
DESIGN DISCUSSION
- an item
NOTE
The fix (it was slow.)
FOLLOW-UP
He said "stop."
SEE ALSO
 * top/3156: Recovery can inspect superseded pull request runs
""", (0, 0)),

    ("a label after a line that ends without a full stop",
     """Label after a reference

PROBLEM
Tests flake on loom (see top/3156)
SOLUTION
longrun now retries less.

- the retry count is too high
SOLUTION
longrun now retries less.

PROBLEM
longrun reports a stall too late.

DESIGN DISCUSSION
The retry logic now lives in `longrun.py`
SEE ALSO
 * top/3156: Recovery

The fix lives in `foo.py`
SEE ALSO

 * top/1: the first topic

- Log more
SEE ALSO
https://github.com/example/foo/issues/1
""",
     """Label after a reference

PROBLEM
Tests flake on loom (see top/3156)
SOLUTION
longrun now retries less.

- the retry count is too high
SOLUTION
longrun now retries less.

PROBLEM
longrun reports a stall too late.

DESIGN DISCUSSION
The retry logic now lives in `longrun.py`
SEE ALSO
 * top/3156: Recovery

The fix lives in `foo.py`
SEE ALSO

 * top/1: the first topic

- Log more
SEE ALSO
https://github.com/example/foo/issues/1
""", (0, 0)),

    ("a list item's hanging indent does not make it an indented block",
     """Rewrap list items with wide markers

nine minutes into the test, so longrun reported it after 19 minutes, not
10. A test stuck in loom's pytest suite prints a stack dump at 300
    seconds and another line at 600, so it was reported after 15 or 20
    minutes.

10. a tenth item that is long enough that it has to wrap onto a second
    line, and then gained a lot more words when someone edited it later on

Example:
    an indented line that is long enough to go past the seventy-two column limit

- an item
    an indented line that is long enough to go past the seventy-two column limit

10. Bump the timeout.
To try it, run:
    longrun --quiet 10 deno test

10. Bump the timeout.
Then run
    longrun --quiet 10 deno test

10. Bump the timeout, then run:
    longrun --quiet 10 deno test

- Outer step
  - Run this:
    make test
    make lint
""",
     """Rewrap list items with wide markers

nine minutes into the test, so longrun reported it after 19 minutes,
not 10. A test stuck in loom's pytest suite prints a stack dump at 300
seconds and another line at 600, so it was reported after 15 or 20
minutes.

10. a tenth item that is long enough that it has to wrap onto a second
    line, and then gained a lot more words when someone edited it later
    on

Example:
    an indented line that is long enough to go past the seventy-two column limit

- an item
    an indented line that is long enough to go past the seventy-two column limit

10. Bump the timeout.
To try it, run:
    longrun --quiet 10 deno test

10. Bump the timeout.
Then run
    longrun --quiet 10 deno test

10. Bump the timeout, then run:
    longrun --quiet 10 deno test

- Outer step
  - Run this:
    make test
    make lint
""", (0, 0)),

    ("a line starting with 1 or following a sentence starts a numbered list",
     """Number the steps

Here is what to do
1. Do a.
2. Do b.

Then, once it lands:
3. Do c.
4. Do d.

Run it (twice.)
3. Check the log.

STEPS
5. Do e., which is long enough that it has to wrap onto a second line here.
""",
     """Number the steps

Here is what to do
1. Do a.
2. Do b.

Then, once it lands:
3. Do c.
4. Do d.

Run it (twice.)
3. Check the log.

STEPS
5. Do e., which is long enough that it has to wrap onto a second line
   here.
""", (0, 0)),

    ("a label with text on the same line is ordinary text",
     """Seal consent results once

PROBLEM: the broker sealed a Calendar write consent's result to a key
that no reader holds.
SOLUTION: delete the sealed result. Nothing reads it.
""",
     """Seal consent results once

PROBLEM: the broker sealed a Calendar write consent's result to a key
that no reader holds. SOLUTION: delete the sealed result. Nothing reads
it.
""", (0, 0)),

    ("ordinary paragraphs are rewrapped to 72 columns",
     """Rewrap paragraphs

This paragraph was written as one long line that goes well past the seventy-two columns GitHub shows.
Short
lines
join up.

A second paragraph stays separate.
""",
     """Rewrap paragraphs

This paragraph was written as one long line that goes well past the
seventy-two columns GitHub shows. Short lines join up.

A second paragraph stays separate.
""", (0, 0)),

    ("a word that looks like a list marker, quote or fence starts no line",
     """Explain the cache

The cache keeps the values it read until the configuration file changes - at which point it reads the file again.

The cache keeps the values it read until the configuration file changes 2. times.

The cache keeps the values it read until the configuration file changes > 3 times.

The cache keeps the values it read until the configuration file changes ```text in it.

A later paragraph is written as one long line that goes past seventy-two columns.
""",
     """Explain the cache

The cache keeps the values it read until the configuration file
changes - at which point it reads the file again.

The cache keeps the values it read until the configuration file
changes 2. times.

The cache keeps the values it read until the configuration file
changes > 3 times.

The cache keeps the values it read until the configuration file
changes ```text in it.

A later paragraph is written as one long line that goes past seventy-two
columns.
""", (0, 0)),

    ("lists keep their items and hanging indents",
     """List the changes

The changes are:
- the first item, which is long enough that it has to wrap onto a second line
- the second item
* a starred item
1. a numbered list can start in the middle of a paragraph
2. and continue
10. past nine
11) with a parenthesis
  - a nested item
""",
     """List the changes

The changes are:
- the first item, which is long enough that it has to wrap onto a second
  line
- the second item
* a starred item
1. a numbered list can start in the middle of a paragraph
2. and continue
10. past nine
11) with a parenthesis
  - a nested item
""", (0, 0)),

    ("indented blocks, fences, quotes and trailers are left alone",
     """Leave preformatted text alone

    an indented line that is long enough to go past the seventy-two column limit
    next

```
a fenced line that is long enough to go past the seventy-two column limit too
```

> a quoted line that is long enough to go past the seventy-two column limit too

Co-Authored-By: Someone With A Very Long Name Indeed <someone.with.a.long.name@example.com>
Change-Id: I0123456789
""",
     """Leave preformatted text alone

    an indented line that is long enough to go past the seventy-two column limit
    next

```
a fenced line that is long enough to go past the seventy-two column limit too
```

> a quoted line that is long enough to go past the seventy-two column limit too

Co-Authored-By: Someone With A Very Long Name Indeed <someone.with.a.long.name@example.com>
Change-Id: I0123456789
""", (0, 0)),

    ("a subject over 72 characters is a problem --fix cannot solve",
     """This subject line goes on and on well past the seventy-two characters allowed

Body.
""",
     """This subject line goes on and on well past the seventy-two characters allowed

Body.
""", (1, 1)),

    ("a body with no blank line after the subject is a problem",
     """Subject
Body.
""",
     """Subject

Body.
""", (1, 0)),
]


def fix(directory, name, message):
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(message)
    result = subprocess.run([sys.executable, SCRIPT, "--fix", path],
                            capture_output=True, text=True, check=False)
    with open(path, encoding="utf-8") as handle:
        return result.returncode, handle.read(), result.stdout


def main():
    failures = 0
    with tempfile.TemporaryDirectory() as directory:
        for number, case in enumerate(CASES):
            description, message, expected, (status, status_again) = case
            code, fixed, output = fix(directory, f"{number}.txt", message)
            again, refixed, _ = fix(directory, f"{number}-again.txt", fixed)
            errors = []
            if code != status:
                errors.append(f"exit status {code}, expected {status}:\n{output}")
            if fixed != expected:
                errors.append(f"got:\n{fixed}\nexpected:\n{expected}")
            if refixed != fixed:
                errors.append(f"a second run changed it to:\n{refixed}")
            if again != status_again:
                errors.append(f"a second run exited with {again}, not {status_again}")
            print(f"{'FAIL' if errors else 'ok  '} {description}")
            for error in errors:
                print("    " + error.replace("\n", "\n    "))
            failures += bool(errors)
    print(f"{len(CASES) - failures} of {len(CASES)} cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
