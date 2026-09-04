#!/bin/sh
# Hardlinks the Markdown files of a system prompt directory into the places
# where Claude Code and Codex read them from.
#
# Each FILE.md in the given directory is linked to ~/.claude/FILE.md and
# ~/.codex/FILE.md. INDEX.md is linked to ~/.claude/CLAUDE.md and
# ~/.codex/AGENTS.md instead.
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

exit $status
