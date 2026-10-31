# Local GUI and AI access

The GUI and MCP tools share the saved configuration catalog and run receipts in this standalone project. Both call the existing `run_external.py` runner; neither changes the target or checker source.

## Open the GUI

Use the **Chaos Security Benchmark** entry in the desktop application menu. Its launcher starts the server if needed and opens `http://127.0.0.1:8765` in your browser. To start it from a terminal:

```sh
python3 /home/jesse/Desktop/Projects/chaos-security-benchmark/launch_gui.py
```

The page lets you choose a saved config, run it, stop it, inspect scores/gates/witness inputs and recent runs, or save a new JSON config. The example is ready to run. For another codebase, its target wrapper and checker still need to follow the JSON-line contract in [EXTERNAL-CODE.md](EXTERNAL-CODE.md). Copy the example in the editor, set `cwd`, `source_paths`, commands, grammar and labeled controls, then save under a new ID.

You can also upload a ZIP of an app into the GUI. [PORTABLE-UPLOAD.md](PORTABLE-UPLOAD.md) explains the optional manifest for automatic configuration and the export bundle for moving the copied app and its saved checks to another installation. AI agents can run imported configurations through the same MCP tools after the upload.

The web server binds only to `127.0.0.1`. Mutating API calls require JSON, a same-origin request, and the `X-Chaos-Local: 1` header. This is a local user tool, not an authentication boundary against other software already running as your user. A configured target runs with your account permissions, so use a checkout intended for testing. Runs, logs and receipts stay in `runs/`. The server permits one active run at a time across the GUI and MCP processes.

## Connect an AI agent

Register this stdio MCP server in an MCP-capable AI host:

```json
{
  "mcpServers": {
    "chaos-security-benchmark": {
      "command": "/usr/bin/python3",
      "args": ["/home/jesse/Desktop/Projects/chaos-security-benchmark/mcp_server.py"]
    }
  }
}
```

The host's exact configuration location varies. The MCP server uses Python's standard library; the `mcp` package is not required to **run** it. Agents can call `list_configs`, `get_config`, `start_run`, `get_run`, `list_runs`, `read_receipt`, and `cancel_run`. A typical flow is `list_configs` → `start_run` with a saved ID → poll `get_run` → `read_receipt`. Tool errors are returned as MCP tool errors. Only named saved configurations can start code; the MCP tools do not accept arbitrary shell commands or create configurations.

The server handles the current MCP `2026-07-28` stdio lifecycle and the `2025-11-25` initialization lifecycle. It was tested end to end with the official MCP Python client 2.3.0 for both versions: tool discovery, starting the example, polling, and reading its 10 saved witness replays. The [MCP stdio specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio) defines the newline-delimited JSON transport used here.

The GUI and MCP tools show the benchmark's declared results. They do not infer a checker for an arbitrary repository. The saved configuration names the code entry point and the property that counts as a failure.
