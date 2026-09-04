# loom/vendor/labs is an unrelated vendored copy; don't edit it when working in the labs repo

`loom/vendor/labs/` (under /Users/ianh/dev/commontools) is an unrelated 
vendored copy of the labs repo for use by loom. When working on the labs 
repo (`/Users/ianh/dev/commontools/commontoolsinc.labs`), do NOT edit, 
sync, or touch files under `loom/vendor/labs/` — even if they mirror a 
file being changed.

**Why:** It is a separate consumer's vendored snapshot, not a mirror to 
keep in sync.

**How to apply:** Confirm the working path is of the form 
`commontoolsinc.labs.X` and ignore identical paths under 
`loom/vendor/labs/`.
