# Architecture and data flow

## What owns each behavior

- `run_external.py` is the experiment entry point. It loads a config, validates controls, runs each seed in both arms, replays witnesses and writes one JSON receipt.
- `external_grammar.py` validates and generates bounded JSON inputs. `Choices` in `run_expanded.py` supplies ordinary seeded choice or a centered logistic-map weight perturbation.
- `external_protocol.py` owns the two JSON-line subprocesses, request/reply limits, timeouts and cleanup. The target and checker remain separate commands.
- `job_service.py` owns saved config IDs, run IDs, background jobs, status files, receipts and the cross-process active-run lock. It invokes `run_external.py` rather than duplicating its logic.
- `web_app.py` serves the loopback HTTP API and static browser assets in `web/`. The GUI creates configs, starts/stops runs and reads saved results.
- `mcp_server.py` exposes saved configs and runs as stdio MCP tools. It uses `JobService`, so an AI sees the same catalog and receipts as the GUI.
- `portable_projects.py` extracts validated ZIP entries into `projects/<id>/files/`, records the imported file hashes, associates configs and builds export bundles.
- `launch_gui.py` starts or reuses the local server; `packaging/atom-code-bug-finder-harness.desktop` is the installed app-menu entry.

## How one run moves through the system

```text
GUI or MCP tool -> JobService -> run_external.py
                                -> config + labeled controls
                                -> bounded grammar + seeded Choices
                                -> target JSON line -> result
                                -> checker JSON line -> violation verdict
                                -> first witness per seed
                                -> fresh-process replay
                                -> runs/<id>.receipt.json
GUI or MCP tool <- run status and receipt <- JobService
```

The target receives `{"request": ...}`. It returns `{"result": ...}`. The checker receives both request and result, then returns `{"violation": true|false, "reason": "..."}`. Every reply must be one JSON line and flush stdout. For a stateful function, one request should describe the complete action sequence because each seed and arm receives a fresh target/checker process pair.

## Why the boundaries are separate

The checker cannot be inferred safely from a target's implementation. A program can return a plausible wrong value, so the checker needs an independent contract. The GUI and MCP surfaces only select saved configurations and inspect results; they do not decide what counts as a bug. The single active-run lock prevents the GUI and MCP process from launching overlapping benchmarks against the same machine. Imported app files live in a managed snapshot so source movement does not silently redirect a run to another checkout.

## Persistent and generated files

Tracked source and example files live in this Git repository. User configs are under ignored `configs/`; uploaded app snapshots under ignored `projects/`; run status, logs and receipts under ignored `runs/`. `examples/ordinary_code_bundle.zip` is a tracked import example. The Git history preserves the frozen earlier experiment protocols and receipts; active runs do not edit those tracked artifacts.

`JobService` marks a run `succeeded` when the runner exits cleanly and writes a receipt. That status says the run completed. A benefit gate inside the receipt can still be `FAILED`; inspect the gates before making any effectiveness claim.
