#!/usr/bin/env python3
"""Cases for l, which changes to the checkout a worktree identifier names.

Run it with no arguments. It makes a home directory holding the checkouts
the cases name, sources l there in zsh with each identifier, and checks the
directory l changed to, or that l refused the identifier. It reports one
line per case. The exit status is 0 when every case passed and 1 otherwise.

The checkouts are empty directories rather than git checkouts, so l ends by
running ll, and a stand-in for ll that prints nothing takes its place.
"""

import os
import subprocess
import sys
import tempfile

L = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "bin", "l")

FOLDERS = [
    "dev/commonfabric/labs/root", "dev/commonfabric/labs/C1",
    "dev/commonfabric/labs/W1", "dev/commonfabric/labs/D0",
    "dev/commonfabric/labs/LE", "dev/commonfabric/cfs/EL",
    "dev/commonfabric/cfs/root", "dev/commonfabric/cfs/1",
    "dev/commonfabric/cfs/E3", "dev/commonfabric/cfs/RM",
    "dev/commonfabric/cfs/FS",
    "dev/commonfabric/weaver/root", "dev/commonfabric/weaver/1",
    "dev/commonfabric/weaver/A1", "dev/commonfabric/web-weaver/root",
    "dev/commonfabric/web-weaver/A1", "dev/commonfabric/web-weaver/EB",
    "dev/commonfabric/crm/root", "dev/commonfabric/infra/2",
    "dev/commonfabric/gvisor/82", "dev/commonfabric/dogfood",
    "dev/denoland/5", "dev/cliffy/root", "dev/contraptions",
]

# Each identifier, and the folder under the home directory it names, or None
# when l is to refuse it.
CASES = [
    ("ℂE3", "dev/commonfabric/cfs/E3"),
    ("ℂe3", "dev/commonfabric/cfs/E3"),
    ("c1", "dev/commonfabric/cfs/1"),
    ("C1", "dev/commonfabric/labs/C1"),
    ("c", "dev/commonfabric/cfs/root"),
    ("cfs", "dev/commonfabric/cfs/root"),
    ("cfs-E3", "dev/commonfabric/cfs/E3"),
    ("loom", None),
    ("loom-E3", None),
    ("𝛌E3", None),
    ("λE3", None),
    ("lEL", None),
    ("le", "dev/commonfabric/labs/LE"),
    ("crm", "dev/commonfabric/crm/root"),
    ("cRM", "dev/commonfabric/cfs/RM"),
    ("cFS", "dev/commonfabric/cfs/FS"),
    ("ωA1", "dev/commonfabric/weaver/A1"),
    ("wa1", "dev/commonfabric/weaver/A1"),
    ("w1", "dev/commonfabric/weaver/1"),
    ("W1", "dev/commonfabric/labs/W1"),
    ("weaver", "dev/commonfabric/weaver/root"),
    ("weaver-A1", "dev/commonfabric/weaver/A1"),
    ("commonfabric-weaver-A1", "dev/commonfabric/weaver/A1"),
    ("web", "dev/commonfabric/web-weaver/root"),
    ("web-A1", "dev/commonfabric/web-weaver/A1"),
    ("INFRA2", "dev/commonfabric/infra/2"),
    ("gvisor-82", "dev/commonfabric/gvisor/82"),
    ("d0", "dev/commonfabric/labs/D0"),
    ("labs", "dev/commonfabric/labs/root"),
    ("deno5", "dev/denoland/5"),
    ("cliffy", "dev/cliffy/root"),
    ("contraptions", "dev/contraptions"),
    ("dogfood", "dev/commonfabric/dogfood"),
    ("ℭE3", None),
    ("μE3", None),
    ("ℂE3X", None),
    ("cE3X", None),
]


def change(home, identifier):
    """The directory l changes to for IDENTIFIER in the home directory HOME,
    or None when it refuses the identifier."""
    stubs = os.path.join(home, "stubs")
    run = subprocess.run(
        ["zsh", "-f", "-c", 'builtin source "$1" "$2" && print -r -- "$PWD"',
         "zsh", L, identifier],
        capture_output=True, text=True, cwd=home,
        env={**os.environ, "HOME": home,
             "PATH": stubs + os.pathsep + os.environ["PATH"]})
    if run.returncode != 0:
        return None
    return run.stdout.strip().splitlines()[-1]


def main():
    failures = 0
    with tempfile.TemporaryDirectory() as directory:
        home = os.path.realpath(directory)
        for folder in FOLDERS:
            os.makedirs(os.path.join(home, folder))
        os.makedirs(os.path.join(home, "stubs"))
        stub = os.path.join(home, "stubs", "ll")
        with open(stub, "w") as f:
            f.write("#!/bin/sh\n")
        os.chmod(stub, 0o755)
        for identifier, folder in CASES:
            expected = folder and os.path.join(home, folder)
            found = change(home, identifier)
            passed = found == expected
            failures += not passed
            print("%s %-24s %s" % ("PASS" if passed else "FAIL", identifier,
                                   os.path.relpath(found, home) if found
                                   else "refused"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
