# The /Users/ianh/dev/commontools/commontoolsinc.labs.* repos are parallel repo copies

Under ~/dev/commontools there are several `commontoolsinc.labs.X` directories (labs, labs.2, labs.3, labs.4, ...). 
They are parallel copies of the same repository, each in use by a different agent.

Rule: work in ONLY the repo specified in the current conversation. Ignore all the other `commontoolsinc.labs.*` 
copies — don't search, edit, or report matches from them. When a task is ambiguous about which copy, ask.

When the user says something like "use labs 2", it means the workspace at 
`/Users/ianh/dev/commontools/commontoolsinc.labs.2` (and likewise "labs G3" → 
`/Users/ianh/dev/commontools/commontoolsinc.labs.G3`).

When starting a new session, immediately git fetch and switch to a new branch rebased onto the tip of tree, so 
that you have the full context of the entire repo, and state unambiguously "I am using labs XX." where XX is the 
labs suffix.

Repos with two character names (e.g. labs F0, labs R4, labs 12) are worktrees. They rebase often. Do not rely on 
upstream/main being stable.

(The loom vendored copy is a [separate concern](loom-vendor-labs-separate.md).)


## Fetching

When you need to see if a labs repository is up to date, use `git fetch upstream`, not just `git fetch`, because 
the fork (`origin`) is very likely out of date (especially its `main` branch).


## Pushing

In the labs repo, your branches and every PR head live in the fork, which is the `origin` remote. The `upstream` 
remote is `commontoolsinc/labs` and is read-only for you: never push a branch there. Always name both the remote 
and the branch — a bare `git push` follows the branch's tracking ref, which points at `upstream/main` because that 
is where you branched from.


## The /Users/ianh/dev/commontools/commontoolsinc.labs.* repos are clones of forks

https://github.com/Hixie/commontoolsinc.labs is a fork of https://github.com/commontoolsinc/labs

The local clones are clones of the fork; `git remote -v` will say this in those directories:

```
origin	git@github.com:Hixie/commontoolsinc.labs.git (fetch)
origin	git@github.com:Hixie/commontoolsinc.labs.git (push)
upstream	git@github.com:commontoolsinc/labs.git (fetch)
upstream	git@github.com:commontoolsinc/labs.git (push)
```

When rebasing, `git fetch` and then rebase against `upstream/main`. The `origin/main` branch is stale and 
irrelevant; use `upstream/main` as the source of truth.

When pushing, use branches go on the `origin` remote, not the `upstream` remote; `origin` is where your branches 
and PR heads live, and is the only remote you push to.

When generating PR URLs, they should be based on the `upstream` org, not the `origin` org, if both are present.
