# settings
Random configuration files that I use.

Each top-level directory holds the settings for one kind of machine:

* `common-fabric` has the settings I use for working on Common Fabric:
  the instructions for coding agents in `system-prompts`, and zsh's
  startup files and the personal commands that go in `~/bin` in `shell`.
  Secrets stay out of this repository: `shell/.zshenv` reads the GitHub
  token from the login keychain, and names other keys by the paths of
  files kept elsewhere.

* `linux-workstation` has the X11 settings for a Linux workstation.

`./install DIRECTORY` puts a hard link in the home directory to each of
the files in that directory that git tracks, so editing `~/.zshrc` in
place, for example, edits the copy here. Run it again after git changes
those files, because git replaces a file when it changes it. A file named
`install-targets` says where the files beside it go, if anywhere; the
comment at the top of `install` explains how.

See also https://github.com/Hixie/usable-git
