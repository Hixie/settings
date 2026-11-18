# User live instances of the weaver

The user has two builds they use for direct testing, dogfood and fishfood. They are in their own directories, 
which each contain two clones, both from the `commonfabric` GitHub organisation over SSH:

- `commonfabric-weaver` — the Weaver app.

- `loom` — the Common Fabric Service (CFS). This is the backend the Weaver reads from.

Nobody develops in these clones. Never commit, branch, or edit files in them. Each clone should always be 
pristine: on `main`, with no local modifications, at the commit its configuration below names. Development happens 
in other worktrees; leave those alone.


## Dogfood configuration

~/dev/commonfabric/dogfood/ holds the Common Fabric instance the user has for real work.

The CFS in this directory runs as a Loom instance named `dogfood`. All settings other than the instance name 
should be the defaults, including using port offset 0, which is also the slot the Weaver connects to by default, 
and the default `--channel`. Its `commonfabric-weaver` clone is identical to `origin/main`, and its `loom` clone 
is identical to `origin/main-green`.

When using these directories, e.g. as part of updating dogfood as described below, your worktree identifier is 
"dogfood".


## Fishfood configuration

~/dev/commonfabric/fishfood/ holds the Common Fabric instance the user has for bleeding edge testing. It runs the 
code the rapids release channel runs, but from these ordinary clones and with ordinary commands. Never use `loom 
channel` or `loom setup --channel` for it: they clone a separate checkout under `~/.local/share/loom/channels/` 
and install a downloaded Weaver.

The CFS runs as a Loom instance named `fishfood`, bound to `~/dev/commonfabric/fishfood/loom`, at port offset 1. 
Port offset 3 cannot be used: it puts the local server on port 9903, which the dogfood Weaver's gateway holds. 
Fishfood signs with the same machine-wide identity key as dogfood, `~/.config/commonfabric/identity.key`. Its home 
is on rapids (`https://rapids.saga-castor.ts.net`), where dogfood's is on estuary. It shares the machine's native 
sandbox install with dogfood.

The clones follow the rapids release, not the branch tips. The current release is `releases/rapids.json` on the 
`main` branch of `commonfabric/infra`. Its `loom.sha` is the commit for the `loom` clone, and its `weaver.sha` is 
the commit for the `commonfabric-weaver` clone. The Labs commit comes with the Loom commit, which vendors it.

Fishfood has no Weaver yet. Its Weaver is to be "Weaver (Rapids)", bundle identifier 
`com.commontools.CommonFabricWeaver.channel.rapids`, built from the fishfood clone and installed beside the 
ordinary app. That needs two code changes that have not landed: a local build of channel Weaver apps in the 
Weaver repository, and a way for Loom to admit and bind such an app to an instance that is not on a channel. Until 
both land, do not build a Weaver from the fishfood clone. The repository's deploy script builds the ordinary app 
and would replace dogfood's `/Applications/Common Fabric Weaver.app`.

When using these directories, e.g. as part of updating fishfood as described below, your worktree identifier is 
"fishfood".


## Updating the Common Fabric Weaver

When asked to update the dogfood or fishfood Weavers, bring the relevant installed Weaver up to date and confirm 
that it is running, by following these steps ($FOOD is "dogfood" or "fishfood" as appropriate):

1. Check the `~/dev/commonfabric/$FOOD/commonfabric-weaver` and `~/dev/commonfabric/$FOOD/loom` worktrees. If 
they are not pristine, find out why before you change anything. One known cause: opening the Xcode project in the 
Xcode app rewrites the project file. The repository forbids hand-editing that file, because it is generated from a 
spec. Copy any modified file to a scratch location, then restore the committed version with `git show HEAD:<path> 
> <path>`. Do not use `git checkout`, `git restore` or `git stash`. Report what you found.

2. Bring the `commonfabric-weaver` clone to its target commit. For dogfood, fetch and fast-forward `main` from 
`origin`. For fishfood, read the current rapids release with `gh api 
'repos/commonfabric/infra/contents/releases/rapids.json?ref=main' -H 'Accept: application/vnd.github.raw+json'`, 
fetch, confirm that its `weaver.sha` is on `origin/main`, and move `main` there with `git reset --keep`. If nothing 
is new and the installed build already matches that commit, say so and skip steps 4 to 6 below.

3. Run `git -C ~/dev/commonfabric/$FOOD/loom rev-parse HEAD` to save the starting commit. For dogfood, then run 
`loom update dogfood` (without using `git fetch` et al). It will do the right thing (moving to the latest 
`main-green` branch commit). For fishfood, fetch in the `loom` clone, confirm that the release's `loom.sha` is on 
`origin/main-green`, move `main` there with `git reset --keep`, and then run `./src/bin/loom update fishfood 
--skip-pull` from the clone. Never run `loom update fishfood` without `--skip-pull`: it would move the clone to the 
tip of `main-green`, past the release. When the Labs pin moves, the update recompiles Labs' code cache, which can 
print nothing for more than ten minutes. After the update runs, check the results with `loom status $FOOD` and 
`loom doctor`.

4. For fishfood, skip steps 4 to 6 until its Weaver can be built, as "Fishfood configuration" above explains, and 
report the commits that both clones moved to. Read what changed before you build. Skim the commit subjects since the last build. Reread anything that touched 
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

- Do not manually fix anything about these instances' data. The user wants these builds to represent the most 
normal usage situation, so any problems with the configuration have to be resolved by changing the code for all 
users, not just tweaking settings or data locally.


## Waiting

Wait on something that belongs to your own session: the log line your own command writes when it finishes, or a 
PID you captured when you launched it. Never use a process-name pattern; many sessions on this machine run the 
same commands.
