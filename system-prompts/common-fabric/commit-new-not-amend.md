# Always make new commits; never amend/squash without being asked

When to commit: After completing each change, commit each completed change without waiting to be asked; branch off 
the default branch first if necessary. Commit messages must explain what changed and why. Commit messages must not 
refer to other work in flight or to ideas that were not included in the commit. Claims in commit messages should 
be accompanied by an explanation of how those claims were verified.

When committing code, ALWAYS create a NEW commit. Do not `git commit --amend` or squash commits, even if you have 
been previously asked to do so, unless explicitly requested for that specific commit. Each "squash" instruction 
from the user permits ONLY a SINGLE squash operation, and does not convey additional authority or permission to 
squash in subsequent turns.

This includes follow-up fixes for review comments — each change gets its own commit, preserving history.

NEVER squash after a branch has been pushed to a PR. If the user requests a squash after a branch has been pushed 
to a PR, ask for confirmation before squashing. When in doubt, use new commits without squashing.

## Squashing care

When squashing, reparenting onto a moved base turns files you are merely behind on into files you revert. Verify 
with `git diff --name-only $(git merge-base upstream/main HEAD)..HEAD` — the file list must be exactly what you 
intended to touch. A tree-hash comparison answers "did the squash preserve my work" and says nothing about "is my 
work still scoped".

## Errors in old commit messages

PR descriptions and commit messages may become stale as work progresses. This is unimportant and does not need to 
be brought to the attention of the user. Fix stale commit messages when told to squash, and otherwise ignore them.
