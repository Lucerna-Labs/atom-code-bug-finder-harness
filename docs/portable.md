# Imported app snapshots and portable bundles

## What import changes

The GUI accepts a ZIP and extracts a validated copy into `projects/<id>/files/`. Once a saved config points to that copy, runs no longer read the original upload path. Import never executes uploaded code. A ZIP with no manifest remains a stored snapshot until a developer creates a target/checker configuration. A root `chaos-project.json` with format `chaos-project-v1` can register one `config` or an array of `configs`; the GUI then shows them as runnable saved checks.

The project inventory records every imported file's size and SHA-256. Export uses that original inventory, so generated files such as Python `__pycache__` do not enter the bundle. It verifies those hashes and refuses export if an imported source changed. The ZIP it creates contains the imported files plus a regenerated manifest with paths relative to the ZIP root. Several checks attached to one app travel together.

## Why the ZIP limits exist

Archive names can escape their destination or shadow one another. The importer rejects absolute and parent paths, backslashes, duplicate or case-colliding names, symlinks, encrypted and special entries. It limits the upload to 100 MiB compressed, 500 MiB expanded, 2,000 entries, 100 MiB per file and a 64 KiB manifest, with an expansion-ratio check. Extraction goes into a generated staging directory and moves into the final project ID only after validation.

The browser server binds to loopback, and uploads require the local request header and same-origin check. The imported target and checker run later with the user's account permissions; the ZIP importer is not an execution sandbox.

## What portable means here

The bundle carries copied app files and test configurations. It does not bundle Python, Node, system libraries, virtual environments or previous run receipts. The destination machine needs the runtimes and dependencies used by the target. An absolute interpreter path in a config may need adjustment on another machine. `PORTABLE-UPLOAD.md` has the manifest shape and the tracked sample ZIP; `PORTABLE-UPLOAD-RESULT.md` records the import-after-source-removal and export/reimport tests.
