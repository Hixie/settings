# Loom worktrees

## Table of contents

- Table of contents
- Create a worktree
- Prepare the worktree
- Run a persistent side-by-side instance
- Keep ports unique
- Run short-lived live tests
- Remove a persistent instance and worktree

Read each section when it becomes relevant. Each section starts with its name prefixed by "##" and ends with two 
blank lines, just like this section did.


## Create a worktree

Use `~/dev/commontools/loom` as the parent repository for every Loom worktree.
Create the worktrees under `~/dev/commontools/loom-worktrees`. Do not create
sibling worktrees from another worktree, and do not edit the vendored Loom
checkout under a Labs repository.

Choose one short, descriptive name for the worktree, branch, and any Loom
instance that will run from it. Instance names must contain only lowercase
letters, numbers, and hyphens.

Start a new branch from the current remote `main` branch:

```bash
git -C ~/dev/commontools/loom fetch origin
git -C ~/dev/commontools/loom worktree add \
  -b banana \
  ~/dev/commontools/loom-worktrees/banana \
  origin/main
```

If the branch already exists locally, omit `-b` and name the existing branch
as the final argument:

```bash
git -C ~/dev/commontools/loom worktree add \
  ~/dev/commontools/loom-worktrees/banana \
  banana
```

Use the parent repository for later worktree operations too. This keeps all
worktree administration anchored in one stable checkout.


## Prepare the worktree

A code-only worktree does not need a running Loom instance. Before binding a
Loom instance, prepare the checkout from inside the worktree:

```bash
cd ~/dev/commontools/loom-worktrees/banana
.ops/bin/prepare-instance-target.sh
```

This command materializes the worktree-local vendored repositories, installs
the runtime Python dependencies into the worktree's `.venv`, creates the local
log directory, and checks that the checkout is ready. Keep these generated
files local to the worktree. Do not share `vendor`, `.venv`, or `.ops/logs`
between worktrees.

Run the read-only check when investigating a worktree that may already be
prepared:

```bash
.ops/bin/prepare-instance-target.sh --check
```


## Run a persistent side-by-side instance

Give every simultaneously running worktree its own named Loom instance:

```bash
loom instance create banana --worktree .
loom setup --instance banana
```

The first command binds the instance to the current worktree. It also gives
the instance its own state directory, File Cabinet path, Browser Access
profile, launchd services, and port offset. The setup command performs the
interactive first-time configuration and leaves the services running.

If the instance is already configured, start it without repeating setup:

```bash
loom start banana
```

Run instance-specific commands from inside the bound worktree whenever
possible. Loom resolves the instance from the current worktree. When running a
command elsewhere, pass the instance name explicitly.


## Keep ports unique

Do not assign service ports individually. Let `loom instance create` choose
the next unused port offset from Loom's machine-wide instance registry. Loom
adds that offset to every service's base port, including the toolshed, shell,
dashboard, local Loom server, and Browser Access port. One unique offset
therefore gives the instance a complete non-overlapping port set.

The registry also prevents an explicit offset from being assigned to two
instances and prevents one worktree from being bound to two active instances.
Do not copy an instance directory or `pieces.json` from another worktree. Do
not hand-edit an instance's port values.

Inspect the allocation after creating or removing an instance:

```bash
loom instance ls
loom instance cat banana
```

`loom instance ls` shows each instance's worktree and port offset. `loom
instance cat` shows the exact configured URLs. If an external process occupies
one of those ports, remove the new instance and create it again with an
explicit unused offset:

```bash
loom instance rm banana
loom instance create banana --worktree . --port-offset 12
```

Choose the explicit offset only after checking `loom instance ls`. The create
command rejects an offset already registered to another Loom instance.


## Run short-lived live tests

Use an acceptance instance instead of a persistent development instance when
the goal is to test a feature branch against realistic data:

```bash
cd ~/dev/commontools/loom-worktrees/banana
loom acceptance up --worktree .
loom acceptance list
```

The acceptance command selects an available acceptance slot, creates an
isolated copy-on-write File Cabinet clone, pauses wish dispatch, disables
hosted push, and reports the instance's URLs. It leaves the primary Loom
instance bound to the parent repository. Do not rebind the protected primary
instance to a feature worktree.

When finished, use the instance name reported by `loom acceptance list`:

```bash
loom acceptance down banana
```


## Remove a persistent instance and worktree

Stop and unregister the instance before removing its worktree:

```bash
loom stop banana --include-toolshed
loom instance rm banana
git -C ~/dev/commontools/loom worktree remove \
  ~/dev/commontools/loom-worktrees/banana
git -C ~/dev/commontools/loom worktree prune
```

`loom instance rm` preserves the instance's data. Use `--purge` only when the
File Cabinet is the instance's default unshared directory and that data should
also be deleted. Git refuses to remove a worktree with uncommitted changes, so
inspect and preserve any work before cleanup.


