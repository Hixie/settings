# The settings repo

This is the repository that stores the source of your global instructions.

This repo only uses the `main` branch, never add another branch.

Never edit this repository without explicit approval. If you think you have approval, write a paragraph that just 
says "☢ EDITING SETTINGS! ☢" before editing the files.

It often has uncommitted files; do not touch them. If you need to edit one of the files that is uncommitted, ask 
the user for guidance.

Never edit files in ~/.claude/ or ~/.codex/ directly; do it via this repository instead.

The zsh startup files and personal commands also come from this repository, from its `shell` directory. 
~/.zshenv, ~/.zprofile, ~/.zshrc, and the commands in ~/bin other than profile-icon are symbolic links into it, so 
editing one of them edits this repository, and the rules above apply. After adding a file to `shell`, run 
`shell/install.sh` to link it into place. Never put a secret in these files: `shell/zshenv` reads the GitHub token 
from the login keychain.

After editing this repository's files, run the "install.sh" script to re-update the hardlinks.

Claude Code mods (plugins that change the interface or behavior of Claude Code) for this machine go in 
`system-prompts/common-fabric/claude/mods/<mod-name>/`. The "install.sh" script does not link that directory into 
~/.claude/. Instead, Claude Code loads each mod from the checkout. To enable a mod, add the absolute path of its 
folder to `CLAUDE_CODE_PLUGIN_DIRS` in the `env` block of `claude/settings.json`. Separate several paths with 
colons. Sessions started after that change load the mod. The desktop app's sessions reload a mod when its files 
change only if that `env` block also sets `CLAUDE_CODE_PLUGIN_DIR_WATCH` to `1`.
