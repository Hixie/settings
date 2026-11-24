export WEAVER_IGNORE_LOAD=1
export LOOM_UNGOVERNED=1

export PRWATCH_GITHUB_APP_ID=5052004
export PRWATCH_GITHUB_APP_KEY="~/dev/commonfabric/prwatch.pem"

# A read-only GitHub token, kept in the login keychain as the password of the
# generic item whose service is GH_TOKEN and whose account is $USER. The item
# lists /usr/bin/security as an application that may read it, so reading it
# never asks for a password. Looking it up takes a few tenths of a second, so
# only a shell that has no GH_TOKEN at all looks it up, and every shell started
# from it inherits the result. When the item cannot be read, for example over
# SSH while the keychain is locked, GH_TOKEN is empty, which gh treats as if
# it were unset. To store a new token, run:
#
#   security add-generic-password -U -a "$USER" -s GH_TOKEN -T /usr/bin/security -w
if [[ -z ${GH_TOKEN+set} ]]; then
  export GH_TOKEN=$(/usr/bin/security find-generic-password -a "$USER" -s GH_TOKEN -w 2>/dev/null)
fi

# common-fabric test-records reporting key
export CF_TEST_RECORDS_KEY_FILE="$HOME/.config/common-fabric/test-records-key.json"

# Claude seems to set this to "1" in agent shells
unset PYTHONDONTWRITEBYTECODE

# mise shims, ahead of everything else on PATH.
#
# `mise activate` (see .zprofile) installs a precmd/chpwd hook, so it only
# updates the environment when a prompt is about to be drawn. Shells with no
# prompt — agent subshells, editor tasks, git hooks, `zsh -c` from a script —
# never run that hook, so they miss the pinned toolchain entirely. Claude Code
# compounds this: it freezes PATH into a snapshot file at session start and
# replays that same PATH for every command, so a per-directory mechanism cannot
# reach it at all.
#
# A shim is a plain executable, so it needs no shell integration. It works out
# the version from the config of the directory it is run in, at the moment it
# is run, and execs the real tool with that config's environment applied.
# .zshenv is read by every zsh, which is what puts this in front of all of them.
typeset -U path
path=("$HOME/.local/share/mise/shims" "${path[@]}")

# mise's own directories, named outright rather than derived from XDG_*.
#
# Test suites point XDG_DATA_HOME (and sometimes HOME) at a scratch directory
# to sandbox their own state; cfs's conftest does this for every test. mise
# derives its install directory from XDG_DATA_HOME but keeps its lock files
# and incomplete-install markers in directories that test did not move, so
# every shim call under such a test downloads the pinned deno again, leaves
# the download behind in the cache, and marks that version as mid-install
# for the real shims too, which then print install progress and wait on the
# lock. These exports make every process see the one mise installation.
# Values a parent already exported win, so a child zsh whose HOME a test has
# changed keeps the real directories.
export MISE_DATA_DIR="${MISE_DATA_DIR:-$HOME/.local/share/mise}"
export MISE_STATE_DIR="${MISE_STATE_DIR:-$HOME/.local/state/mise}"
export MISE_CACHE_DIR="${MISE_CACHE_DIR:-$HOME/Library/Caches/mise}"
export MISE_CONFIG_DIR="${MISE_CONFIG_DIR:-$HOME/.config/mise}"

# Coding agents write their shell commands for bash. These options make zsh
# expand words the way bash does in the shells that run those commands.
# Claude Code and Codex each run a command as "zsh -c", which reads only
# this file. The test picks out a non-interactive, non-login "zsh -c" whose
# parent is the agent: Claude Code exports its own PID as CLAUDE_PID, and
# Codex sets CODEX_SHELL or CODEX_THREAD_ID. Both agents snapshot the login
# environment in a login shell, which keeps zsh's defaults while it runs
# .zprofile and .zshrc. A zsh script keeps zsh's defaults even when a
# command execs it, because it is not a "zsh -c".
if [[ ! -o interactive && ! -o login && -n ${ZSH_EXECUTION_STRING-} ]] && {
  [[ -n ${CLAUDE_PID-} && $PPID == "$CLAUDE_PID" ]] ||
  [[ -n ${CODEX_SHELL-}${CODEX_THREAD_ID-} && $(/bin/ps -o ucomm= -p $PPID) == codex* ]]
}; then
  setopt no_nomatch          # a glob that matches nothing stays as typed
  setopt no_bad_pattern      # so does a malformed glob, such as "(*"
  setopt no_equals           # "=word" is not a command path, so "echo ===" works
  setopt no_bare_glob_qual   # "*(N)" is not a glob qualifier
  setopt sh_word_split       # unquoted $var splits on whitespace
  setopt glob_subst          # unquoted $var is globbed (and, unlike bash, a leading ~ expands)
  setopt ksh_arrays          # arrays start at 0; "$v[0]" and "$ref:src" are not subscripts or modifiers
  setopt bash_rematch        # [[ =~ ]] fills BASH_REMATCH
  setopt bsd_echo            # echo leaves backslashes alone unless given -e
  setopt no_multios          # "cmd >file | other" sends output only to the file
  setopt sh_nullcmd          # "> file" with no command just truncates the file
  setopt no_bg_nice          # background jobs keep normal priority
fi
