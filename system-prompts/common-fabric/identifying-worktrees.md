# Identifying worktrees

## Common Fabric

The following are commonly-referenced Common Fabric repositories: labs, loom, commonfabric-weaver, infra, specs.

There are many more; to get a complete list, run: `(setopt bareglobqual; cd ~/dev/commonfabric; print -rl -- *(N/))`

All Common Fabric repositories on this machine use worktrees referenced by a one or two character alphanumeric 
worktree code, e.g. "2" or "X6" or "8A", representing a base 36 number. In the examples below, this is written as 
XX. Letters in these codes must be uppercase.

For a Common Fabric repository REPO, worktree XX, the directory to use is: ~/dev/commonfabric/REPO/XX/

These directories are configured as worktrees linked to a main worktree in ~/dev/commonfabric/REPO/root/

Do not create worktrees in the ~/dev/ directory hierarchy that do not match this pattern, even if requested; such 
a request would likely be a typo or user mistake.

For some repositories, the user might use a short name to abbreviate the full name. The "short name" column in the 
table below documents these. When referencing a worktree, rather than giving the full name or even the short name, 
use the worktree identifier described in the table below. Some repositories have additional rules, see the 
referenced files for those.

| Repository | Short name | Worktree identifier | Notes |
|--|--|--|--|
| labs | | XX | No prefix, just the worktree code. This repository [is a fork, not a straight clone, with special `--port-offset` rules and certain worktrees dedicated to certain tasks](labs.md). |
| loom | cfs | 𝛌XX | [The loom repository has a number of special rules needed to handle creation and cleanup](loom.md). |
| commonfabric-weaver | weaver | ωXX | [Certain weaver worktrees are dedicated to certain tasks](weaver.md). |
| infra | | INFRAXX | e.g. INFRA2; [never deploy infrastructure changes before they merge upstream](infra.md) |
| web-weaver | web | web-XX | e.g. web-A1 |
| all others | | REPO-XX | e.g. gvisor-82 |

For example, a user might say "use labs D0", and you would use "D0" as your worktree identifier.

The [`~/dev/commonfabric/dogfood` directory](dogfood.md) contains files not used for development. Never use these 
directories for making changes.

In cases where you need to read the latest content of a repository without modifying it, e.g. to read a skill from 
the labs repo, or to read the CFC specs, you may identify the "root" main worktree as the worktree to use; the 
worktree identifier in that case is the name of the repository (e.g. "labs", "specs"). You should fetch and rebase 
in those worktrees before using them (to ensure they are up to date, as these repos move fast), but make no other 
changes. If you decide to later make a change in such a repo, you must first identify a linked worktree to work 
from, as described below.


## Deno and related repositories

The denoland repository uses a similar configuration. ~/dev/denoland/root is the main worktree of 
~/dev/denoland/XX worktrees. The format of worktree identifiers for Deno worktrees is "denoXX", as in, "use 
deno2".

The cliffy repository has its main worktree at ~/dev/cliffy/root with worktrees at ~/dev/cliffy/XX and the 
convention is "cliffyXX".


## Other repositories

The contraptions, settings, and usable-git repositories are very different.

They are found in ~/dev/contraptions, ~/dev/settings, and ~/dev/usable-git and use the full repo name as the 
worktree identifier. There are no linked worktrees for these repos. They should always remain on the main branch. 
Work done on those repositories is done on the main branch. Only one session should ever be working in these 
repositories at a time. Do not create branches. Do not create worktrees. Never push from these repositories unless 
very explicitly requested; a push on main in these repositories is permanent and cannot be undone.


## Choosing a worktree

If you have not been given explicit instructions identifying a specific worktree, you may select an unused one for 
yourself.

An unused worktree is one that no other session (in Codex or Claude) is using, and that has no active work (you 
may `git fetch` and check if the latest branch has been merged to determine this).

Some repositories have specific guidelines for selecting worktrees, see notably the [labs](labs.md) and 
[weaver](weaver.md) worktrees. In the absence of any other guidelines, using two-character worktrees in the range 
10-9Z for Codex, and two-character worktrees in the range E0-VZ for Claude.


## Creating worktrees

Do not create worktrees other than those that follow the pattern described above and those required for 
[adversarial review](reviews.md) (those go in a temporary directory). Inform the user whenever you create a 
worktree outside of those in temporary directories. In normal operation, you should only need to create linked 
worktrees when instructed to use a worktree that does not yet exist; create it from the corresponding `root` main 
worktree.


## Branches

Any branch you expect the user to merge into the upstream repository must be checked out in a non-temporary 
worktree. If you have multiple branches for the user to merge upstream, then use multiple worktrees (this is an 
unusual situation).
