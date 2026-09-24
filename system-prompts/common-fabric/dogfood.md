# Dogfood

~/dev/commonfabric/dogfood/ holds the Common Fabric instance the user has for real work. It contains two clones, 
both from the `commonfabric` GitHub organisation over SSH:

- `commonfabric-weaver` — the Weaver app.

- `loom` — the Common Fabric Service (CFS). This is the backend the Weaver reads from. It runs as a Loom instance 
  named `dogfood` at port offset 0, which is the slot the Weaver connects to by default.

Nobody develops in these clones. Never commit, branch, or edit files in them. Each clone should always be 
pristine: on `main`, identical to `origin/main`, with no local modifications. Development happens in other 
worktrees; leave those alone.

When using these directories, e.g. as part of updating dogfood as described below, your worktree identifier is 
"dogfood".

## Updating the Common Fabric Weaver

When asked to update or relaunch the dogfood Weaver bring the installed Weaver up to date with `main` and confirm 
that it is running.

1. **Check the checkout.** If it is not pristine, find out why before you change anything. One known cause: 
opening the Xcode project in the Xcode app rewrites the project file. The repository forbids hand-editing that 
file, because it is generated from a spec. Copy any modified file to a scratch location, then restore the 
committed version with `git show HEAD:<path> > <path>`. Do not use `git checkout`, `git restore` or `git stash`. 
Report what you found.

2. **Fetch and fast-forward** `main` from `origin`. These are plain clones, not forks. If nothing is new and the 
installed build already matches `main`, say so and stop.

3. **Read what changed before you build.** Skim the commit subjects since the last build. Reread anything that 
touched the build and deploy instructions: `README.md`, `AGENTS.md`, `docs/agents/`, and the skills under 
`.claude/skills/` (especially the machine-setup and team-setup skills). Those documents are the source of truth 
for how to build. If they differ from what you did last time, or if this is your first time, follow them.

4. **Build and install for this Mac only**, using whatever local-only deploy path the repository currently 
documents. The normal build is signed with the company team. The user's Apple account is an App Manager on that 
team, and this Mac is registered. Another session may hold locks that block parts of the build; wait for it. Never 
break a lock or kill another session's processes. Do not open the project in the Xcode app. Do not show windows 
other than the Weaver itself.

5. **Verify the result; do not trust the script's exit code alone.** Confirm that the build succeeded, that the 
installed app carries this build's stamp, that its signature names the team rather than an ad-hoc signature, and 
that the app is running. Then confirm that it is talking to the service: the app has a local status route, which 
the repository documents. A build that installs cleanly but fails to launch is a known failure; check for it 
specifically.

6. **Report back.** Give the build stamp and the commit it was built from. Then list the user-visible changes 
since the last build, in plain words, a few lines at most. Mention anything that affects the user or is addressed 
to the user.

## Updating the Common Fabric Service

Check the `dogfood` Loom instance with the `loom` command-line tool, whose reference is in the `loom` clone's 
documentation. If its clone is behind `origin/main`, update it using the update path that documentation describes, 
not by pulling and restarting by hand. Updating restarts the services. Afterwards, confirm that its status and 
diagnostics are healthy. If the Weaver shows its own prompt offering to update the service, that is the same 
update.

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

## Waiting

Wait on something that belongs to your own session: the log line your own command writes when it finishes, or a 
PID you captured when you launched it. Never use a process-name pattern; many sessions on this machine run the 
same commands.
