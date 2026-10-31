# Development guide

## Run locally

This is a Python 3.10+ project on Linux/Unix. The GUI, runner and MCP server use the standard library. Start the GUI with `python3 launch_gui.py`, or launch **Atom Code Bug Finder Harness** from the app menu. The server binds to `127.0.0.1:8765` and opens in a browser. The GUI stays available while the local server process runs.

For a direct benchmark without the GUI:

```sh
python3 run_external.py \
  --config examples/ordinary_code/config.json \
  --output ordinary-code-results.json
```

For an AI host, register `/usr/bin/python3` with the argument `/home/jesse/Desktop/Projects/chaos-security-benchmark/mcp_server.py`. The seven MCP tools list configs, start and poll runs, read receipts and cancel active work. `GUI-AND-AI.md` has a generic host configuration example.

## Add a target

1. Choose one behavior and write its contract in plain terms. Define at least one legitimate and one violating labeled control. A check that merely copies the target's calculation cannot provide independent evidence.
2. Write a target JSON-line wrapper that reads one `{"request": ...}` per line and replies with `{"result": ...}`. Keep one request self-contained; represent a multi-step workflow as one request array or object.
3. Write a separate checker command. It sees the request and result and replies with a Boolean `violation` and short reason. It should not import the target's decision function.
4. Create a config JSON with `cwd`, target/checker command arrays, declared `source_paths`, bounded grammar, seeds, call budget, timeout and controls. The included `examples/ordinary_code/config.json` is a complete working example. See `EXTERNAL-CODE.md` for grammar forms.
5. Run the controls and a bounded benchmark. Inspect the saved witness request, verify it again outside the generator, and report both the plain and chaos scores. Do not interpret a `succeeded` job state as a passed benefit gate.

The wrapper and checker can live in another repository; the config can point there. For source independence, upload a ZIP containing the app and the wrappers, then run its copied snapshot. The ZIP manifest can register one or several configs automatically.

## Run the meaningful checks

```sh
python3 tests/external_boundary.py
python3 tests/ui_mcp_boundaries.py
PYTHONPATH=. python3 tests/cancel_run.py
python3 tests/upload_portable.py
PYTHONPATH=. python3 tests/dev_docs_boundary.py
python3 verify_broad.py
python3 -m compileall -q run_external.py job_service.py web_app.py mcp_server.py portable_projects.py
```

The boundary checks cover external subprocess behavior, invalid controls, a stalled target and cleanup, HTTP/MCP job lifecycle, ZIP import/export, source removal, reimport and hostile archive rejection. `verify_broad.py` verifies the preserved synthetic benchmark receipts. Keep checks focused on the boundary a change touches; rerun broader checks only when a shared interface changes.

## Change discipline

The `PRECOMMIT.md`, `EXPANDED-PRECOMMIT.md`, `WORKFLOW-PRECOMMIT.md`, `BROAD-PRECOMMIT.md` and `NORMAL-CODE-PRECOMMIT.md` files freeze historical experiments. Keep them and their failed gates as evidence. For a new experiment, write its metrics, controls, seeds and predicted failure boundary before implementation. Change code and record a new receipt rather than rewriting a prior outcome.

Use source hashes to distinguish test code drift from a changed target. The runner hashes only the files listed in `source_paths`; include every source file whose behavior matters. A passing hash check cannot validate undeclared imports, runtime packages or external services.
