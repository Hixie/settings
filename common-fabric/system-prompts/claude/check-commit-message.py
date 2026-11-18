#!/usr/bin/env python3
"""Check, and optionally rewrap, a commit message so GitHub renders it unwrapped.

GitHub truncates a commit subject at 72 characters and wraps the body narrower
than the 80 columns an editor defaults to, so a message that looks fine locally
loses its last few words on the web. This holds the subject inside 72 and the
body inside 72.

Usage:
    python3 ~/.claude/check-commit-message.py [--fix] [--width N] MESSAGE_FILE

--fix rewraps ordinary prose and list items. It keeps a section label such as
PROBLEM on a line of its own, leaves indented blocks, fenced code, quotes, and
the trailer block alone, and reports anything still too wide that only
rewording can shorten. Exits non-zero while problems remain.

check-commit-message-cases.py beside this script tests it.
"""

import argparse
import re
import sys
import textwrap

SUBJECT_LIMIT = 72
SUBJECT_TARGET = 50
BODY_WIDTH = 72

FENCE = re.compile(r"^\s*(```|~~~)")
BULLET = re.compile(r"^(\s*(?:[-*+]|(\d+)[.)])\s+)")
LABEL = re.compile(r"^[A-Z][A-Z0-9 -]*[A-Z0-9]:?$")
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


def starts_block(word):
    """True if a line starting with this word is not read as ordinary text."""
    return bool(BULLET.match(word + " ") or QUOTE.match(word) or FENCE.match(word))


def ends_sentence(line):
    """True if the line ends in . : ? or !, before any closing brackets and quotes."""
    return line.rstrip().rstrip(")]\"'").endswith((".", ":", "?", "!"))


def rewrap_block(block, width):
    """Rewrap one paragraph, keeping labels, list structure and hanging indents.

    A label, a line of capital letters such as PROBLEM, stays on a line of its
    own. A line that follows ordinary text whose last line does not end a
    sentence continues that text even when it starts with a number other than
    1. A word that would make its line read as a list item, a quote or a fence
    is kept off the start of a wrapped line.
    """
    lines = [line for _, line in block]
    items = []  # [prefix, parts]; a label is a prefix with no parts
    for number, line in enumerate(lines):
        marker = BULLET.match(line)
        unfinished = number > 0 and not ends_sentence(lines[number - 1])
        continues = unfinished and items[-1][1] and not BULLET.match(items[-1][0])
        if LABEL.match(line.rstrip()):
            items.append([line.rstrip(), []])
        elif marker and (marker.group(2) in (None, "1") or not continues):
            items.append([marker.group(1), [line[marker.end():]]])
        elif items and items[-1][1]:
            items[-1][1].append(line)
        else:
            items.append([re.match(r"^\s*", line).group(0), [line]])

    out = []
    for prefix, parts in items:
        words = " ".join(parts).split()
        glued = "".join(
            ("\0" if starts_block(word) else " ") + word for word in words[1:]
        )
        wrapped = textwrap.wrap(
            "".join(words[:1]) + glued,
            width=width,
            initial_indent=prefix,
            subsequent_indent=" " * len(prefix),
            break_long_words=False,
            break_on_hyphens=False,
        )
        out.extend([line.replace("\0", " ") for line in wrapped] or [prefix.rstrip()])
    return out


def has_break_point(line, width):
    """True if the line could be wrapped at or before width."""
    indent = len(line) - len(line.lstrip())
    return " " in line[indent:width + 1].strip()


def indented(lines):
    """True if a line is indented as code, not as the rest of a list item.

    A line indented by a tab or four or more spaces is code, unless it is
    indented exactly as far as the text of the list item above it and the
    line before it does not end in a colon. An unindented line that is not a
    list item ends that indentation.
    """
    hanging, previous = None, ""
    for line in lines:
        indent = len(line) - len(line.lstrip(" "))
        if line.startswith(("    ", "\t")) and (
            indent != hanging or previous.rstrip().endswith(":")
        ):
            return True
        marker = BULLET.match(line)
        if marker:
            hanging = len(marker.group(1))
        elif not line.startswith(" "):
            hanging = None
        previous = line
    return False


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
        elif any(QUOTE.match(line) for line in text) or indented(text):
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
