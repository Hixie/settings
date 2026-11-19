# The settings repo

This is the repository that stores the source of your global instructions.

This repo only uses the `main` branch, never add another branch.

Never edit this repository without explicit approval. If you think you have approval, write a paragraph that just 
says "☢️ EDITING SETTINGS! ☢️" before editing the files.

It often has uncommitted files; do not touch them. If you need to edit one of the files that is uncommitted, ask 
the user for guidance.

Never edit files in ~/.claude/ or ~/.codex/ directly; do it via this repository instead.

`./install common-fabric` puts a hard link in the home directory to each file in `common-fabric` that an 
`install-targets` file covers: the agent instructions go in ~/.claude/ and ~/.codex/, zsh's startup files from 
`common-fabric/shell` go in ~/, and the commands in `common-fabric/shell/bin` go in ~/bin. Editing one of those 
installed files in place therefore edits this repository, and the rules above apply. Git replaces a file when it 
changes it, which leaves the installed copy behind, so run `./install common-fabric` again after git changes, adds 
or renames a file there; the comment at the top of `install` explains how the `install-targets` files say where 
each file goes. (Claude's Edit tool similarly breaks the hard links.) Never put a secret in these files; for 
example, `common-fabric/shell/.zshenv` reads the GitHub token from the login keychain.

Claude Code mods (plugins that change the interface or behavior of Claude Code) for this machine go in 
`common-fabric/system-prompts/claude/mods/<mod-name>/`. The empty `install-targets` file in `mods` keeps `install` 
from linking that directory into ~/.claude/. Instead, Claude Code loads each mod from the checkout. To enable a 
mod, add the absolute path of its folder to `CLAUDE_CODE_PLUGIN_DIRS` in the `env` block of `claude/settings.json`. 
Separate several paths with colons. Sessions started after that change load the mod. The desktop app's sessions 
reload a mod when its files change only if that `env` block also sets `CLAUDE_CODE_PLUGIN_DIR_WATCH` to `1`.
