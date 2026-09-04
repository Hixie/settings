# INFRA worktrees

When working in the commontoolsinc/infra repo, use a worktree in: ~/dev/commontools/infra/

NEVER EVER DEPLOY ANYTHING UNTIL THE CORRESPONDING INFRA REPOSITORY CHANGES HAVE LANDED ON GITHUB.

## Specified worktree

If you are told to "use INFRA123" where "123" is some decimal number, e.g. "use INFRA2", then use that directory 
in ~/dev/commontools/infra/, e.g. ~/dev/commontools/infra/INFRA2.

If that directory exists, use it directly; git fetch and create a new branch synced to tip of tree.

If that directory does not exist, create it as a worktree parented to: ~/dev/commontools/infra/root

## Unspecified worktree

When you find you need to work in the infra repo but have not been specified a particular worktree, create a new 
one by creating the INFRA subdirectory next lowest decimal number that does not already exist. For example, if 
there are INFRA1 and INFRA2, you would create INFRA3. Act as described above for using a specified worktree, with 
the one you have selected.

## Rules for using the infra repo

Never deploy something that has not already landed upstream in the relevant repo.

Read the /README.md file in the root of the repo for orientation.

Read the /CLAUDE.md file in the root of the repo for repo-specific instructions.

Report inconsistencies and errors you run into that are not related to your specific work.
