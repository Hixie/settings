#!/usr/bin/env python3
"""PermissionDenied hook that appends the denial to
~/.claude/permission-denials.jsonl.

Reads the hook payload on stdin and writes it as one line of JSON, with a
"ts" field (UTC, to the second) placed first. Many sessions append to the
file at once, so each record goes out in a single write() on a descriptor
opened with O_APPEND; buffered writers split large records into several
writes, which interleave with other sessions' records.
"""

import datetime
import json
import os
import sys

LOG = os.path.expanduser("~/.claude/permission-denials.jsonl")

payload = json.load(sys.stdin)
ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
line = json.dumps({"ts": ts, **payload}, ensure_ascii=False) + "\n"
fd = os.open(LOG, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
try:
    os.write(fd, line.encode())
finally:
    os.close(fd)
