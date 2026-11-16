# Add personal commands and the usable-git shortcuts in interactive shells.
typeset -U path
path=("${path[@]}" "$HOME/bin" "$HOME/dev/usable-git")

# Use nano for command-line tools that open an editor.
export EDITOR="nano"
export VISUAL="nano"

# Page through cf view, from the labs checkout in use or else the labs main
# worktree, but never from a copy of labs that another repository vendors.
export PAGER="$HOME/bin/cf-view"
export LL_PAGER="$PAGER"

l() {
  builtin source "$HOME/bin/l" "$@"
}

autoload -Uz compinit
compinit

# Completes the identifiers that l takes, most recently used checkout first.
# Each repository has a main checkout, which l names by the repository, and,
# when that is a root checkout, the worktrees beside it, which l names by a
# marker for the repository followed by the worktree's code. Each checkout is
# described by the time HEAD last moved there and the branch checked out.
_l_targets() {
  (( CURRENT == 2 )) || return 1

  local root prefix name worktree git_dir head modified_at record display_limit
  local -a groups stat_values records matches displays
  local -A checkouts

  zmodload -F zsh/stat b:zstat
  zmodload zsh/datetime

  for root in "$HOME"/dev/commonfabric/*/root(N-/); do
    name=${root:h:t}
    case $name in
      labs) prefix= ;;
      loom) prefix=l ;;
      commonfabric-weaver) prefix=w ;;
      infra) prefix=INFRA ;;
      *) prefix=$name- ;;
    esac
    groups+=("$root" "$prefix" "$name")
  done
  groups+=(
    "$HOME/dev/denoland/root" deno deno
    "$HOME/dev/cliffy/root" cliffy cliffy
  )
  for name in contraptions settings usable-git; do
    groups+=("$HOME/dev/$name" '' "$name")
  done

  for root prefix name in "${groups[@]}"; do
    [[ -d $root ]] || continue
    checkouts[$name]=$root
    [[ ${root:t} == root ]] || continue
    for worktree in "${root:h}"/{[0-9A-Z],[0-9A-Z][0-9A-Z]}(N-/); do
      checkouts[$prefix${worktree:t}]=$worktree
    done
  done

  for name worktree in "${(@kv)checkouts}"; do
    git_dir=$worktree/.git
    [[ -f $git_dir ]] && read -r git_dir < "$git_dir" &&
      git_dir=${git_dir#gitdir: }
    head=
    [[ -r $git_dir/HEAD ]] && read -r head < "$git_dir/HEAD"
    if [[ $head == 'ref: refs/heads/'* ]]; then
      head=${head#ref: refs/heads/}
    else
      head=${head[1,10]}
    fi
    zstat -A stat_values +mtime -- "$git_dir/logs/HEAD" 2>/dev/null ||
      zstat -A stat_values +mtime -- "$worktree"
    strftime -s modified_at '%b %e %H:%M' "${stat_values[1]}"
    records+=("${stat_values[1]}"$'\t'"$name"$'\t'"$name  $modified_at${head:+ · $head}")
  done

  if (( COLUMNS > 20 )); then
    display_limit=$(( COLUMNS - 2 ))
  else
    display_limit=78
  fi

  for record in ${(On)records}; do
    record=${record#*$'\t'}
    matches+=("${record%%$'\t'*}")
    record=${record#*$'\t'}
    if (( ${#record} > display_limit )); then
      record="${record[1,display_limit - 1]}…"
    fi
    displays+=("$record")
  done

  (( ${#matches} )) || return 1
  compstate[insert]=menu
  compadd -V l-targets -l -M 'm:{a-z}={A-Z}' -d displays -- "${matches[@]}"
}

_c_commits() {
  (( CURRENT == 2 )) || return 1

  local comparison_ref
  local full_hash head_short_hash short_hash subject
  local prefix=${(L)PREFIX}
  local -A is_local_only
  local -a matches displays local_matches local_displays other_matches other_displays

  head_short_hash=$(
    command git rev-parse --verify --short 'HEAD^{commit}' 2>/dev/null
  ) || return 1

  if [[ -z $PREFIX && -z $SUFFIX ]]; then
    compadd -- "$head_short_hash"
    return
  fi

  [[ -n $prefix ]] || return 1

  # The base-branch file beside c says which branch the current branch's
  # commits are compared with. Reading it in a subshell keeps its variables
  # out of this shell.
  (( $+commands[c] )) &&
    comparison_ref=$(builtin . "${commands[c]:h}/base-branch" 2>/dev/null &&
      print -r -- "$BASE_REF")

  if command git rev-parse --verify --quiet "$comparison_ref" >/dev/null 2>&1; then
    while IFS= read -r full_hash; do
      is_local_only[$full_hash]=1
    done < <(command git rev-list HEAD --not "$comparison_ref" 2>/dev/null)
  fi

  while IFS=$'\x1f' read -r full_hash short_hash subject; do
    [[ $short_hash == "$prefix"* ]] || continue
    if (( ${+is_local_only[$full_hash]} )); then
      local_matches+=("$short_hash")
      local_displays+=("+ $short_hash  $subject")
    else
      other_matches+=("$short_hash")
      other_displays+=("  $short_hash  $subject")
    fi
  done < <(command git --no-pager log --format='%H%x1f%h%x1f%s' HEAD 2>/dev/null)

  matches=("${local_matches[@]}" "${other_matches[@]}")
  displays=("${local_displays[@]}" "${other_displays[@]}")
  (( ${#matches} )) || return 1
  compstate[insert]=menu
  if (( ${#matches} > 50 )); then
    compstate[list]=
  fi
  compadd -V c-commits -l -M 'm:{A-F}={a-f}' -d displays -- "${matches[@]}"
}

compdef _l_targets l
compdef _c_commits c

# mise setup is in .zprofile

source ~/dev/contraptions/iterm-run/iterm-run.zsh
