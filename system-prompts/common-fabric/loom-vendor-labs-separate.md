# loom/vendor/labs is a separate vendored copy; don't edit it when working in the labs repo

The checkouts matching `~/dev/commonfabric/loom/*/vendor/labs/` are separate vendored copies of the labs repo for 
use by the Common Fabric Service (loom repo). When working on the labs repo (`~/dev/commonfabric/labs/XX`), do NOT 
edit, sync, or touch files under any `loom/vendor/labs/` directory — even if they mirror a file being changed. It 
is a separate consumer's vendored snapshot, not a mirror to keep in sync.
