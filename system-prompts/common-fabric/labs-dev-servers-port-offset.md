# start/stop local dev servers with offset

When working in a `commontoolsinc.labs.XYZ` workspace, always start and stop the local Common Fabric dev servers 
with a port offset (expressed as a decimal number) strictly equal to the copy number XYZ intepreted as a base36 
number — no exceptions, never a different value. For example, labs.4 uses `--port-offset 4; labs.G uses 
`--port-offset 16`; labs R2 uses `--port-offset 974`:

  `./scripts/start-local-dev.sh --port-offset N`
  `./scripts/stop-local-dev.sh --port-offset N`

`restart-local-dev.sh` and `check-local-dev.sh` accept the same flag.

**Why:** The labs copies are parallel ([[labs-parallel-copies]]); the offset shifts the shell/toolshed/inspector 
ports off their shared base so the running copies don't collide on the same ports.

**How to apply:** Always use the offset matching the current copy's N, never a different value, so the running 
copies never share a port.
