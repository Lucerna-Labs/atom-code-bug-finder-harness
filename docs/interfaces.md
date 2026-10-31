# Browser, API and AI interfaces

## Browser and HTTP

`launch_gui.py` starts or reuses `web_app.py` on `127.0.0.1:8765`. The browser UI is implemented in `web/index.html`, `web/app.js` and `web/style.css`. It lists saved configs and imported apps, starts or stops a run, reads the status and receipt, creates a config, uploads an app ZIP and downloads a portable bundle. The page renders values as text rather than inserting uploaded strings as HTML.

The HTTP API provides `/api/health`, `/api/configs`, `/api/projects` and `/api/runs` with detail routes for IDs, run receipts/logs and project export. ZIP import is `POST /api/projects/import`. Mutating calls require JSON or ZIP content type, a local request header and a matching browser Origin when present. The server accepts only localhost Host values and sends a restrictive content security policy. It has no user authentication and must stay bound to loopback.

Important routes and payloads:

- `GET /api/configs` lists saved IDs. `GET /api/configs/<id>` returns the raw JSON config and its hash. `POST /api/configs` accepts `{"id":"my-check","config":{...}}` and creates a validated, immutable ID.
- `POST /api/runs` accepts `{"config_id":"my-check"}` and returns a run ID. `GET /api/runs/<id>` returns `starting`, `running`, `succeeded`, `failed` or `cancelled`. `GET /api/runs/<id>/receipt` returns the complete experiment receipt after success. `GET /api/runs/<id>/log` returns a bounded log tail. `POST /api/runs/<id>/cancel` stops an active run.
- `GET /api/projects` and `GET /api/projects/<id>` show imported snapshots. `POST /api/projects/import` accepts the ZIP bytes as `application/zip`, with `X-Chaos-Project-Id` and URL-encoded `X-Chaos-Project-Name` headers. `GET /api/projects/<id>/export` returns a ZIP download; it requires `X-Chaos-Local: 1`.

Browser POST requests also set `X-Chaos-Local: 1` and use a same-origin `Origin`. The GUI's `web/app.js` shows working request shapes. Invalid config and upload requests return a JSON `error` field with a non-success HTTP status. The result is kept in a file under ignored `runs/`, not in browser storage.

## AI through MCP

`mcp_server.py` serves stdio MCP messages. It advertises seven tools: `list_configs`, `get_config`, `start_run`, `get_run`, `list_runs`, `read_receipt` and `cancel_run`. Its modern 2026-07-28 and legacy 2025-11-25 lifecycles were exercised through an official MCP Python client. The production server itself uses no third-party MCP package. AI tools can run only a named saved config; they cannot submit an arbitrary shell command or upload new app files through MCP.

`JobService` is shared by both interfaces. It stores one status JSON, one log and one receipt per run under `runs/`. A file lock permits one active run across separate GUI and MCP processes. Starting a run is asynchronous; poll its status, then read the receipt when it succeeds. Cancelling sends termination to the runner, whose signal handler closes target/checker subprocesses. The GUI uses the same catalog and can show runs started by MCP.

## Why both interfaces stay thin

The UI and MCP server choose a saved configuration and display evidence. `run_external.py` remains the single authority for controls, input generation, target/checker calls, replays and gates. This keeps a GUI run and an AI run comparable and prevents one interface from quietly changing the testing method. The exact MCP host registration example and local launch instructions are in `GUI-AND-AI.md`.
