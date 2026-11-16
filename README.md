# settings
Random configuration files that I use.

`shell` has zsh's startup files and the personal commands that go in
`~/bin`. `shell/install.sh` links each of them into place with a symbolic
link, so editing `~/.zshrc` edits the copy here. Secrets stay out of this
repository: `zshenv` reads the GitHub token from the login keychain, and
names other keys by the paths of files kept elsewhere.

`system-prompts` has the instructions for coding agents.
`system-prompts/install.sh DIRECTORY` links one set of them into place.

See also https://github.com/Hixie/usable-git

