# Upload an app and carry its tests with it

Open [the local GUI](http://127.0.0.1:8765), choose **Upload an app copy**, enter a project ID, and select a ZIP of the app. The GUI keeps an extracted snapshot under `projects/<id>/files/`. Runs use that snapshot and no longer read the upload source path. Imported apps appear in the **Imported apps** panel; **Download bundle** exports the original imported files and all associated saved checks as a ZIP that another installation of this benchmark can import.

You can try the complete workflow with [the sample ZIP](examples/ordinary_code_bundle.zip). It contains the ordinary Python example, a target wrapper, an independent checker and a `chaos-project.json` manifest. Importing it creates a runnable saved configuration automatically. Click **Start matched run** after upload. An imported ZIP without a manifest is still stored; click **Configure** to prefill the config editor, then set the wrapper, checker, input grammar and labeled controls before saving. Saving a config whose working directory and declared source files are inside the imported snapshot attaches it to that project for later export.

The optional root-level manifest is JSON:

```json
{
  "format": "chaos-project-v1",
  "config": {
    "name": "my-app-check",
    "cwd": ".",
    "target_command": ["python3", "target_jsonl.py"],
    "checker_command": ["python3", "checker_jsonl.py"],
    "source_paths": ["program.py", "target_jsonl.py", "checker_jsonl.py"],
    "timeout_seconds": 2,
    "seeds": [11, 23, 37],
    "calls_per_seed": 100,
    "grammar": {
      "type": "array", "min_length": 0, "max_length": 8,
      "items": {"type": "int", "min": 0, "max": 5}
    },
    "controls": [
      {"request": [], "violation": false},
      {"request": [1, 1], "violation": true}
    ]
  }
}
```

`cwd` and `source_paths` in the manifest are relative to the ZIP root. Commands run from `cwd`. For several checks, use `"configs": [<config>, <config>]` instead of one `"config"`; all saved checks are restored on import. A command may name a runtime installed on the destination computer, such as `python3`, but source file arguments and declared source files must be included in the ZIP for the bundle to be independent of the original app path.

**Portable scope:** the bundle carries imported files and saved test configurations. It does not package Python, Node, system libraries, a virtual environment, or run receipts. Those runtimes and dependencies must exist on the destination machine. If an app needs generated files, include them in the uploaded ZIP; export intentionally includes the original imported inventory and excludes artifacts generated during a test. Export refuses to package an imported source file whose content changed after upload, so the saved snapshot cannot silently drift.

The importer accepts ZIP files up to 100 MiB compressed, 500 MiB expanded, 2,000 entries and 100 MiB per file. It rejects absolute or parent paths, duplicate and case-colliding names, symlinks, encrypted or special entries, and extreme expansion ratios. The app never runs during import. The GUI stays bound to the local machine; uploaded code runs only after a saved configuration is started by the user or an AI tool. This follows the size and path concerns in [OWASP's file upload guidance](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) and [Python's ZIP documentation](https://docs.python.org/3/library/zipfile.html).

`tests/upload_portable.py` proves import → delete original source → run → export all checks → reimport → run. It also tests a ZIP without a manifest, manual configuration and five rejected unsafe archives. The browser upload, imported run and ZIP download were verified through the live GUI.
