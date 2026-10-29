# Dogfood

~/dev/commonfabric/dogfood/ holds the Common Fabric instance the user has for real work. It contains two clones, 
both from the `commonfabric` GitHub organisation over SSH:

- `commonfabric-weaver` — the Weaver app.

- `loom` — the Common Fabric Service (CFS). This is the backend the Weaver reads from. It runs as a Loom instance
  named `dogfood` at port offset 0, which is the slot the Weaver connects to by default.

Nobody develops in these clones. Never commit, branch, or edit files in them. Each clone should always be 
pristine: on `main`, identical to `origin/main` for `commonfabric-weaver` and identical to `origin/main-green` for 
`loom`, with no local modifications. Development happens in other worktrees; leave those alone.

When using these directories, e.g. as part of updating dogfood as described below, your worktree identifier is 
"dogfood".

## Updating the Common Fabric Weaver

When asked to update the dogfood Weaver, bring the installed Weaver up to date with `main` and confirm that it is 
running, by following these steps:

1. Check the `~/dev/commonfabric/dogfood/commonfabric-weaver` and `~/dev/commonfabric/dogfood/loom` worktrees. If 
they are not pristine, find out why before you change anything. One known cause: opening the Xcode project in the 
Xcode app rewrites the project file. The repository forbids hand-editing that file, because it is generated from a 
spec. Copy any modified file to a scratch location, then restore the committed version with `git show HEAD:<path> 
> <path>`. Do not use `git checkout`, `git restore` or `git stash`. Report what you found.

2. Fetch and fast-forward `main` from `origin` in `~/dev/commonfabric/dogfood/commonfabric-weaver`. If nothing is 
new and the installed build already matches `main`, say so and skip steps 4 to 6 below. (Do not do this for the 
`loom` repository.)

3. Run `git -C ~/dev/commonfabric/dogfood/loom rev-parse HEAD` in `~/dev/commonfabric/dogfood/loom` to save the 
starting commit, then run `loom update dogfood` (without using `git fetch` et al). It will do the right thing 
(moving to the latest `main-green` branch commit). After that runs, check the results with `loom status dogfood` 
and `loom doctor`.

4. Read what changed before you build. Skim the commit subjects since the last build. Reread anything that touched 
the build and deploy instructions: `README.md`, `AGENTS.md`, `docs/agents/`, and the skills under 
`.claude/skills/` (especially the machine-setup and team-setup skills). Those documents are the source of truth 
for how to build. If they differ from what you did last time, or if this is your first time, follow them.

5. Build and install for this Mac only, using whatever local-only deploy path the repository currently documents. 
The normal build is signed with the company team. The user's Apple account is an App Manager on that team, and 
this Mac is registered. Another session may hold locks that block parts of the build; wait for it. Never break a 
lock or kill another session's processes. Do not open the project in the Xcode app.

6. Verify the result; do not trust the script's exit code alone. Confirm that the build succeeded, that the 
installed app carries this build's stamp, that its signature names the team rather than an ad-hoc signature, and 
that the app is running. Then confirm that it is talking to the service: the app has a local status route, which 
the repository documents. A build that installs cleanly but fails to launch is a known failure; check for it 
specifically.

7. Report back on the updates to both repositories. Give the build stamp and the commit it was built from. Then 
list the user-visible changes since the last build, in plain words, a few lines at most. Mention anything that 
affects the user or is addressed to the user.

Contrary to other documentation, on this machine we do not enable Full Disk Access for Weaver (this is to test 
what happens when it is not enabled).

## When something fails

- Report failures exactly as they happened, with the error text. Never install a stale build, and never describe a 
failed deploy as a success.

- If signing fails, look up the symptom in the troubleshooting table in the repository's machine-setup 
documentation before investigating further. Anything that needs Apple account changes, Xcode sign-in, or passwords 
is the user's to do. Give the user an overview of what needs to happen, then tell the user exactly what one step 
to take, one step at a time.

- The repository documents an unsigned, ad-hoc-signed build for when team signing is unavailable. Use it only as a 
stated fallback, never silently. Label every stamp from it as ad hoc, and list what does not work in that build.

- For a problem in the repositories themselves, not in this instance, report it and follow the team's usual 
channels ([production issues process](prodred.md), [flakes process](flakes.md), the [topics board](topics.md)) 
rather than fixing it here.

- Do not manually fix anything about the dogfood instance's data. The user wants the dogfood build to represent 
the most normal usage situation, so any problems with the configuration have to be resolved by changing the code 
for all users, not just tweaking settings or data locally.

## Waiting

Wait on something that belongs to your own session: the log line your own command writes when it finishes, or a 
PID you captured when you launched it. Never use a process-name pattern; many sessions on this machine run the 
same commands.
