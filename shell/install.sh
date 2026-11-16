#!/bin/sh
# Links the shell's startup files and commands into place with symbolic
# links: zshenv, zprofile and zshrc to ~/.zshenv, ~/.zprofile and ~/.zshrc,
# and each file in bin to the same name in ~/bin.
#
# A destination that is a regular file with the same contents as its source
# is replaced by the link. Any other destination that already exists is
# reported and left alone, and the script exits with a non-zero status.

set -eu

here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
status=0

link() { # link SOURCE DESTINATION
  if [ "$1" -ef "$2" ]; then
    return
  fi
  if [ -L "$2" ] || { [ -e "$2" ] && ! { [ -f "$2" ] && cmp -s "$1" "$2"; }; }; then
    echo "$2 differs from $1; leaving it alone" >&2
    status=1
    return
  fi
  mkdir -p "$(dirname "$2")"
  ln -sf "$1" "$2"
}

for name in zshenv zprofile zshrc; do
  link "$here/$name" "$HOME/.$name"
done

for source in "$here"/bin/*; do
  [ -f "$source" ] || continue
  link "$source" "$HOME/bin/$(basename "$source")"
done

exit $status
