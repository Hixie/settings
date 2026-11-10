#!/bin/sh
# Hardlinks the files of a system prompt directory into the places where
# Claude Code and Codex read them from.
#
# Each FILE.md in the given directory is linked to ~/.claude/FILE.md and
# ~/.codex/FILE.md. INDEX.md is linked to ~/.claude/CLAUDE.md and
# ~/.codex/AGENTS.md instead.
#
# Files that only one of the two reads, such as Claude Code's hooks, go in
# the directory's claude or codex subdirectory. Each is linked to the same
# path under ~/.claude or ~/.codex respectively, so claude/hooks/X.py is
# linked to ~/.claude/hooks/X.py. Hidden files and directories, and Python's
# __pycache__ directories, are left out. Anything else there that is not a
# regular file, such as a symbolic link, is reported and left out.
#
# A destination that already holds different contents is reported and left
# alone, and the script exits with a non-zero status.

set -eu

directory=${1:?usage: install.sh DIRECTORY}
status=0

link() { # link SOURCE DESTINATION
  if [ "$1" -ef "$2" ]; then
    return
  fi
  if [ -e "$2" ] && ! cmp -s "$1" "$2"; then
    echo "$2 differs from $1; leaving it alone" >&2
    status=1
    return
  fi
  mkdir -p "$(dirname "$2")"
  ln -f "$1" "$2"
}

mkdir -p "$HOME/.claude" "$HOME/.codex"

for source in "$directory"/*.md; do
  [ -e "$source" ] || continue
  name=$(basename "$source")
  if [ "$name" = INDEX.md ]; then
    link "$source" "$HOME/.claude/CLAUDE.md"
    link "$source" "$HOME/.codex/AGENTS.md"
  else
    link "$source" "$HOME/.claude/$name"
    link "$source" "$HOME/.codex/$name"
  fi
done

for tool in claude codex; do
  [ -d "$directory/$tool" ] || continue
  # find runs in an assignment, so that set -e stops the script if it fails.
  # The loop reads a here-document rather than a pipe, so that it runs in
  # this shell and a status that link sets survives it.
  files=$(find -H "$directory/$tool" \( -name __pycache__ -o -name '.*' \) \
    -prune -o ! -type d -print)
  while IFS= read -r source; do
    [ -n "$source" ] || continue
    if [ -L "$source" ] || [ ! -f "$source" ]; then
      echo "$source is not a regular file; leaving it alone" >&2
      status=1
      continue
    fi
    link "$source" "$HOME/.$tool/${source#"$directory/$tool/"}"
  done <<EOF
$files
EOF
done

exit $status
