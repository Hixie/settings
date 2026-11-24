#!/usr/bin/env python3
"""Cases for send-pr, which finds the session working on a pull request by
the worktree identifier of the pull request's checkout.

Run it with no arguments. Each case makes a home directory with checkouts,
records of running Claude sessions, and records the Claude app keeps of
stopped sessions, puts a stand-in for pr-worktree there that answers with
the case's checkout, and runs send-pr -n, which describes the session it
finds without sending anything. It reports one line per case. The exit
status is 0 when every case passed and 1 otherwise.
"""

import json
import os
import subprocess
import sys
import tempfile

SEND_PR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "bin", "send-pr")

URL = "https://github.com/commonfabric/cfs/pull/1"

FOLDERS = ["dev/commonfabric/labs/C1", "dev/commonfabric/cfs/E3",
           "dev/commonfabric/weaver/A1"]

# Symbolic links from the former names of renamed repositories.
LINKS = {"dev/commonfabric/loom": "cfs",
         "dev/commonfabric/commonfabric-weaver": "weaver"}

# Each case: a description, the checkout pr-worktree answers with, the titles
# of the running Claude sessions, the titles of stopped sessions the Claude
# app keeps records of, and a phrase send-pr's output is to carry.
CASES = [
    ("cfs worktree", "dev/commonfabric/cfs/E3", ["ℂE3: 🧱 Fix it"], [],
     "Claude session: ℂE3: 🧱 Fix it"),
    ("cfs worktree under its former mark", "dev/commonfabric/cfs/E3",
     ["𝛌E3: 🧱 Fix it", "E3: 🧱 Labs"], [],
     "no session lists ℂE3 in its title"),
    ("cfs worktree under its former Greek mark", "dev/commonfabric/cfs/E3",
     ["C1, λE3: 🧱 Fix it"], [], "no session lists ℂE3 in its title"),
    ("cfs worktree through its former directory", "dev/commonfabric/loom/E3",
     ["ℂE3: 🧱 Fix it"], [], "Claude session: ℂE3: 🧱 Fix it"),
    ("cfs worktree listed under a mark of no repository",
     "dev/commonfabric/cfs/E3", ["ℭE3: 🧱 Fix it"], [],
     "no session lists ℂE3 in its title"),
    ("cfs worktree beside its former mark", "dev/commonfabric/cfs/E3",
     ["ℂE3: 🧱 Fix it", "𝛌E3: 🧱 Fix it again"], [],
     "Claude session: ℂE3: 🧱 Fix it"),
    ("cfs worktree in two titles", "dev/commonfabric/cfs/E3",
     ["ℂE3: 🧱 Fix it", "C1, ℂE3: 🧱 Fix it again"], [],
     "several sessions list ℂE3"),
    ("weaver worktree", "dev/commonfabric/weaver/A1", ["ωA1: 🧱 Fix it"], [],
     "Claude session: ωA1: 🧱 Fix it"),
    ("weaver worktree through its former directory",
     "dev/commonfabric/commonfabric-weaver/A1", ["ωA1: 🧱 Fix it"], [],
     "Claude session: ωA1: 🧱 Fix it"),
    ("labs worktree", "dev/commonfabric/labs/C1",
     ["ℂC1: 🧱 Other", "C1: 🧱 Fix it"], [], "Claude session: C1: 🧱 Fix it"),
    ("stopped session", "dev/commonfabric/cfs/E3", [],
     ["ℂE3: 🧱 Fix it", "ℂE4: 🧱 Other"], "local_0  ℂE3: 🧱 Fix it"),
    ("stopped session under the former mark", "dev/commonfabric/cfs/E3", [],
     ["𝛌E3: 🧱 Fix it"], "no session lists ℂE3 in its title"),
]


def send_pr(checkout, running, stopped):
    """Runs send-pr -n with pr-worktree answering CHECKOUT, a folder under
    the home directory, while Claude sessions with the titles RUNNING run,
    and the Claude app keeps records of stopped sessions with the titles
    STOPPED. Returns what send-pr wrote, on both its outputs."""
    with tempfile.TemporaryDirectory() as directory:
        home = os.path.realpath(directory)
        for folder in FOLDERS:
            os.makedirs(os.path.join(home, folder))
        for link, target in LINKS.items():
            os.symlink(target, os.path.join(home, link))
        os.makedirs(os.path.join(home, "bin"))
        stub = os.path.join(home, "bin", "pr-worktree")
        with open(stub, "w") as f:
            f.write("#!/bin/sh\nprintf '%%s\\n' '%s'\n"
                    % os.path.join(home, checkout))
        os.chmod(stub, 0o755)
        os.makedirs(os.path.join(home, ".codex"))
        sessions = os.path.join(home, ".claude", "sessions")
        os.makedirs(sessions)
        processes = []
        records = os.path.join(home, "Library", "Application Support", "Claude",
                               "claude-code-sessions", "account", "org")
        os.makedirs(records)
        try:
            for number, title in enumerate(running):
                process = subprocess.Popen(["cat"], stdin=subprocess.PIPE)
                processes.append(process)
                with open(os.path.join(sessions, "%d.json" % process.pid),
                          "w") as f:
                    json.dump({"sessionId": "s%d" % number, "name": title}, f)
            for number, title in enumerate(stopped):
                with open(os.path.join(records, "local_%d.json" % number),
                          "w", encoding="utf-8") as f:
                    json.dump({"sessionId": "local_%d" % number,
                               "title": title}, f, ensure_ascii=False)
            environment = {key: value for key, value in os.environ.items()
                           if key not in ("CLAUDE_CONFIG_DIR", "CODEX_HOME")}
            run = subprocess.run([SEND_PR, "-n", URL], capture_output=True,
                                 text=True, env={**environment, "HOME": home})
        finally:
            for process in processes:
                process.stdin.close()
                process.wait()
        return run.stdout + run.stderr


def main():
    failures = 0
    for description, checkout, running, stopped, phrase in CASES:
        output = send_pr(checkout, running, stopped)
        passed = phrase in output
        failures += not passed
        print("%s %s" % ("PASS" if passed else "FAIL", description))
        if not passed:
            print("     expected %r in:\n     %s"
                  % (phrase, output.strip().replace("\n", "\n     ")))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
