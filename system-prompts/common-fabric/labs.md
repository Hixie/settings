# Labs repositories

## The labs repo is a fork

The labs repository is a fork; `git remote -v` will say this in labs worktrees:

```
origin	git@github.com:Hixie/commontoolsinc.labs.git (fetch)
origin	git@github.com:Hixie/commontoolsinc.labs.git (push)
upstream	git@github.com:commonfabric/labs.git (fetch)
upstream	git@github.com:commonfabric/labs.git (push)
```

## Fetching, rebasing

When you need to see if a labs repository is up to date, use `git fetch upstream`, not just `git fetch`, because 
the fork (`origin`) is very likely out of date (especially its `main` branch); the `origin/main` branch is stale 
and irrelevant; use `upstream/main` as the source of truth.


## Pushing

In the labs repo, your branches and every PR head live in the fork, which is the `origin` remote. The `upstream` 
remote is `commonfabric/labs` and is read-only for you: never push a branch there. Always name both the remote and 
the branch — a bare `git push` follows the branch's tracking ref, which points at `upstream/main` because that is 
where you branched from.


## Selecting labs worktrees

When selecting a labs worktree (e.g. to [start a new session](starting-new-sessions.md)), use worktrees that start 
with a digit for Codex and a worktree that starts with a letter for Claude.

Where relevant, prefer the following associations:

- labs 1 to labs 9: for use by Codex for [production and red main fixes](prodred.md).
- labs 10 to labs 7Z: for use by Codex.
- labs 80 to labs 8Z: for use by Codex for Dashboard-related work.
- labs 90 to labs 9Z: for use by Codex for deflaking.
- labs B0-BZ: for use by Claude for follow-up work from another session in the labs B or B0-BZ range.
- labs C0-CZ: for use by Claude for CFC-related work.
- labs D0-DZ: for use by Claude for Dashboard work.
- labs E0-EZ: for use by Claude for [production and red main fixes](prodred.md) and other bug fixing tasks.
- labs F0-FZ: for use by Claude for dealing with flakes (including those found during babysitting).
- labs G0-GZ: for use by Claude for technical debt work.
- labs L0-LZ: for use by Claude for feature work that does not fit another category.
- labs R0-RZ: for use by Claude for regression-related work (especially performance-related work).
- labs T0-TZ: for use by Claude for timeout-related, sleep-related, or retry-loop-related issues.
- labs U0-UZ: for use by Claude for user-facing improvements.
- labs Z0-ZZ: for use by Claude for work related to `cf view`.


## Start/stop local dev servers with offset

When working in a labs worktree, start and stop the local Common Fabric dev servers with a port offset (expressed 
as a decimal number) strictly equal to the worktree code XX interpreted as a base36 number. For example, labs 4 
uses `--port-offset 4`; labs G uses `--port-offset 16`; labs R2 uses `--port-offset 974`:

  `./scripts/start-local-dev.sh --port-offset N`
  `./scripts/stop-local-dev.sh --port-offset N`

`restart-local-dev.sh` and `check-local-dev.sh` accept the same flag.

The offset shifts the shell/toolshed/inspector ports off their shared base so the running copies don't collide on 
the same ports.


# Relationship to loom

The loom vendored copy of labs is a [separate concern](loom-vendor-labs-separate.md).
