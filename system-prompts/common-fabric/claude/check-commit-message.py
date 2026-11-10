#!/usr/bin/env python3
"""Check, and optionally rewrap, a commit message so GitHub renders it unwrapped.

GitHub truncates a commit subject at 72 characters and wraps the body narrower
than the 80 columns an editor defaults to, so a message that looks fine locally
loses its last few words on the web. This holds the subject inside 72 and the
body inside 72.

Usage:
    python3 ~/.claude/check-commit-message.py [--fix] [--width N] MESSAGE_FILE

--fix rewraps ordinary prose and list items. It leaves indented blocks, fenced
code, quotes, and the trailer block alone, and reports anything still too wide
that only rewording can shorten. Exits non-zero while problems remain.
"""

import argparse
import re
import sys
import textwrap

SUBJECT_LIMIT = 72
SUBJECT_TARGET = 50
BODY_WIDTH = 72

FENCE = re.compile(r"^\s*(```|~~~)")
BULLET = re.compile(r"^(\s*(?:[-*+]|\d+[.)])\s+)")
TRAILER = re.compile(r"^[A-Za-z][A-Za-z0-9-]*: .+$")
QUOTE = re.compile(r"^\s*>")


def fenced_lines(lines):
    """Indices sitting inside a ``` or ~~~ region, fence markers included."""
    inside, marked = None, set()
    for index, line in enumerate(lines):
        match = FENCE.match(line)
        if match and inside is None:
            inside, = match.groups()
            marked.add(index)
        elif match and match.group(1) == inside:
            inside = None
            marked.add(index)
        elif inside is not None:
            marked.add(index)
    return marked


def split_blocks(lines):
    """Group (index, line) pairs into blocks separated by blank lines."""
    blocks, current = [], []
    for index, line in enumerate(lines):
        if line.strip():
            current.append((index, line))
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def rewrap_block(block, width):
    """Rewrap one paragraph, keeping list structure and hanging indents."""
    items, current, prefix = [], [], ""
    for _, line in block:
        match = BULLET.match(line)
        if match:
            if current:
                items.append((prefix, current))
            prefix = match.group(1)
            current = [line[len(prefix):].strip()]
        elif current:
            current.append(line.strip())
        else:
            prefix = re.match(r"^\s*", line).group(0)
            current = [line.strip()]
    if current:
        items.append((prefix, current))

    out = []
    for prefix, parts in items:
        hanging = " " * len(prefix)
        out.extend(
            textwrap.wrap(
                " ".join(parts),
                width=width,
                initial_indent=prefix,
                subsequent_indent=hanging,
                break_long_words=False,
                break_on_hyphens=False,
            )
            or [prefix.rstrip()]
        )
    return out


def has_break_point(line, width):
    """True if the line could be wrapped at or before width."""
    indent = len(line) - len(line.lstrip())
    return " " in line[indent:width + 1].strip()


def classify(lines, width):
    """Split the body into blocks and label each one."""
    fenced = fenced_lines(lines)
    blocks = split_blocks(lines)
    labelled = []
    for position, block in enumerate(blocks):
        indices = [index for index, _ in block]
        text = [line for _, line in block]
        if any(index in fenced for index in indices):
            kind = "preformatted"
        elif any(QUOTE.match(line) or line.startswith(("    ", "\t")) for line in text):
            kind = "preformatted"
        elif position == len(blocks) - 1 and all(TRAILER.match(line) for line in text):
            kind = "trailer"
        else:
            kind = "prose"
        labelled.append((kind, block))
    return labelled


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--fix", action="store_true")
    parser.add_argument("--width", type=int, default=BODY_WIDTH)
    args = parser.parse_args()

    with open(args.path, encoding="utf-8") as handle:
        lines = handle.read().rstrip("\n").split("\n")

    if not lines or not lines[0].strip():
        print("error: commit message is empty")
        return 1

    problems, notes = [], []
    subject, body = lines[0], lines[1:]

    if len(subject) > SUBJECT_LIMIT:
        problems.append(
            f"subject is {len(subject)} chars, {len(subject) - SUBJECT_LIMIT} over the "
            f"{SUBJECT_LIMIT} GitHub truncates at. Reword it; --fix cannot:\n"
            f"      {subject[:SUBJECT_LIMIT]}|{subject[SUBJECT_LIMIT:]}"
        )
    elif len(subject) > SUBJECT_TARGET:
        notes.append(
            f"subject is {len(subject)} chars. Under {SUBJECT_TARGET} reads better in "
            f"narrow views, but it will not be truncated."
        )

    if body and body[0].strip():
        problems.append("subject and body must be separated by a blank line")
        body = [""] + body

    if args.fix:
        rebuilt, previous_end = [], 0
        for kind, block in classify(body, args.width):
            start = block[0][0]
            rebuilt.extend([""] * (start - previous_end))
            text = [line for _, line in block]
            rebuilt.extend(rewrap_block(block, args.width) if kind == "prose" else text)
            previous_end = block[-1][0] + 1
        body = rebuilt
        with open(args.path, "w", encoding="utf-8") as handle:
            handle.write("\n".join([subject] + body).rstrip("\n") + "\n")

    for kind, block in classify(body, args.width):
        for index, line in block:
            if len(line) <= args.width:
                continue
            where = f"line {index + 2} is {len(line)} chars"
            shown = f"      {line[:args.width]}|{line[args.width:]}"
            if kind == "preformatted":
                notes.append(
                    f"{where}, inside a code or indented block. It will wrap on "
                    f"GitHub; shorten it by hand if that matters.\n{shown}"
                )
            elif kind == "trailer":
                notes.append(f"{where}, but it is a trailer and cannot be split.")
            elif not has_break_point(line, args.width):
                notes.append(f"{where} with no break point (a URL or path). Left as is.")
            else:
                problems.append(f"{where}:\n{shown}")

    for note in notes:
        print(f"  note: {note}")

    if problems:
        print(f"\ncommit message is too wide for GitHub, {len(problems)} problem(s):\n")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print(f"commit message fits: subject {len(subject)} chars, body within {args.width}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
