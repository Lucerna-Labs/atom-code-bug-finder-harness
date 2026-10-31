# Portable upload result

The GUI now imports app ZIPs into a managed `projects/<id>/files/` snapshot. A root `chaos-project.json` can register one or several runnable configurations; a ZIP without the manifest is stored for manual configuration. Saved configurations that use the imported snapshot are associated with it. Export creates a ZIP of the original imported file inventory plus all associated configurations, rewritten with relative paths.

Operational evidence:

- An integration test uploaded a ZIP built from a temporary ordinary-code project, removed the original source folder, then ran the imported target/checker successfully. The run produced all 10 expected witness replays from the earlier ordinary-code example.
- The test added a second saved check, exported both checks with the app files, reimported the bundle under a different ID, and ran it successfully again. A manifest-free upload was configured afterward, run and exported with its saved check.
- The live GUI accepted [the sample ZIP](examples/ordinary_code_bundle.zip), created the `sample-upload` config, displayed its copied project, ran it to completion with first-hit scores 11/7 and 10 saved witnesses, and downloaded a bundle. The final downloaded bundle contains exactly three original source files plus `chaos-project.json`; generated `__pycache__` output was excluded. The browser console showed no errors. An MCP client listed and ran the imported `sample-upload` config, reaching the same 10 replays.
- Seven hostile ZIP cases were rejected: parent-path escape, absolute path, backslash path, link, high expansion ratio, non-object manifest and oversized manifest. The importer also enforces archive and expanded-size limits, file count and per-file size. Export refuses a changed imported source file. The source inventory and SHA-256 hashes are in each imported project's metadata.

The export is portable **between installations of this benchmark** when the destination machine has the necessary runtime and app dependencies. It does not carry Python/Node/system libraries or previous run receipts. No uploaded code executes during import. Real app support still needs a target wrapper and independent checker; the manifest can include them and their saved test configurations. See [PORTABLE-UPLOAD.md](PORTABLE-UPLOAD.md) for the bundle format and UI steps.

Validation entry point: `python3 tests/upload_portable.py`. The result is scoped to the tested Python example and the stated ZIP boundary; it does not prove arbitrary applications will run without their environment.
